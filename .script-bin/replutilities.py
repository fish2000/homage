#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import print_function

import sys

#  N.B. this may or may not be a PY2/PY3 thing:
maxint = getattr(sys, 'maxint',
         getattr(sys, 'maxsize', (2 ** 64) / 2))

import io, os, re, six
import argparse
import array
import contextlib
import numpy

__exports__ = {}

def doctrim(docstring):
    """ This function is straight outta PEP257 -- q.v. `trim(…)`,
       “Handling Docstring Indentation” subsection sub.:
            https://www.python.org/dev/peps/pep-0257/#id18
    """
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = maxint
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < maxint:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)

def determine_name(thing, name=None, try_repr=False):
    """ Private module function to find a name for a thing. """
    if name is not None:
        return name
    code = None
    if hasattr(thing, '__export_name__'):
        # q.v. “export(…)” deco-function sub.
        if thing.__export_name__:
            return thing.__export_name__
    if hasattr(thing, '__code__'):
        # Python 3.x function code object
        code = thing.__code__
    elif hasattr(thing, 'func_code'):
        # Python 2.x function code object
        code = thing.func_code
    if code is not None:
        if hasattr(code, 'co_name'):
            # Use the code objects’ name
            name = code.co_name
    else:
        # Try either __qualname__ or __name__
        if hasattr(thing, '__qualname__'):
            name = thing.__qualname__
        elif hasattr(thing, '__name__'):
            name = thing.__name__
    if try_repr and name is None:
        return repr(thing)
    return name

class ExportError(NameError):
    pass

def export(thing, name=None, *, doc=None):
    """ Add a function -- or any object, really, to the export list.
        Exported items will end up wih their names in the modules’
       `__all__` tuple, and will also be named in the list returned
        by the modules’ `__dir__()` function.
        
        Use export as a decorator to a function definition:
            
            @export
            def yo_dogg(i_heard=None):
                ...
        
        … or manually, to export anything that doesn’t have a name:
            
            yo_dogg = lambda i_heard=None: ...
            dogg_heard_index = ( ... ) 
            
            export(yo_dogg,             name="yo_dogg")
            export(dogg_heard_index,    name="dogg_heard_index")
    """
    # Access the module-namespace __exports__ dict:
    global __exports__
    
    # No explict name was passed --
    # try to determine one:
    name = determine_name(thing, name=name)
    
    # Double-check our name and item before stowing:
    if name is None:
        raise ExportError("can’t export an unnamed thing")
    if name in __exports__:
        raise ExportError("can’t re-export “%s”" % name)
    if name == '<lambda>':
        raise ExportError("can’t export an unnamed lambda")
    if thing is __exports__:
        raise ExportError("can’t export the __export__ dict directly")
    
    # If a “doc” argument was passed in, attempt to assign
    # the __doc__ attribute accordingly on the item -- note
    # that this won’t work for e.g. slotted, builtin, or C-API
    # types that lack mutable __dict__ internals (or at least
    # a settable __doc__ slot or established attribute).
    if doc is not None:
        try:
            thing.__doc__ = doctrim(doc)
        except AttributeError:
            pass
    
    # Stow the item in the global __exports__ dict:
    __exports__[name] = thing
    
    # Attempt to assign our name as a private attribute
    # on the item -- q.v. __doc__ note supra.
    if not hasattr(thing, '__export_name__'):
        try:
            thing.__export_name__ = name
        except AttributeError:
            pass
    return thing

@export
def tuplize(*items):
    """ Return a new tuple containing all non-`None` arguments """
    return tuple(item for item in items if item is not None)

@export
def uniquify(*items):
    """ Return a tuple with a unique set of all non-`None` arguments """
    return tuple(frozenset(item for item in items if item is not None))

@export
def listify(*items):
    """ Return a new list containing all non-`None` arguments """
    return list(item for item in items if item is not None)

