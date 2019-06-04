#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import print_function

import sys

try:
    from pathlib import Path
except ImportError:
    try:
        from pathlib2 import Path
    except ImportError:
        Path = None

#  N.B. this may or may not be a PY2/PY3 thing:
maxint = getattr(sys, 'maxint',
         getattr(sys, 'maxsize', (2 ** 64) / 2))

# Determine if we’re on PyPy:
PYPY = hasattr(sys, 'pypy_version_info')

import io, os, re, six

DEBUG = bool(int(os.environ.get('DEBUG', '0'), base=10))

import argparse
import array
import contextlib
import decimal
import warnings

try:
    from importlib.util import cache_from_source
except ImportError:
    cache_from_source = lambda pth: pth + 'c'

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
    elif hasattr(thing, '__export_name__'):
        # q.v. “export(…)” deco-function sub.
        if thing.__export_name__:
            return thing.__export_name__
    code = None
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

# λ = determine_name(lambda: None)
LAMBDA = determine_name(lambda: None)

class ExportError(NameError):
    pass

class ExportWarning(Warning):
    pass

def export(thing, name=None, doc=None):
    """ Add a function -- or any object, really -- to the export list.
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
    
    # No explict name was passed -- try to determine one:
    named = determine_name(thing, name=name)
    
    # Double-check our determined name and item before stowing:
    if named is None:
        raise ExportError("can’t export an unnamed thing")
    if named == LAMBDA:
        raise ExportError("can’t export an unnamed lambda")
    if named in __exports__:
        raise ExportError("can’t re-export name “%s”" % named)
    if thing is __exports__:
        raise ExportError("can’t export the __export__ dict directly")
    
    # At this point, “named” is valid -- if we were passed
    # a lambda, try to rename it with our valid name:
    if callable(thing):
        if getattr(thing, '__name__', '') == LAMBDA:
            thing.__name__ = thing.__qualname__ = named
            thing.__lambda_name__ = LAMBDA # To recall the lambda’s genesis
    
    # If a “doc” argument was passed in, attempt to assign
    # the __doc__ attribute accordingly on the item -- note
    # that this won’t work for e.g. slotted, builtin, or C-API
    # types that lack mutable __dict__ internals (or at least
    # a settable __doc__ slot or established attribute).
    if doc is not None:
        try:
            thing.__doc__ = doctrim(doc)
        except (AttributeError, TypeError):
            typename = determine_name(type(thing))
            message = "Can’t set the docstring for thing “%s” of type %s:" % (named, typename)
            warnings.warn(message, ExportWarning, stacklevel=2)
    
    # Stow the item in the global __exports__ dict:
    __exports__[named] = thing
    
    # Attempt to assign our name as a private attribute
    # on the item -- q.v. __doc__ note supra.
    if not hasattr(thing, '__export_name__'):
        try:
            thing.__export_name__ = named
        except (AttributeError, TypeError):
            if DEBUG:
                typename = determine_name(type(thing))
                message = "Can’t set __export_name__ for thing “%s” of type %s:" % (named, typename)
                warnings.warn(message, ExportWarning, stacklevel=2)
    
    # Return the thing, unchanged (that’s how we decorate).
    return thing


# UTILITY FUNCTIONS: helpers for builtin container types:
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

def merge_two(one, two, cls=dict):
    """ Merge two dictionaries into an instance of the specified class
        Based on this docopt example source: https://git.io/fjCZ6
    """
    if not cls:
        cls = type(one)
    keys = frozenset(one) | frozenset(two)
    merged = ((key, one.get(key, None) or two.get(key, None)) for key in keys)
    return cls(merged)

@export
def merge_as(*dicts, **overrides):
    """ Merge all dictionary arguments into a new instance of the specified class,
        passing all additional keyword arguments to the class constructor as overrides
    """
    cls = overrides.pop('cls', dict)
    if not cls:
        cls = len(dicts) and type(dicts[0]) or dict
    merged = cls(**overrides)
    for d in dicts:
        merged = merge_two(merged, d, cls=cls)
    return merged

@export
def merge(*dicts, **overrides):
    """ Merge all dictionary arguments into a new `dict` instance, using any
        keyword arguments as item overrides in the final `dict` instance returned
    """
    if 'cls' in overrides:
        raise NameError('Cannot override the `cls` value')
    return merge_as(*dicts, cls=dict, **overrides)

# UTILITY FUNCTIONS: hasattr(…) shortcuts:
haspyattr = lambda thing, atx: hasattr(thing, '__%s__' % atx)
anyattrs = lambda thing, *attrs: any(hasattr(thing, atx) for atx in attrs)
allattrs = lambda thing, *attrs: all(hasattr(thing, atx) for atx in attrs)
anypyattrs = lambda thing, *attrs: any(haspyattr(thing, atx) for atx in attrs)
allpyattrs = lambda thing, *attrs: all(haspyattr(thing, atx) for atx in attrs)

# Things with either __iter__(…) OR __getitem__(…) are iterable:
isiterable = lambda thing: anypyattrs(thing, 'iter', 'getitem')

# q.v. `merge_two(…)` implementation supra.
ismergeable = lambda thing: bool(hasattr(thing, 'get') and isiterable(thing))

# UTILITY STUFF: asdict(…)
# Originally implemented as a lambda:
# asdict = lambda thing: isinstance(thing, dict) \
#                               and thing \
#                       or (hasattr(thing, '__dict__') \
#                               and thing.__dict__ \
#                           or dict(thing))
@export
def asdict(thing):
    """ asdict(thing) → returns either thing, thing.__dict__, or dict(thing) as necessary """
    if isinstance(thing, dict):
        return thing
    if hasattr(thing, '__dict__'):
        return thing.__dict__
    return dict(thing)

# UTILITY STUFF: SimpleNamespace
@export
class SimpleNamespace(object):
    
    """ Implementation courtesy this SO answer:
        • https://stackoverflow.com/a/37161391/298171
    """
    __slots__ = tuplize('__dict__', '__weakref__')
    
    def __init__(self, *args, **kwargs):
        for arg in args:
            self.__dict__.update(asdict(arg))
        self.__dict__.update(kwargs)
    
    def __iter__(self):
        return iter(self.__dict__.keys())
    
    def __repr__(self):
        items = ("{}={!r}".format(key, self.__dict__[key]) for key in sorted(self))
        return "{}({}) @ {}".format(determine_name(type(self)),
                          ", ".join(items),          id(self))
    
    def __eq__(self, other):
        return self.__dict__ == asdict(other)
    
    def __ne__(self, other):
        return self.__dict__ != asdict(other)

@export
class NoDefault(object):
    __slots__ = tuplize()
    def __new__(cls, *a, **k):
        return cls

@export
class Namespace(SimpleNamespace):
    
    """ Namespace adds the `get(…)`, `__len__()`, `__contains__(…)`, `__getitem__(…)`,
        `__setitem__(…)`, `__add__(…)`, and `__bool__()` methods to its ancestor class
        implementation SimpleNamespace.
        
        Since it implements a `get(…)` method, Namespace instances can be passed
        to `merge(…)` – q.v. `merge(…)` function definition supra.
        
        Additionally, Namespace furnishes an `__all__` property implementation.
    """
    __slots__ = tuplize()
    
    # Right now @export can’t export a subclass of something that’s
    # already been exported, unless you manually name it, like so:
    __export_name__ = 'Namespace'
    
    def get(self, key, default=NoDefault):
        """ Return the value for key if key is in the dictionary, else default. """
        if default is NoDefault:
            return self.__dict__.get(key)
        return self.__dict__.get(key, default)
    
    @property
    def __all__(self):
        """ Get a tuple with all the stringified keys in the Namespace. """
        return tuple(str(key) for key in sorted(self))
    
    @__all__.setter
    def __all__(self, value):
        # Set ops on __all__ are no-ops – 
        # allow them to happen, but do nothing:
        pass
    
    def __len__(self):
        return len(self.__dict__)
    
    def __contains__(self, key):
        return key in self.__dict__
    
    def __getitem__(self, key):
        return self.__dict__.__getitem__(key)
    
    def __setitem__(self, key, value):
        self.__dict__.__setitem__(key, value)
    
    def __delitem__(self, key):
        self.__dict__.__delitem__(key)
    
    def __add__(self, operand):
        # On add, old values are not overwritten
        if not ismergeable(operand):
            return NotImplemented
        return merge_two(self, operand, cls=type(self))
    
    def __radd__(self, operand):
        # On reverse-add, old values are overwritten
        if not ismergeable(operand):
            return NotImplemented
        return merge_two(operand, self, cls=type(self))
    
    def __iadd__(self, operand):
        # On in-place add, old values are updated and replaced
        if not ismergeable(operand):
            return NotImplemented
        self.__dict__.update(asdict(operand))
        return self
    
    def __or__(self, operand):
        return self.__add__(operand)
    
    def __ror__(self, operand):
        return self.__radd__(operand)
    
    def __ior__(self, operand):
        return self.__iadd__(operand)
    
    def __bool__(self):
        return bool(self.__dict__)

# UTILITY FUNCTIONS: getattr(…) shortcuts:
no_op = lambda thing, atx, default=None: atx or default
or_none = lambda thing, atx: getattr(thing, atx, None)
getpyattr = lambda thing, atx, default=None: getattr(thing, '__%s__' % atx, default)
getitem = lambda thing, itx, default=None: getattr(thing, 'get', no_op)(itx, default)

accessor = lambda function, thing, *attrs: ([atx for atx in (function(thing, atx) \
                                                 for atx in attrs) \
                                                 if atx is not None] or [None]).pop(0)

attr = lambda thing, *attrs: accessor(or_none, thing, *attrs)
pyattr = lambda thing, *attrs: accessor(getpyattr, thing, *attrs)
item = lambda thing, *items: accessor(getitem, thing, *items)

@export
def nameof(thing, fallback=''):
    """ Get the name of a thing, according to either:
        >>> thing.__qualname__
        … or:
        >>> thing.__name__
        … optionally specifying a fallback string.
    """
    return determine_name(thing) or fallback

BUILTINS = ('__builtins__', '__builtin__', 'builtins', 'builtin')
VERBOTEN = tuple('__%s__' % atx for atx in ('all', 'cached', 'loader', 'file', 'spec'))
VERBOTEN += BUILTINS
VERBOTEN += ('Namespace', 'SimpleNamespace')

import types as thetypes
types = Namespace()
typed = re.compile(r"^(?P<typename>\w+)(?:Type)$")

# Fill a Namespace with type aliases, minus the fucking 'Type' suffix --
# We know they are types because they are in the fucking “types” module, OK?
# And those irritating four characters take up too much pointless space, if
# you asked me, which you implicitly did by reading the comments in my code,
# dogg.

for typename in dir(thetypes):
    if typename.endswith('Type'):
        setattr(types, typed.match(typename).group('typename'),
        getattr(thetypes, typename))
    elif typename not in VERBOTEN:
        setattr(types, typename, getattr(thetypes, typename))

# Substitute our own SimpleNamespace class, instead of the provided version:
setattr(types, 'Namespace',       Namespace)
setattr(types, 'SimpleNamespace', SimpleNamespace)

# Get the `importlib.util.cache_from_source` function,
# using a default that simply appends a 'c' to the end of the path,
# which that should work for Python-2 purposes:
# cache_from_source = getattr(importlib.util, 'cache_from_source', lambda pth: pth + 'c')

# Manually set `types.__file__`:
setattr(types, '__file__',        __file__)
setattr(types, '__cached__',      cache_from_source(__file__))

@export
def graceful_issubclass(thing, *cls_or_tuple):
    """ A wrapper for `issubclass()` that tries to work with you. """
    length = 0
    try:
        length = len(cls_or_tuple)
    except TypeError:
        pass
    else:
        if length == 1:
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
isabstractmethod = lambda method: getattr(method, '__isabstractmethod__', False)
isabstract = lambda thing: bool(pyattr(thing, 'abstractmethods', 'isabstractmethod'))
isabstractcontextmanager = lambda cls: graceful_issubclass(cls, contextlib.AbstractContextManager)
iscontextmanager = lambda cls: allpyattrs(cls, 'enter', 'exit') or isabstractcontextmanager(cls)

numeric_types = (int, float, decimal.Decimal)

try:
    import numpy
except (ImportError, SyntaxError):
    numpy = None
    array_types = (array.ArrayType,
                   bytearray, memoryview)
else:
    array_types = (numpy.ndarray,
                   numpy.matrix,
                   numpy.ma.MaskedArray, array.ArrayType,
                                         bytearray, memoryview)

bytes_types = (bytes, bytearray)
string_types = six.string_types
path_classes = tuplize(argparse.FileType, or_none(os, 'PathLike'), Path) # Path may be “None” in disguise
path_types = string_types + bytes_types + path_classes
file_types = (io.TextIOBase, io.BufferedIOBase, io.RawIOBase, io.IOBase)

callable_types = (types.Function,
                  types.Method,
                  types.Lambda,
                  types.BuiltinFunction,
                  types.BuiltinMethod)

if six.PY3 and not PYPY:
    callable_types += (
                  types.Coroutine,
                  types.ClassMethodDescriptor,
                  types.MemberDescriptor,
                  types.MethodDescriptor)


ispathtype = lambda cls: issubclass(cls, path_types)
ispath = lambda thing: graceful_issubclass(thing, path_types) or haspyattr(thing, 'fspath')
isvalidpath = lambda thing: ispath(thing) and os.path.exists(os.path.expanduser(thing))

isnumber = lambda thing: graceful_issubclass(thing, numeric_types)
isnumeric = lambda thing: graceful_issubclass(thing, numeric_types)
isarray = lambda thing: graceful_issubclass(thing, array_types)
isstring = lambda thing: graceful_issubclass(thing, string_types)
isbytes = lambda thing: graceful_issubclass(thing, bytes_types)
isfunction = lambda thing: isinstance(thing, (types.Function, types.Lambda)) or callable(thing)
islambda = lambda thing: pyattr(thing, 'lambda_name', 'name', 'qualname') == LAMBDA

# THE MODULE EXPORTS:
export(ExportError,     name='ExportError', doc="An exception raised during a call to export()")
export(ExportWarning,   name='ExportWarning', doc="A warning issued during a call to export()")
export(doctrim,         name='doctrim')

export(haspyattr,       name='haspyattr',   doc="haspyattr(thing, attribute) → boolean predicate, shortcut for hasattr(thing, '__%s__' % attribute)")
export(anyattrs,        name='anyattrs',    doc="anyattrs(thing, *attributes) → boolean predicate, shortcut for any(hasattr(thing, atx) for atx in attributes)")
export(allattrs,        name='allattrs',    doc="allattrs(thing, *attributes) → boolean predicate, shortcut for all(hasattr(thing, atx) for atx in attributes)")
export(anypyattrs,      name='anypyattrs',  doc="anypyattrs(thing, *attributes) → boolean predicate, shortcut for any(haspyattr(thing, atx) for atx in attributes)")
export(allpyattrs,      name='allpyattrs',  doc="allpyattrs(thing, *attributes) → boolean predicate, shortcut for all(haspyattr(thing, atx) for atx in attributes)")
export(isiterable,      name='isiterable',  doc="isiterable(thing) → boolean predicate, True if thing can be iterated over")
export(ismergeable,     name='ismergeable', doc="ismergeable(thing) → boolean predicate, True if thing is a valid operand to merge(…) or merge_as(…)")

export(no_op,           name='no_op',       doc="no_op(thing, attribute, default=None) → shortcut for (attribute or default)")
export(or_none,         name='or_none',     doc="or_none(thing, attribute) → shortcut for getattr(thing, attribute, None)")
export(getpyattr,       name='getpyattr',   doc="getpyattr(thing, attribute[, default]) → shortcut for getattr(thing, '__%s__' % attribute[, default])")
export(getitem,         name='getitem',     doc="getitem(thing, item[, default]) → shortcut for thing.get(item[, default])")
export(accessor,        name='accessor',    doc="accessor(func, thing, *attributes) → return the first non-None value had by successively applying func(thing, attribute)")
export(attr,            name='attr',        doc="Return the first existing attribute from a thing, given 1+ attribute names")
export(pyattr,          name='pyattr',      doc="Return the first existing __special__ attribute from a thing, given 1+ attribute names")
export(item,            name='item',        doc="Return the first existing item held by thing, given 1+ item names")

# NO DOCS ALLOWED:
# export(λ,               name='λ')
export(PYPY,            name='PYPY')
export(LAMBDA,          name='LAMBDA')
export(BUILTINS,        name='BUILTINS')
export(VERBOTEN,        name='VERBOTEN')

export(types,           name='types',       doc=""" A Namespace instance containing aliases into the `types` module,
                                                    sans the irritating and lexically unnecessary “Type” suffix --
                                                    e.g. `types.ModuleType` can be accessed as just `types.Module`
                                                    from this Namespace, which is less pointlessly redundant and far
                                                    more typographically pleasing, like definitively.
                                                """)

export(isabstractmethod,                   name='isabstractmethod',
                                            doc="isabstractmethod(thing) → boolean predicate, True if thing is a method declared abstract with @abc.abstractmethod")
export(isabstract,                         name='isabstract',
                                            doc="isabstract(thing) → boolean predicate, True if thing is an abstract method OR an abstract base class (née ABC)")
export(isabstractcontextmanager,           name='isabstractcontextmanager',
                                            doc="isabstractcontextmanager(thing) → boolean predicate, True if thing decends from contextlib.AbstractContextManager")
export(iscontextmanager,                   name='iscontextmanager',
                                            doc="iscontextmanager(thing) → boolean predicate, True if thing is a context manager (either abstract or concrete)")

# NO DOCS ALLOWED:
export(numeric_types,   name='numeric_types')
export(array_types,     name='array_types')
export(bytes_types,     name='bytes_types')
export(string_types,    name='string_types')

# NO DOCS ALLOWED:
export(path_classes,    name='path_classes')
export(path_types,      name='path_types')
export(file_types,      name='file_types')
export(callable_types,  name='callable_types')

export(ispathtype,      name='ispathtype',  doc="ispathtype(thing) → boolean predicate, True if thing is a path type")
export(ispath,          name='ispath',      doc="ispath(thing) → boolean predicate, True if thing seems to be path-ish instance")
export(isvalidpath,     name='isvalidpath', doc="isvalid(thing) → boolean predicate, True if thing is a valid path on the filesystem")

export(isnumber,        name='isnumber',    doc="isnumber(thing) → boolean predicate, True if thing is a numeric type or an instance of same")
export(isnumeric,       name='isnumeric',   doc="isnumeric(thing) → boolean predicate, True if thing is a numeric type or an instance of same")
export(isarray,         name='isarray',     doc="isarray(thing) → boolean predicate, True if thing is an array type or an instance of same")
export(isstring,        name='isstring',    doc="isstring(thing) → boolean predicate, True if thing is a string type or an instance of same")
export(isbytes,         name='isbytes',     doc="isbytes(thing) → boolean predicate, True if thing is a bytes-like type or an instance of same")
export(isfunction,      name='isfunction',  doc="isfunction(thing) → boolean predicate, True if thing is of a callable function type")
export(islambda,        name='islambda',    doc="islambda(thing) → boolean predicate, True if thing is a function created with the «lambda» keyword")

# NO DOCS ALLOWED:
export(export)                              # hahaaaaa
export(None,            name='__exports__') # in name only
export(None,            name='__all__')     # in name only

__all__ = tuple(__exports__.keys())
__dir__ = lambda: list(__all__)

def test():
    from pprint import pprint
    from terminalsize import get_terminal_size
    
    termsize = get_terminal_size(default=(100, 25))
    SEPARATOR_WIDTH = termsize[0]
    print_separator = lambda: print('-' * SEPARATOR_WIDTH)
    
    # print("ALL: (length=%i)" % len(__all__))
    # print()
    # pprint(__all__)
    
    # print()
    
    # print("DIR(): (length=%i)" % len(__dir__()))
    # print()
    # pprint(__dir__())
    
    # print()
    
    assert list(__all__) == __dir__()
    assert len(__all__) == len(__dir__())
    assert len(__all__) == len(__exports__)
    
    print("EXPORTS: (length=%i)" % len(__exports__))
    print()
    pprint(__exports__, indent=4, width=SEPARATOR_WIDTH)
    
    print()
    
    print("» Checking “attr(•) accessor …”")
    print()
    
    import plistlib
    dump = attr(plistlib, 'dumps', 'writePlistToString')
    load = attr(plistlib, 'loads', 'readPlistFromString')
    assert dump is not None
    assert load is not None
    wat = attr(plistlib, 'yo_dogg', 'wtf_hax')
    assert wat is None
    
    print("» Checking basic isXXX(•) functions …")
    print()
    
    assert graceful_issubclass(int, int)
    
    assert ispathtype(str)
    assert ispathtype(bytes)
    assert ispathtype(os.PathLike)
    assert not ispathtype(SimpleNamespace)
    assert ispath('/yo/dogg')
    assert not ispath(SimpleNamespace())
    assert not isvalidpath('/yo/dogg')
    assert isvalidpath('/')
    assert isvalidpath('/private/tmp')
    assert isvalidpath('~/')
    
    assert isnumber(int)
    assert isnumber(decimal.Decimal)
    assert isnumber(666)
    assert not isnumber(str)
    assert not isnumber("666")
    assert isnumeric(int)
    assert isnumeric(float)
    assert isnumeric(1)
    assert not isnumeric(bytes)
    assert not isnumeric("2001e50")
    
    assert isarray(array.array)
    if numpy is not None:
        assert isarray(numpy.ndarray)
        assert isarray(numpy.array([0, 1, 2]))
    assert isstring(str)
    assert isstring("")
    assert isbytes(bytes)
    assert isbytes(bytearray)
    assert isbytes(b"")
    
    assert islambda(lambda: None)
    assert islambda(attr)
    assert not islambda(export)
    assert isfunction(lambda: None)
    assert isfunction(attr)
    assert isfunction(export)
    assert not isfunction(SimpleNamespace())
    assert isfunction(SimpleNamespace) # classes are callable!
    
    print("» Checking lambda naming …")
    
    lammy = lambda: None
    print("» lambda name = %s" % lammy.__name__)
    print("» lambda name = %s" % pyattr(lammy, 'name', 'qualname'))
    lammy_name = lammy.__name__
    lammy_pyattr_name = pyattr(lammy, 'name', 'qualname')
    lambda_name = LAMBDA
    assert lammy_name == lammy_pyattr_name
    assert lammy_name == lambda_name
    assert lammy_pyattr_name == lambda_name
    print()
    
    print("» Checking “types.__doc__ …”")
    print()
    
    print_separator()
    print('types.__doc__ =')
    print()
    print(types.__doc__)
    print_separator()
    print('type(types).__doc__ =')
    print()
    print(doctrim(type(types).__doc__))
    print_separator()
    print('type(types).__export_name__ =', type(types).__export_name__)
    print_separator()
    print()
    
    print("» Checking “haspyattr.__doc__ …”")
    print()
    
    print_separator()
    print(haspyattr.__doc__)
    print_separator()
    print()
    
    dict_one = { 'compress_level' : 9,
                       'optimize' : True,
                         'format' : 'png' }
    
    dict_two = { 'yo' : 'dogg' }
    
    dict_three = { 'compress_level' : 10,
                         'optimize' : True,
                           'format' : 'jpg' }
    
    merged = merge(dict_one, dict_two, dict_three, yo='DOGG')
    
    print("» Checking “merge(•) …”")
    print()
    
    assert merged == { 'compress_level' : 9,
                             'optimize' : True,
                               'format' : 'png',
                                   'yo' : 'DOGG' }
    
    print_separator()
    pprint(merged)
    print_separator()
    print()
    
    print("» Checking “Namespace.operator+(•) …”")
    print()
    
    ns1 = Namespace(dict_one)
    ns2 = Namespace(dict_two)
    
    merged = ns1 + ns2 + dict_three + Namespace(yo='DOGG')
    
    assert merged == { 'compress_level' : 9,
                             'optimize' : True,
                               'format' : 'png',
                                   'yo' : 'dogg' }
    
    print_separator()
    pprint(merged)
    print_separator()
    print()
    
    print("» Checking “Namespace.operator+=(•) …”")
    print()
    
    merged = Namespace(dict_one)
    ns2 = Namespace(dict_two)
    
    merged += ns2
    merged += dict_three
    merged += Namespace(yo='DOGG')
    
    assert merged == { 'compress_level' : 10,
                             'optimize' : True,
                               'format' : 'jpg',
                                   'yo' : 'DOGG' }
    
    print_separator()
    # pprint(ns2)
    # pprint(dict_three)
    pprint(merged)
    print_separator()
    print()

if __name__ == '__main__':
    test()