# UTILITY STUFF: SimpleNamespace
@export
class SimpleNamespace(object):
    
    """ Implementation courtesy this SO answer:
        • https://stackoverflow.com/a/37161391/298171
    """
    __slots__ = tuplize('__dict__', '__weakref__')
    
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    
    def __repr__(self):
        keys = sorted(self.__dict__)
        items = ("{}={!r}".format(k, self.__dict__[k]) for k in keys)
        return "{}({})".format(type(self).__name__, ", ".join(items))
    
    def __eq__(self, other):
        return self.__dict__ == other.__dict__


# UTILITY FUNCTIONS: getattr(…) shortcuts:
or_none = lambda thing, atx: getattr(thing, atx, None)
attr = lambda thing, *attrs: ([or_none(thing, atx) for atx in attrs if or_none(thing, atx) is not None] or [None]).pop()
getpyattr = lambda thing, atx, default_value=None: getattr(thing, '__%s__' % atx, default_value)
pyattr = lambda thing, *attrs: ([getpyattr(thing, atx) for atx in attrs if getpyattr(thing, atx) is not None] or [None]).pop()

@export
def nameof(thing, fallback=''):
    """ Get the name of a thing, according to either:
        >>> thing.__qualname__
        … or:
        >>> thing.__name__
        … optionally specifying a fallback string.
    """
    return determine_name(thing) or fallback

BUILTINS =  ('__builtins__', '__builtin__', 'builtins', 'builtin')

import types as thetypes
types = SimpleNamespace()
typed = re.compile(r"^(?P<typename>\w+)(?:Type)$")

# Fill a namespace with type aliases, minus the fucking 'Type' suffix --
# We know they are types because they are in the fucking “types” module, OK?
# And those irritating four characters take up too much pointless space, if
# you asked me, which you implicitly did by reading the comments in my code,
# dogg.

for typename in dir(thetypes):
    if typename.endswith('Type'):
        setattr(types, typed.match(typename).group('typename'),
        getattr(thetypes, typename))
    elif typename not in BUILTINS:
        setattr(types, typename, getattr(thetypes, typename))

# UTILITY FUNCTIONS: hasattr(…) shortcuts:
haspyattr = lambda thing, atx: hasattr(thing, '__%s__' % atx)
anyattrs = lambda thing, *attrs: any(hasattr(thing, atx) for atx in attrs)
allattrs = lambda thing, *attrs: all(hasattr(thing, atx) for atx in attrs)
anypyattrs = lambda thing, *attrs: any(haspyattr(thing, atx) for atx in attrs)
allpyattrs = lambda thing, *attrs: all(haspyattr(thing, atx) for atx in attrs)

# isiterable = lambda thing: hasattr(thing, '__iter__') or hasattr(thing, '__getitem__')
isiterable = lambda thing: anypyattrs(thing, 'iter', 'getitem')

@export
def graceful_issubclass(thing, *cls_or_tuple):
    """ A wrapper for `issubclass()` that tries to work with you. """
    if len(cls_or_tuple) == 1:
        cls_or_tuple = cls_or_tuple[0]
    else:
        cls_or_tuple = tuple(item for item in cls_or_tuple if item is not None)
    if (not isinstance(cls_or_tuple, (type, tuple))) \
        and isiterable(cls_or_tuple):
        cls_or_tuple = tuple(cls_or_tuple)
    try:
        return issubclass(thing, cls_or_tuple)
    except TypeError:
        pass
    try:
        return issubclass(type(thing), cls_or_tuple)
    except TypeError:
        pass
    return None

# UTILITY FUNCTIONS: is<something>() unary-predicates, and utility type-tuples with which
# said predicates use to make their decisions:
isabstract = lambda method: getattr(method, '__isabstractmethod__', False)
isabstractcontextmanager = lambda cls: graceful_issubclass(cls, contextlib.AbstractContextManager)
# iscontextmanager = lambda cls: (hasattr(cls, '__enter__') and hasattr(cls, '__exit__')) \
#                                                            or isabstractcontextmanager(cls)
iscontextmanager = lambda cls: allpyattrs(cls, 'enter', 'exit') or isabstractcontextmanager(cls)

array_types = (numpy.ndarray,
               numpy.matrix,
               numpy.ma.MaskedArray, array.ArrayType,
                                     bytearray)
bytes_types = (bytes, bytearray)
string_types = six.string_types
path_classes = tuplize(argparse.FileType, or_none(os, 'PathLike'))
path_types = string_types + bytes_types + path_classes
file_types = (io.TextIOBase, io.BufferedIOBase, io.RawIOBase, io.IOBase)
callable_types = (types.Function,
                  types.Method,
                  types.Lambda,
                  types.BuiltinFunction,
                  types.BuiltinMethod)
if six.PY3:
    callable_types += (
                  types.Coroutine,
                  types.ClassMethodDescriptor,
                  types.MemberDescriptor,
                  types.MethodDescriptor)


ispathtype = lambda cls: issubclass(cls, path_types)
ispath = lambda thing: graceful_issubclass(thing, path_types) or haspyattr(thing, 'fspath')
isvalidpath = lambda thing: ispath(thing) and os.path.exists(thing)

isarray = lambda thing: graceful_issubclass(thing, array_types)
isstring = lambda thing: graceful_issubclass(thing, string_types)
isbytes = lambda thing: graceful_issubclass(thing, bytes_types)
isfunction = lambda thing: graceful_issubclass(thing, types.Function, types.Lambda)

# THE MODULE EXPORTS:
export(or_none,         name='or_none',     doc="or_none(thing, attribute) → shortcut for getattr(thing, attribute, None)")
export(attr,            name='attr',        doc="Return the first existing attribute from a thing, given 1+ attribute names")
export(getpyattr,       name='getpyattr',   doc="getpyattr(thing, attribute[, default]) → shortcut for getattr(thing, '__%s__' % attribute[, default])")
export(pyattr,          name='pyattr',      doc="Return the first existing __special__ attribute from a thing, given 1+ attribute names")
export(types,           name='types',       doc=""" Namespace containing type aliases from the `types` module,
                                                    sans the irritating and lexically unnecessary “Type” suffix --
                                                    e.g. `types.ModuleType` can be accessed as just `types.Module`
                                                    from this namespace, which is less pointlessly redundant and
                                                    aesthetically more pleasant, like definitively.
                                                """)
export(BUILTINS,        name='BUILTINS')

export(haspyattr,       name='haspyattr')
export(anyattrs,        name='anyattrs')
export(allattrs,        name='allattrs')
export(anypyattrs,      name='anypyattrs')
export(allpyattrs,      name='allpyattrs')

export(isiterable,                  name='isiterable')
export(isabstract,                  name='isabstract')
export(isabstractcontextmanager,    name='isabstractcontextmanager')
export(iscontextmanager,            name='iscontextmanager')

export(array_types,     name='array_types')
export(bytes_types,     name='bytes_types')
export(string_types,    name='string_types')

export(path_classes,    name='path_classes')
export(path_types,      name='path_types')
export(file_types,      name='file_types')
export(callable_types,  name='callable_types')

export(ispathtype,      name='ispathtype')
export(ispath,          name='ispath')
export(isvalidpath,     name='isvalidpath')

export(isarray,         name='isarray')
export(isstring,        name='isstring')
export(isbytes,         name='isbytes')
export(isfunction,      name='isfunction')

export(export)                              # hahaaaaa
export(None,            name='__exports__') # in name only
export(None,            name='__all__')     # in name only

__all__ = tuple(__exports__.keys())
__dir__ = lambda: list(__all__)

def test():
    from pprint import pprint
    
    print("ALL:")
    pprint(__all__)
    
    print()
    
    print("DIR():")
    pprint(__dir__())
    
    print()
    
    print("EXPORTS:")
    # print(__exports__)
    pprint(__exports__)
    
    print()
    
    import plistlib
    dump = attr(plistlib, 'dumps', 'writePlistToString')
    load = attr(plistlib, 'loads', 'readPlistFromString')
    assert dump is not None
    assert load is not None
    wat = attr(plistlib, 'yo_dogg', 'wtf_hax')
    assert wat is None
    
    # import doctest
    # print(doctest._indent(types.__doc__))
    print(types.__doc__)

if __name__ == '__main__':
    test()