#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import print_function
from collections import Counter, OrderedDict
from enum import Enum, unique, _is_dunder as ispyname
from itertools import chain
import sys, os

# Possible names for builtin modules:
BUILTINS = ('__builtins__', '__builtin__', 'builtins', 'builtin')

# Are we debuggin out?
DEBUG = bool(int(os.environ.get('DEBUG', '0'), base=10))

# On non-macOS platforms this may be awry:
ENCODING = sys.getfilesystemencoding().upper() # 'UTF-8'

# N.B. this may or may not be a PY2/PY3 thing:
MAXINT = getattr(sys, 'maxint',
         getattr(sys, 'maxsize', (2 ** 64) / 2))

# Determine if our Python is three’d up:
PY3 = sys.version_info.major > 2

# Determine if we’re on PyPy:
PYPY = hasattr(sys, 'pypy_version_info')

# Determine if we’re in TextMate:
TEXTMATE = 'TM_PYTHON' in os.environ

import io, re
import argparse
import array
import contextlib
import decimal
import warnings

class AutoType(object):
    
    """ Simple polyfill for `enum.auto` (which apparently
        does not exist in PyPy 2 for some reason)
    """
    
    def __init__(self):
        self.count = 0
    
    def __call__(self, increment=1):
        out = int(self.count)
        self.count += increment
        return out

# Try to get `auto` from `enum`, falling back to the polyfill:
try:
    from enum import auto
except ImportError:
    auto = AutoType()

# Set up some terminal-printing stuff:
if TEXTMATE:
    SEPARATOR_WIDTH = 100
else:
    from terminalsize import get_terminal_size
    SEPARATOR_WIDTH = get_terminal_size(default=(100, 25))[0]

print_separator = lambda: print('-' * SEPARATOR_WIDTH)

if PY3:
    unicode = str
    long = int

try:
    from collections.abc import Mapping, MutableMapping, Hashable as HashableABC
except ImportError:
    from collections import Mapping, MutableMapping, Hashable as HashableABC

try:
    from importlib.util import cache_from_source
except ImportError:
    # As far as I can tell, this is what Python 2.x does:
    cache_from_source = lambda pth: pth + 'c'

try:
    from functools import lru_cache
except ImportError:
    def lru_cache(**keywrds):
        """ No-op dummy decorator for lesser Pythons """
        def inside(function):
            return function
        return inside

try:
    from pathlib import Path
except ImportError:
    try:
        from pathlib2 import Path
    except ImportError:
        Path = None

pytuple = lambda *attrs: tuple('__%s__' % str(atx) for atx in attrs)

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
    indent = MAXINT
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < MAXINT:
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
    # Shortcut everything if a name was explictly specified:
    if name is not None:
        return name
    # Check for telltale function-object attributes:
    code = None
    if hasattr(thing, '__code__'): # Python 3.x
        code = thing.__code__
    elif hasattr(thing, 'func_code'): # Python 2.x
        code = thing.func_code
    # Use the function’s code object, if found…
    if code is not None:
        if hasattr(code, 'co_name'):
            name = code.co_name
    # … Otherwise, try the standard name attributes:
    else:
        if hasattr(thing, '__qualname__'):
            name = thing.__qualname__
        elif hasattr(thing, '__name__'):
            name = thing.__name__
    # We likely have something by now:
    if name is not None:
        return name
    # If asked to try the thing’s repr, return that:
    if try_repr:
        return repr(thing)
    # LAST RESORT: Search the entire id-space
    # of objects within imported modules -- it is
    # possible (however unlikely) that this’ll ending
    # up returning None:
    return thingname_search(thing)

# λ = determine_name(lambda: None)
LAMBDA = determine_name(lambda: None)

# UTILITY FUNCTIONS: boolean predicates for class types

ismetaclass = lambda thing: hasattr(thing, '__mro__') and \
                                len(thing.__mro__) > 1 and \
                                    thing.__mro__[-2] is type

isclass = lambda thing: (thing is object) or (hasattr(thing, '__mro__') and \
                         thing.__mro__[-1] is object and \
                         thing.__mro__[-2] is not type)

isclasstype = lambda thing: hasattr(thing, '__mro__') and \
                                    thing.__mro__[-1] is object

# UTILITY FUNCTIONS: hasattr(…) shortcuts:

haspyattr = lambda thing, atx: hasattr(thing, '__%s__' % atx)
anyattrs = lambda thing, *attrs: any(hasattr(thing, atx) for atx in attrs)
allattrs = lambda thing, *attrs: all(hasattr(thing, atx) for atx in attrs)
anypyattrs = lambda thing, *attrs: any(haspyattr(thing, atx) for atx in attrs)
allpyattrs = lambda thing, *attrs: all(haspyattr(thing, atx) for atx in attrs)

# Things with either __iter__(…) OR __getitem__(…) are iterable:
isiterable = lambda thing: anypyattrs(thing, 'iter', 'getitem')

# q.v. `merge_two(…)` implementation sub.
ismergeable = lambda thing: bool(hasattr(thing, 'get') and isiterable(thing))

# UTILITY FUNCTIONS: getattr(…) shortcuts:

always = lambda thing: True
never = lambda thing: False
nuhuh = lambda thing: None

no_op = lambda thing, atx, default=None: atx or default
or_none = lambda thing, atx: getattr(thing, atx, None)
getpyattr = lambda thing, atx, default=None: getattr(thing, '__%s__' % atx, default)
getitem = lambda thing, itx, default=None: getattr(thing, 'get', no_op)(itx, default)

accessor = lambda function, thing, *attrs: ([atx for atx in (function(thing, atx) \
                                                 for atx in attrs) \
                                                 if atx is not None] or [None]).pop(0)

searcher = lambda function, xatx, *things: ([atx for atx in (function(thing, xatx) \
                                                 for thing in things) \
                                                 if atx is not None] or [None]).pop(0)

attr = lambda thing, *attrs: accessor(or_none, thing, *attrs)
pyattr = lambda thing, *attrs: accessor(getpyattr, thing, *attrs)
item = lambda thing, *items: accessor(getitem, thing, *items)

attr_search = lambda atx, *things: searcher(or_none, atx, *things)
pyattr_search = lambda atx, *things: searcher(getpyattr, atx, *things)
item_search = lambda itx, *things: searcher(getitem, itx, *things)

# Does a class contain an attribute -- whether it uses `__dict__` or `__slots__`?
thing_has = lambda thing, atx: atx in (pyattr(thing, 'dict', 'slots') or tuple())
class_has = lambda cls, atx: isclasstype(cls) and thing_has(cls, atx)

# Is this a class based on a `__dict__`, or one using `__slots__`?
isslotted = lambda thing: allpyattrs(thing, 'mro', 'slots')
isdictish = lambda thing: allpyattrs(thing, 'mro', 'dict')
isslotdicty = lambda thing: allpyattrs(thing, 'mro', 'slots', 'dict')

clademap = {
    'class'         : isclass,
    'metaclass'     : ismetaclass,
    'singleton'     : lambda thing: (thing is True) or \
                                    (thing is False) or \
                                    (thing is None) or \
                                    (thing is Ellipsis) or \
                                    (thing is NotImplemented),
    'number'        : lambda thing: isinstance(thing, (int, long, float, complex)),
    'set'           : lambda thing: isinstance(thing, (set, frozenset)),
    'string'        : lambda thing: isinstance(thing, (str, unicode)),
    'bytes'         : lambda thing: isinstance(thing, (bytes, bytearray, memoryview)),
    'lambda'        : lambda thing: determine_name(thing) == LAMBDA or \
                                         getpyattr(thing, 'lambda_name') == LAMBDA,
    'function'      : lambda thing: determine_name(thing) != LAMBDA and \
                                     not haspyattr(thing, 'lambda_name') and \
                                          callable(thing) and \
                                          anyattrs(thing, '__code__', 'func_code'),
    'sequence'      : lambda thing: isinstance(thing, (tuple, list)),
    'dictionary'    : lambda thing: isinstance(thing, (dict, Mapping, MutableMapping)),
    'iterable'      : lambda thing: (not isclasstype(thing)) and \
                                          anypyattrs(thing, 'iter', 'getitem'),
    'instance'      : lambda thing: (not isclasstype(thing)) and \
                                        isclass(type(thing))
}

NoneType = type(None)
EllipsisType = type(Ellipsis)
NotImplementedType = type(NotImplemented)

SINGLETON_TYPES = (bool, NoneType, EllipsisType, NotImplementedType)

def predicates_for_types(*types):
    """ For a list of types, return a list of “isinstance” predicates """
    predicates = []
    for classtype in frozenset(types):
        predicates.append(lambda thing: isinstance(thing, classtype))
    return tuple(predicates)

@unique
class Clade(Enum):
    
    """ An enumeration class for classifying exported types. """
    
    CLASS       = (isclass, never)
    METACLASS   = (ismetaclass, never)
    SINGLETON   = (SINGLETON_TYPES,                 clademap['singleton'], never)
    NUMBER      = ((int, long, float, complex),     clademap['number'], never)
    SET         = ((set, frozenset),                clademap['set'], never)
    STRING      = ((str, unicode),                  clademap['string'], never)
    BYTES       = ((bytes, bytearray, memoryview),  clademap['bytes'], never)
    LAMBDA      =                                  (clademap['lambda'], never)
    FUNCTION    =                                  (clademap['function'], never)
    SEQUENCE    = ((tuple, list),                   clademap['sequence'], never)
    DICTIONARY  = ((dict, Mapping, MutableMapping), clademap['dictionary'], never)
    ITERABLE    =                                  (clademap['iterable'], never)
    INSTANCE    =                                  (clademap['instance'], never)
    
    @classmethod
    def of(cls, thing, name_hint=None):
        for clade in cls:
            for predicate in clade.predicates:
                if predicate(thing):
                    return clade
        thing_hinted_name = name_hint or determine_name(thing)
        raise ValueError("can’t determine clade for thing: %s" % thing_hinted_name)
    
    @classmethod
    def for_string(cls, string):
        for clade in cls:
            if clade.to_string() == string.lower():
                return clade
        raise ValueError("for_string(): unknown clade name %s" % string)
    
    @classmethod
    def label_for(cls, thing, name_hint=None):
        clade = cls.of(thing, name_hint=name_hint)
        return repr(clade)
    
    def __init__(self, *predicates):
        typelist = tuple()
        if type(predicates[0]) is tuple:
            # typelist, *predicates = predicates
            typelist = predicates[0]
            predicates = predicates[1:]
            if not all(isclasstype(putative) for putative in typelist):
                raise TypeError("non-class-type item in clade definition")
        self.predicates = predicates_for_types(*typelist) + tuple(predicates)
    
    def to_string(self):
        return str(self.name.lower())
    
    def __str__(self):
        return self.to_string()
    
    def __bytes__(self):
        return bytes(self.to_string(), encoding=ENCODING)
    
    def __repr__(self):
        return "%s.%s" % (pyattr(type(self), 'qualname', 'name'), self.name)

class ExportError(NameError):
    pass

class ExportWarning(Warning):
    pass

class NoDefault(object):
    __slots__ = tuple()
    def __new__(cls, *a, **k):
        return cls

case_sort = lambda c: c.lower() if c.isupper() else c.upper()

class Exporter(MutableMapping):
    
    """ A class representing a list of things for a module to export. """
    __slots__ = pytuple('exports', 'clades')
    
    def __init__(self):
        self.__exports__ = {}
        self.__clades__ = Counter()
    
    def exports(self):
        """ Get a new dictionary instance filled with the exports. """
        out = {}
        out.update(self.__exports__)
        return out
    
    def clade_histogram(self):
        """ Return the histogram of clade counts. """
        return Counter(self.__clades__)
    
    messages = {
        'docstr'    : "Can’t set the docstring for thing “%s” of type %s:",
        'xclade'    : "Can’t determine a clade for thing “%s” of type %s",
        'noname'    : "Can’t determine a name for lambda: 0x%0x"
    }
    
    def classify(self, thing, named):
        """ Attempt to classify a thing to a clade.
            Returns a member of the Clade enum.
        """
        clade = Clade.of(thing, name_hint=named)
        if DEBUG:
            print("••• \tthing: %s" % str(thing))
            print("••• \tnamed: %s" % str(named))
            print("••• \tclade: %s" % repr(clade))
            print()
        return clade
    
    def increment_for_clade(self, thing, named, increment=1):
        clade = self.classify(thing, named=named)
        self.__clades__[clade] += int(increment)
        return clade
    
    def decrement_for_clade(self, thing, named, decrement=-1):
        clade = self.classify(thing, named=named)
        self.__clades__[clade] += int(decrement)
        return clade
    
    def keys(self):
        """ Get a key view on the exported items dictionary. """
        return self.__exports__.keys()
    
    def values(self):
        """ Get a value view on the exported items dictionary. """
        return self.__exports__.values()
    
    def get(self, key, default=NoDefault):
        if default is NoDefault:
            return self.__exports__.get(key)
        return self.__exports__.get(key, default)
    
    def pop(self, key, default=NoDefault):
        if key in self.__exports__:
            self.decrement_for_clade(self[key], named=key)
        if default is NoDefault:
            return self.__exports__.pop(key)
        return self.__exports__.pop(key, default)
    
    def export(self, thing, name=None, doc=None):
        """ Add a function -- or any object, really -- to the export list.
            Exported items will end up wih their names in the modules’
           `__all__` tuple, and will also be named in the list returned
            by the modules’ `__dir__()` function.
            
            It looks better if this method is decoupled from its parent
            instance, to wit:
            
                exporter = Exporter()
                export = exporter.decorator() # q.v. “decorator()” sub.
            
            Use `export` as a decorator to a function definition:
                
                @export
                def yo_dogg(i_heard=None):
                    …
                
            … or manually, to export anything that doesn’t have a name:
                
                yo_dogg = lambda i_heard=None: …
                dogg_heard_index = ( ¬ ) 
                
                export(yo_dogg,             name="yo_dogg")
                export(dogg_heard_index,    name="dogg_heard_index")
            
        """
        # No explict name was passed -- try to determine one:
        named = determine_name(thing, name=name)
        
        # Double-check our determined name and item before stowing:
        if named is None:
            raise ExportError("can’t export an unnamed thing")
        if named in self.__exports__:
            raise ExportError("can’t re-export name “%s”" % named)
        if thing is self.__exports__:
            raise ExportError("can’t export the __exports__ dict directly")
        if thing is self:
            raise ExportError("can’t export an exporter instance directly")
        
        # Attempt to classify the item to a clade:
        try:
            self.increment_for_clade(thing, named=named)
        except ValueError:
            # no clade found
            typename = determine_name(type(thing))
            warnings.warn(type(self).messages['xclade'] % (named, typename),
                          ExportWarning, stacklevel=2)
        
        # At this point, “named” is valid -- if we were passed
        # a lambda, try to rename it with either our valid name,
        # or the result of an ID-based search for that lambda:
        if callable(thing):
            if getattr(thing, '__name__', '') == LAMBDA:
                if named == LAMBDA:
                    named = thingname_search(thing)
                if named is None:
                    raise ExportError(type(self).messages['noname'] % id(thing))
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
                warnings.warn(type(self).messages['docstr'] % (named, typename),
                              ExportWarning, stacklevel=2)
        
        # Stow the item in the global __exports__ dict:
        self.__exports__[named] = thing
        
        # Return the thing, unchanged (that’s how we decorate).
        return thing
    
    def decorator(self):
        """ Return a reference to this Exporter instances’ “export”
            method, suitable for use as a decorator, e.g.:
            
                export = exporter.decorator()
                
                @export
                def yodogg():
                    ''' Yo dogg, I heard you like exporting '''
                    …
            
            … This should be done near the beginning of a module,
            to facilitate marking functions and other objects to be
            exported – q.v. the “all_and_dir()” method sub.
        """
        return self.export
    
    def __call__(self):
        """ Exporter instances are callable, for use in `__all__` definitions """
        return tuple(self.keys())
    
    def dir_function(self):
        """ Return a list containing the exported module names. """
        return list(self.keys())
    
    def all_and_dir(self):
        """ Assign a modules’ __all__ and __dir__ values, e.g.:
            
                __all__, __dir__ = exporter.all_and_dir()
            
            … This should be done near the end of a module, after
            all calls to `exporter.export(…)` (aka @export) have
            been made – q.v. the “decorator()” method supra.
        """
        return self(), self.dir_function
    
    def dir_and_all(self):
        """ Assign a modules’ __dir__ and __all__ values, e.g.:
            
                __dir__, __all__ = exporter.dir_and_all()
            
            … This should be done near the end of a module, after
            all calls to `exporter.export(…)` (aka @export) have
            been made – q.v. the “decorator()” method supra.
        """
        return self.dir_function, self() # OPPOSITE!
    
    def cache_info(self):
        """ Shortcut to get the CacheInfo namedtuple from the
            cached internal `thingname_search_by_id(…)` function,
            which is used in last-resort name lookups made by
            `determine_name(…)` during `export(…)` calls.
        """
        return thingname_search_by_id.cache_info()
    
    def _print_export_list(self):
        """ Print out a prettified (IMHO at any rate) representation of
            the current module export list.
            
            N.B. This function is a fucking illegible mess at the moment
        """
        from pprint import pformat
        exports = self.exports()
        keys = sorted(exports.keys(), key=case_sort, reverse=True)
        vals = (getitem(exports, key) for key in keys)
        print_separator()
        print("≠≠≠ EXPORTS: (length = %i)" % len(keys))
        print()
        od = OrderedDict.fromkeys(keys)
        od.update(zip(keys, vals))
        for idx, (key, value) in enumerate(reversed(od.items())):
            prelude = "%03d → [ %24s ] →" % (idx, key)
            print(prelude, " %s" % re.subn(r'\n', '\n' + " " * (len(prelude) + 2),
                                                                pformat(value,
                                                                        width=SEPARATOR_WIDTH,
                                                                        compact=True), flags=re.MULTILINE)[0])
    
    def _print_clade_histogram(self):
        """ Print out a bar graph of the current clade histogram.
            Like e.g. this:
            
            ---------------------------------------------------------------------------------
            ≠≠≠ CLASSIFICATION HISTOGRAM
            ≠≠≠ Clades: 8 (of 12)
            ≠≠≠ Things: 102 total, 0 unclassified
            
            00 → [       LAMBDA ] → 46 • 45% ••••••••••••••••••••••••••••••••••••••••••••••
            01 → [     FUNCTION ] → 28 • 27% ••••••••••••••••••••••••••••
            02 → [     SEQUENCE ] → 10 •  9% ••••••••••
            03 → [        CLASS ] →  8 •  7% ••••••••
            04 → [    SINGLETON ] →  3 •  2% •••
            05 → [       STRING ] →  3 •  2% •••
            06 → [   DICTIONARY ] →  2 •  1% ••
            07 → [       NUMBER ] →  2 •  1% ••
            
            ≠≠≠ 4 leaf clades:
            ≠≠≠ instance, iterable, metaclass, set
            
            ---------------------------------------------------------------------------------
        """
        clade_histogram = self.clade_histogram()
        total = sum(clade_histogram.values())
        unclassified = len(self) - total
        print_separator()
        print("≠≠≠ CLASSIFICATION HISTOGRAM")
        print("≠≠≠ Clades: %i (of %i)" % (len(clade_histogram), len(Clade)))
        print("≠≠≠ Things: %i total, %i unclassified" % (total, unclassified))
        print()
        for idx, (clade, count) in enumerate(sorted(clade_histogram.items(),
                                                    key=lambda item: item[1],
                                                    reverse=True)):
            prelude = "%02d → [ %12s ] → %2i • %s%%" % (idx,
                                                        clade.name,
                                                        count,
                                                        str(int((count / total) * 100)).rjust(2)) # percent
            print(prelude, "•" * count) # ASCII histogram bar graph
        print()
        leafclades = frozenset(Clade) - frozenset(clade_histogram.keys())
        if len(leafclades) > 0:
            print("≠≠≠ %i leaf clades:" % len(leafclades))
            print("≠≠≠ %s" % ", ".join(sorted(clade.to_string() for clade in leafclades)))
            print()
    
    def _print_cache_info(self):
        """ Print out the “CacheInfo” namedtuple from the search-by-ID
            cached thingname function (q.v. “cache_info()” method supra.)
        """
        from pprint import pprint
        print_separator()
        print("≠≠≠ THINGNAME SEARCH-BY-ID CACHE INFO:")
        print()
        pprint(self.cache_info())
    
    def print_diagnostics(self, module_all, module_dir):
        """ Pretty-print the current list of exported things """
        # Sanity-check the modules’ __dir__ and __all__ attributes
        exports = self.exports()
        
        assert list(module_all) == module_dir()
        assert len(module_all) == len(module_dir())
        assert len(module_all) == len(exports)
        
        # Pretty-print the export list
        self._print_export_list()
        
        # Pretty-print the clade histogram
        self._print_clade_histogram()
        
        # Print the cache info
        if PY3:
            self._print_cache_info()
        
        # Print closing separators
        print_separator()
        print()
    
    def __iter__(self):
        return iter(self.__exports__.keys())
    
    def __len__(self):
        return len(self.__exports__)
    
    def __contains__(self, key):
        return key in self.__exports__
    
    def __getitem__(self, key):
        return self.__exports__[key]
    
    def __setitem__(self, key, value):
        if key in self.__exports__:
            self.decrement_for_clade(self[key], named=key)
        self.increment_for_clade(value, named=key)
        self.__exports__[key] = value
    
    def __delitem__(self, key):
        self.decrement_for_clade(self[key], named=key)
        del self.__exports__[key]
    
    def __bool__(self):
        return len(self.__exports__) > 0

exporter = Exporter()
export = exporter.decorator()

# MODULE SEARCH FUNCTIONS: iterate and search modules, yielding
# names, thing values, and/or id(thing) values, matching by given
# by thing names or id(thing) values

@export
def itermodule(module):
    """ Get an iterable of `(name, thing)` tuples for all things
        contained in a given module (although it’ll probably work
        for classes and instances too – anything `dir()`-able.)
    """
    keys = tuple(key for key in sorted(dir(module)) \
                      if key not in BUILTINS)
    values = (getattr(module, key) for key in keys)
    return zip(keys, values)

@export
def moduleids(module):
    """ Get a dictionary of `(name, thing)` tuples from a module,
        indexed by the `id()` value of `thing`
    """
    out = {}
    for key, thing in itermodule(module):
        out[id(thing)] = (key, thing)
    return out

@export
def thingname(original, *modules):
    """ Find the name of a thing, according to what it is called
        in the context of a module in which it resides
    """
    inquestion = id(original)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for module in frozenset(modules):
            for key, thing in itermodule(module):
                if id(thing) == inquestion:
                    return key
    return None

def itermoduleids(module):
    """ Internal function to get an iterable of `(name, id(thing))`
        tuples for all things comntained in a given module – q.v.
        `itermodule(…)` implementation supra.
    """
    keys = tuple(key for key in dir(module) \
                      if key not in BUILTINS)
    ids = (id(getattr(module, key)) for key in keys)
    return zip(keys, ids)

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

# Q.v. `thingname_search_by_id(…)` function sub.
cache = lru_cache(maxsize=128, typed=False)

# This goes against all logic and reason, but it fucking seems
# to fix the problem of constants, etc showing up erroneously
# as members of the `__console__` or `__main__` modules –
# a problem which, I should mention, is present in the operation
# of the `pickle.whichmodule(…)` function (!)
sysmods = lambda: reversed(uniquify(*sys.modules.values()))

@cache
def thingname_search_by_id(thingID):
    """ Cached function to find the name of a thing, according
        to what it is called in the context of a module in which
        it resides – searching across all currently imported
        modules in entirely, as indicated from the inspection of
        `sys.modules.values()` (which is potentially completely
        fucking enormous).
        
        This function implements `thingname_search(…)` – q.v.
        the calling function code sub., and is also used in the
        implementdation of `determine_module(…)`, - also q.v.
        the calling function code sub.
        
        Caching courtesy the `functools.lru_cache(…)` decorator.
    """
    # Would you believe that the uniquify(…) call is absolutely
    # fucking necessary to use on `sys.modules`?! I checked and
    # on my system, like on all my REPLs, uniquifying the modules
    # winnowed the module list (and therefore, this functions’
    # search space) by around 100 fucking modules (!) every time!!
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for module in sysmods():
            for key, valueID in itermoduleids(module):
                if valueID == thingID:
                    return module, key
    return None, None

@export
def thingname_search(thing):
    """ Attempt to find the name for thing, using the logic from
        the `thingname(…)` function, applied to all currently
        imported modules, as indicated from the inspection of
        `sys.modules.values()` (which that, as a search space,
        is potentially fucking enormous).
        
        This function may be called by `determine_name(…)`. Its
        subordinate internal function, `thingname_search_by_id(…)`,
        uses the LRU cache from `functools`.
    """
    return thingname_search_by_id(id(thing))[1]

@export
def slots_for(cls):
    """ Get the summation of the `__slots__` tuples for a class and its ancestors """
    # q.v. https://stackoverflow.com/a/6720815/298171
    if not haspyattr(cls, 'mro'):
        return tuple()
    return tuple(chain.from_iterable(
                 getpyattr(ancestor, 'slots', tuple()) \
                       for ancestor in cls.__mro__))

@export
def nameof(thing, fallback=''):
    """ Get the name of a thing, according to either:
        >>> thing.__qualname__
        … or:
        >>> thing.__name__
        … optionally specifying a fallback string.
    """
    return determine_name(thing) or fallback

@export
def determine_module(thing):
    """ Determine in which module a given thing is ensconced,
        and return that modules’ name as a string.
    """
    return pyattr(thing, 'module', 'package') or \
           determine_name(
           thingname_search_by_id(id(thing))[0])

# UTILITY FUNCTIONS: dictionary-merging

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

# UTILITY STUFF: asdict(…)

@export
def asdict(thing):
    """ asdict(thing) → returns either thing, thing.__dict__, or dict(thing) as necessary """
    if isinstance(thing, dict):
        return thing
    if haspyattr(thing, 'dict'):
        return thing.__dict__
    return dict(thing)

# UTILITY STUFF: SimpleNamespace and Namespace

@export
class SimpleNamespace(object):
    
    """ Implementation courtesy this SO answer:
        • https://stackoverflow.com/a/37161391/298171
    """
    __slots__ = pytuple('dict', 'weakref')
    
    def __init__(self, *args, **kwargs):
        for arg in args:
            self.__dict__.update(asdict(arg))
        self.__dict__.update(kwargs)
    
    def __iter__(self):
        return iter(self.__dict__.keys())
    
    def __repr__(self):
        items = ("{}={!r}".format(key, self.__dict__[key]) for key in sorted(self))
        return "{}({}) @ {}".format(determine_name(type(self)),
                          ",\n".join(items),         id(self))
    
    def __eq__(self, other):
        return self.__dict__ == asdict(other)
    
    def __ne__(self, other):
        return self.__dict__ != asdict(other)

@export
class Namespace(SimpleNamespace, MutableMapping):
    
    """ Namespace adds the `get(…)`, `__len__()`, `__contains__(…)`, `__getitem__(…)`,
        `__setitem__(…)`, `__add__(…)`, and `__bool__()` methods to its ancestor class
        implementation SimpleNamespace.
        
        Since it implements a `get(…)` method, Namespace instances can be passed
        to `merge(…)` – q.v. `merge(…)` function definition supra.
        
        Additionally, Namespace furnishes an `__all__` property implementation.
    """
    __slots__ = tuple()
    
    winnower = re.compile(r"\{(?:\s+)(?P<stuff>.+)")
    
    def get(self, key, default=NoDefault):
        """ Return the value for key if key is in the dictionary, else default. """
        if default is NoDefault:
            return self.__dict__.get(key)
        return self.__dict__.get(key, default)
    
    @property
    def __all__(self):
        """ Get a tuple with all the stringified keys in the Namespace. """
        return tuple(str(key) for key in sorted(self))
    
    def __repr__(self):
        from pprint import pformat
        return "{}({}) @ {}".format(determine_name(type(self)),
                                    self.winnower.sub('{\g<stuff>',
                                              pformat(self.__dict__,
                                                      width=SEPARATOR_WIDTH)),
                                                      id(self))
    
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

VERBOTEN = pytuple('all', 'cached', 'loader', 'file', 'spec')
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

# Manually set `types.__file__` and related attributes:
setattr(types, '__file__',        __file__)
setattr(types, '__cached__',      cache_from_source(__file__))
setattr(types, '__package__',     os.path.splitext(
                                  os.path.basename(__file__))[0])

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

# UTILITY FUNCTIONS: is<something>() unary-predicates, and utility
# type-tuples with which said predicates use to make their decisions:

predicatenop = lambda *things: None

isabstractmethod = lambda method: getpyattr(method, 'isabstractmethod', False)
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

try:
    from six import string_types
except (ImportError, SyntaxError):
    string_types = uniquify(str, unicode)

bytes_types = (bytes, bytearray)
path_classes = tuplize(argparse.FileType, or_none(os, 'PathLike'), Path) # Path may be “None” in disguise
path_types = string_types + bytes_types + path_classes
file_types = (io.TextIOBase, io.BufferedIOBase, io.RawIOBase, io.IOBase)

callable_types = (types.Function,
                  types.Method,
                  types.Lambda,
                  types.BuiltinFunction,
                  types.BuiltinMethod)

if PY3 and not PYPY:
    callable_types += (
                  types.Coroutine,
                  types.ClassMethodDescriptor,
                  types.MemberDescriptor,
                  types.MethodDescriptor)


ispathtype = lambda cls: issubclass(cls, path_types)
ispath = lambda thing: graceful_issubclass(thing, path_types) or haspyattr(thing, 'fspath')
isvalidpath = lambda thing: ispath(thing) and os.path.exists(os.path.expanduser(thing))

class FilesystemError(IOError):
    """ A problem in dealing with the filesystem """
    pass

@export
def ensure_path_is_valid(pth):
    """ Raise an exception if we can’t write to the specified path """
    if os.path.exists(pth):
        if os.path.isdir(pth):
            raise FilesystemError("Can’t save over directory: %s" % pth)
        raise FilesystemError("Output file exists: %s" % pth)
    parent_dir = os.path.dirname(pth)
    if not os.path.isdir(parent_dir):
        raise FilesystemError("Directory doesn’t exist: %s" % parent_dir)

isnumber = lambda thing: graceful_issubclass(thing, numeric_types)
isnumeric = lambda thing: graceful_issubclass(thing, numeric_types)
isarray = lambda thing: graceful_issubclass(thing, array_types)
isstring = lambda thing: graceful_issubclass(thing, string_types)
isbytes = lambda thing: graceful_issubclass(thing, bytes_types)
ismodule = lambda thing: graceful_issubclass(thing, types.Module)
isfunction = lambda thing: isinstance(thing, (types.Function, types.Lambda)) or callable(thing)
islambda = lambda thing: pyattr(thing, 'lambda_name', 'name', 'qualname') == LAMBDA
ishashable = lambda thing: isinstance(thing, HashableABC)

# QUALIFIED-NAME FUNCTIONS: import by qualified name (like e.g. “yo.dogg.DoggListener”),
# assess a thing’s qualified name, etc etc.

QUALIFIER = '.'

@export
def dotpath_join(base, *addenda):
    """ Join dotpath elements together as one, á la os.path.join(…) """
    if base is None or base == '':
        return dotpath_join(*addenda)
    for addendum in addenda:
        if not base.endswith(QUALIFIER):
            base += QUALIFIER
        if addendum.startswith(QUALIFIER):
            if len(addendum) == 1:
                raise ValueError('operand too short: %s' % addendum)
            addendum = addendum[1:]
        base += addendum
    # N.B. this might be overthinking it -- 
    # maybe we *want* to allow dotpaths
    # that happen to start and/or end with dots?
    if base.endswith(QUALIFIER):
        return base[:-1]
    return base

@export
def dotpath_split(dotpath):
    """ For a dotted path e.g. `yo.dogg.DoggListener`,
        return a tuple `('DoggListener', 'yo.dogg')`.
        When called with a string containing no dots,
        `dotpath_split(…)` returns `(string, None)`.
    """
    head = dotpath.split(QUALIFIER)[-1]
    tail = dotpath.replace("%s%s" % (QUALIFIER, head), '')
    return head, tail != head and tail or None

@export
def qualified_import(qualified):
    """ Import a qualified thing-name.
        e.g. 'instakit.processors.halftone.FloydSteinberg'
    """
    import importlib
    if QUALIFIER not in qualified:
        raise ValueError("qualified name required (got %s)" % qualified)
    head, tail = dotpath_split(qualified)
    module = importlib.import_module(tail)
    imported = getattr(module, head)
    if DEBUG:
        print("Qualified Import: %s" % qualified)
    return imported

@export
def qualified_name_tuple(thing):
    """ Get the module/package and thing-name for a class or module.
        e.g. ('instakit.processors.halftone', 'FloydSteinberg')
    """
    return determine_module(thing), \
           dotpath_split(
           determine_name(thing))[0]

@export
def qualified_name(thing):
    """ Get a qualified thing-name for a thing.
        e.g. 'instakit.processors.halftone.FloydSteinberg'
    """
    mod_name, cls_name = qualified_name_tuple(thing)
    qualname = dotpath_join(mod_name, cls_name)
    if DEBUG:
        print("Qualified Name: %s" % qualname)
    return qualname

# OS UTILITIES: get the current process’ umask value

@lru_cache(maxsize=1)
def current_umask():
    """ Get the current umask value (cached on Python 3 and up). """
    mask = os.umask(0)
    os.umask(mask)
    return mask

@export
def masked_permissions(perms=0o666):
    """ Compute the permission bitfield, using the current umask value
        and a given permission octal number.
    """
    return perms & ~current_umask()

# ENUM UTILITIES: `isenum(…)` predicate; `enumchoices(…)` to return a tuple
# of strings naming an enum’s choices (like duh)
    
@export
def isenum(cls):
    """ isenum(cls) → boolean predicate, True if cls descends from Enum. """
    if not hasattr(cls, '__mro__'):
        return False
    return Enum in cls.__mro__

@export
def enumchoices(cls):
    """ isenum(cls) → Return a tuple of strings naming the members of an Enum class. """
    if not isenum(cls):
        return tuple()
    return tuple(choice.name for choice in cls)

# TEXT UTILITIES: `sanitize(…)` to remove high-code-point glyphs

@export
def sanitize(text):
    """ Remove specific unicode strings, in favor of ASCII-friendly versions """
    sanitized = unicode(text)
    for sanitizer, substitution in sanitize.sanitizers:
        sanitized, _ = sanitizer.subn(substitution, sanitized)
    return sanitized

# Regular expression compiler shortcut:
sanitize.re = lambda string: re.compile(string, re.MULTILINE)

# Sanitization regexes and their replacement strings:
sanitize.sanitizers = (
    (sanitize.re(r"[“”]"),              '"'),
    (sanitize.re(r"[‘’]"),              "'"),
    (sanitize.re(r"[«»]"),              ":"),
    (sanitize.re(r"[äáª]"),             "a"),
    (sanitize.re(r"[ëé]"),              "e"),
    (sanitize.re(r"[ïí]"),              "i"),
    (sanitize.re(r"[öóº]"),             "o"),
    (sanitize.re(r"[üú]"),              "u"),
    (sanitize.re(r"‽"),                 "?!"),
    (sanitize.re(r"¡"),                 "!"),
    (sanitize.re(r"¿"),                 "?"),
    (sanitize.re(r"±"),                 "+/-"),
    (sanitize.re(r"÷"),                 "/"),
    (sanitize.re(r"•"),                 "*"),
    (sanitize.re(r"ˆ"),                 "^"),
    (sanitize.re(r"†"),                 "<*>"),
    (sanitize.re(r"‡"),                 "<**>"),
    (sanitize.re(r"§"),                 "$"),
    (sanitize.re(r"¥"),                 "Y"),
    (sanitize.re(r"¢"),                 "c"),
    (sanitize.re(r"ƒ"),                 "f"),
    (sanitize.re(r"∫"),                 "S"),
    (sanitize.re(r"ß"),                 "ss"),
    (sanitize.re(r"ﬂ"),                 "fl"),
    (sanitize.re(r"ﬁ"),                 "fi"),
    (sanitize.re(r"£"),                 "lb."),
    (sanitize.re(r""),                 "Apple"),
    (sanitize.re(r"⌘"),                 "command"),
    (sanitize.re(r"∞"),                 "infinity"),
    (sanitize.re(r'√(?P<arg>[\w\d]*)'), 'sqrt(\g<arg>)'),
    (sanitize.re(r"¶"),                 "[P]"),
    (sanitize.re(r"[∂∆]"),              "d"),
    (sanitize.re(r"Ø"),                 "0"),
    (sanitize.re(r"→"),                 "->"),
    (sanitize.re(r"¬"),                 "-]"),
    (sanitize.re(r"…"),                 "..."),
    (sanitize.re(r"©"),                 "(c)"),
    (sanitize.re(r"®"),                 "(r)"),
    (sanitize.re(r"™"),                 "(tm)"),
    (sanitize.re(r"—"),                 "-"))


# THE MODULE EXPORTS:
export(print_separator, name='print_separator', doc="print_separator() → prints a line of dashes as wide as it believes the terminal width to be")
export(doctrim)
export(case_sort)

export(ispyname,        name='ispyname',        doc="ispyname(string) → boolean predicate, True if string looks like a __special__ (née “dunder”) python attribute")
export(pytuple,         name='pytuple',         doc="pytuple(*attrs) → turns ('do', 're', 'mi') into ('__do__', '__re__', '__mi__')")
export(determine_name)

export(AutoType)
export(ExportError,     name='ExportError',     doc="An exception raised during a call to export()")
export(ExportWarning,   name='ExportWarning',   doc="A warning issued during a call to export()")
export(NoDefault,       name='NoDefault',       doc="A singleton class with no value, used to represent a lack of a default value")

export(ismetaclass,     name='ismetaclass',     doc="ismetaclass(thing) → boolean predicate, True if thing is a class, descending from `type`")
export(isclass,         name='isclass',         doc="isclass(thing) → boolean predicate, True if thing is a class, descending from `object`")
export(isclasstype,     name='isclasstype',     doc="isclasstype(thing) → boolean predicate, True if thing is a class, descending from either `object` or `type`")

export(haspyattr,       name='haspyattr',       doc="haspyattr(thing, attribute) → boolean predicate, shortcut for hasattr(thing, '__%s__' % attribute)")
export(anyattrs,        name='anyattrs',        doc="anyattrs(thing, *attributes) → boolean predicate, shortcut for any(hasattr(thing, atx) for atx in attributes)")
export(allattrs,        name='allattrs',        doc="allattrs(thing, *attributes) → boolean predicate, shortcut for all(hasattr(thing, atx) for atx in attributes)")
export(anypyattrs,      name='anypyattrs',      doc="anypyattrs(thing, *attributes) → boolean predicate, shortcut for any(haspyattr(thing, atx) for atx in attributes)")
export(allpyattrs,      name='allpyattrs',      doc="allpyattrs(thing, *attributes) → boolean predicate, shortcut for all(haspyattr(thing, atx) for atx in attributes)")
export(isiterable,      name='isiterable',      doc="isiterable(thing) → boolean predicate, True if thing can be iterated over")
export(ismergeable,     name='ismergeable',     doc="ismergeable(thing) → boolean predicate, True if thing is a valid operand to merge(…) or merge_as(…)")

export(Clade)
export(clademap,        name='clademap')
export(sysmods,         name='sysmods',         doc="sysmods() → shortcut for reversed(tuple(frozenset(sys.modules.values()))) …OK? I know. It’s not my finest work, but it works.")

export(always,          name='always',          doc="always(thing) → boolean predicate that always returns True")
export(never,           name='never',           doc="never(thing) → boolean predicate that always returns False")
export(nuhuh,           name='nuhuh',           doc="nuhuh(thing) → boolean predicate that always returns None")
export(no_op,           name='no_op',           doc="no_op(thing, attribute[, default]) → shortcut for (attribute or default)")
export(or_none,         name='or_none',         doc="or_none(thing, attribute) → shortcut for getattr(thing, attribute, None)")
export(getpyattr,       name='getpyattr',       doc="getpyattr(thing, attribute[, default]) → shortcut for getattr(thing, '__%s__' % attribute[, default])")
export(getitem,         name='getitem',         doc="getitem(thing, item[, default]) → shortcut for thing.get(item[, default])")
export(accessor,        name='accessor',        doc="accessor(func, thing, *attributes) → return the first non-None value had by successively applying func(thing, attribute)")
export(searcher,        name='searcher',        doc="searcher(func, attribute, *things) → return the first non-None value had by successively applying func(thing, attribute)")

export(attr,            name='attr',            doc="Return the first existing attribute from a thing, given 1+ attribute names")
export(pyattr,          name='pyattr',          doc="Return the first existing __special__ attribute from a thing, given 1+ attribute names")
export(item,            name='item',            doc="Return the first existing item held by thing, given 1+ item names")
export(attr_search,     name='attr_search',     doc="Return the first-found existing attribute from a thing, given 1+ things")
export(pyattr_search,   name='pyattr_search',   doc="Return the first-found existing __special__ attribute from a thing, given 1+ things")
export(item_search,     name='item_search',     doc="Return the first-found existing item from a thing, given 1+ things")

export(thing_has,       name='thing_has',       doc="thing_has(thing, attribute) → boolean predicate, True if thing has the attribute (in either __dict__ or __slots__)")
export(class_has,       name='class_has',       doc="class_has(cls, attribute) → boolean predicate, True if cls is a class type and has the attribute (in either __dict__ or __slots__)")
export(isslotted,       name='isslotted',       doc="isslotted(thing) → boolean predicate, True if thing has both an __mro__ and a __slots__ attribute")
export(isdictish,       name='isdictish',       doc="isdictish(thing) → boolean predicate, True if thing has both an __mro__ and a __dict__ attribute")
export(isslotdicty,     name='isslotdicty',     doc="isslotdicty(thing) → boolean predicate, True if thing has __mro__, __slots__, and __dict__ attributes")

# NO DOCS ALLOWED:
export(BUILTINS,        name='BUILTINS')
export(DEBUG,           name='DEBUG')
export(ENCODING,        name='ENCODING')
export(LAMBDA,          name='LAMBDA')
export(MAXINT,          name='MAXINT')
export(PYPY,            name='PYPY')
export(QUALIFIER,       name='QUALIFIER')
export(SEPARATOR_WIDTH, name='SEPARATOR_WIDTH')
export(SINGLETON_TYPES, name='SINGLETON_TYPES')
export(TEXTMATE,        name='TEXTMATE')
export(VERBOTEN,        name='VERBOTEN')
export(current_umask,   name='current_umask')

export(types,           name='types',       doc=""" A Namespace instance containing aliases into the `types` module,
                                                    sans the irritating and lexically unnecessary “Type” suffix --
                                                    e.g. `types.ModuleType` can be accessed as just `types.Module`
                                                    from this Namespace, which is less pointlessly redundant and far
                                                    more typographically pleasing, like definitively.
                                                """)

export(isabstractmethod,                    doc="isabstractmethod(thing) → boolean predicate, True if thing is a method declared abstract with @abc.abstractmethod")
export(isabstract,                          doc="isabstract(thing) → boolean predicate, True if thing is an abstract method OR an abstract base class (née ABC)")
export(isabstractcontextmanager,            doc="isabstractcontextmanager(thing) → boolean predicate, True if thing decends from contextlib.AbstractContextManager")
export(iscontextmanager,                    doc="iscontextmanager(thing) → boolean predicate, True if thing is a context manager (either abstract or concrete)")

# NO DOCS ALLOWED:
export(numeric_types)
export(array_types)
export(bytes_types)
export(string_types)
export(path_classes)
export(path_types)
export(file_types)
export(callable_types)

export(ispathtype,      name='ispathtype',  doc="ispathtype(thing) → boolean predicate, True if thing is a path type")
export(ispath,          name='ispath',      doc="ispath(thing) → boolean predicate, True if thing seems to be path-ish instance")
export(isvalidpath,     name='isvalidpath', doc="isvalidpath(thing) → boolean predicate, True if thing is a valid path on the filesystem")

export(isnumber,        name='isnumber',    doc="isnumber(thing) → boolean predicate, True if thing is a numeric type or an instance of same")
export(isnumeric,       name='isnumeric',   doc="isnumeric(thing) → boolean predicate, True if thing is a numeric type or an instance of same")
export(isarray,         name='isarray',     doc="isarray(thing) → boolean predicate, True if thing is an array type or an instance of same")
export(isstring,        name='isstring',    doc="isstring(thing) → boolean predicate, True if thing is a string type or an instance of same")
export(isbytes,         name='isbytes',     doc="isbytes(thing) → boolean predicate, True if thing is a bytes-like type or an instance of same")
export(ismodule,        name='ismodule',    doc="ismodule(thing) → boolean predicate, True if thing is a module type or an instance of same")
export(isfunction,      name='isfunction',  doc="isfunction(thing) → boolean predicate, True if thing is of a callable function type")
export(islambda,        name='islambda',    doc="islambda(thing) → boolean predicate, True if thing is a function created with the «lambda» keyword")
export(ishashable,      name='ishashable',  doc="ishashable(thing) → boolean predicate, True if thing can be hashed, via the builtin `hash(thing)`")

# NO DOCS ALLOWED:
export(Exporter) # hahaaaaa

# Assign the modules’ `__all__` and `__dir__` using the exporter:
__all__, __dir__ = exporter.all_and_dir()

def test_attr_accessor():
    """ » Checking “attr(•) accessor …” """
    print(test_attr_accessor.__doc__)
    print()
    
    # plistlib on Python 2.x uses those ungainly `writePlistToString`
    # methods; on Python 3.x you have the more reasonable and expected
    # `dumps` and `loads` calls… thus, attr(…) will bridge the gap:
    import plistlib
    dump = attr(plistlib, 'dumps', 'writePlistToString')
    load = attr(plistlib, 'loads', 'readPlistFromString')
    assert dump is not None
    assert load is not None
    
    # When attr(…) can't find an attribute matching any of the names
    # provided, you get None back:
    wat = attr(plistlib, 'yo_dogg', 'wtf_hax')
    assert wat is None

def test_boolean_predicates():
    """ » Checking basic isXXX(•) functions … """
    print(test_boolean_predicates.__doc__)
    print()
    
    assert graceful_issubclass(int, int)
    
    assert ispathtype(str)
    assert ispathtype(bytes)
    if hasattr(os, 'PathLike'):
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

def test_lambda_naming():
    """ » Checking lambda naming … """
    print(test_lambda_naming.__doc__)
    
    lammy = lambda: None
    print("» lambda name = %s" % lammy.__name__)
    print("» lambda name = %s" % pyattr(lammy, 'name', 'qualname'))
    lammy_name = lammy.__name__
    lammy_pyattr_name = pyattr(lammy, 'name', 'qualname')
    lambda_name = LAMBDA
    assert lammy_name == lammy_pyattr_name
    assert lammy_name == lambda_name
    assert lammy_pyattr_name == lambda_name
    assert determine_name(lammy) == LAMBDA
    print()

def test_namespace_instance_docstring():
    """ » Checking “types.__doc__ …” """
    print(test_namespace_instance_docstring.__doc__)
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
    
    print('slots_for(type(types)) =', slots_for(type(types)))
    print_separator()
    print()
    
    print("» Checking “haspyattr.__doc__ …”")
    print()
    
    print_separator()
    print(haspyattr.__doc__)
    print_separator()
    print()
    
    
def test_dict_and_namespace_merge():
    from pprint import pprint
    
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
    pprint(merged)
    print_separator()
    print()

def test_qualified_name():
    """ » Checking “qualified_name(¬) …” """
    print(test_qualified_name.__doc__)
    print()
    
    assert qualified_name(BUILTINS) == '%s.BUILTINS' % __name__
    assert qualified_name(types) == '%s.types' % __name__
    
    print_separator()
    print('qualified_name(BUILTINS):', qualified_name(BUILTINS))
    print('qualified_name(types):', qualified_name(types))
    print_separator()
    print()

def test_qualified_import():
    """ » Checking “qualified_import(¬) …” """
    print(test_qualified_import.__doc__)
    print()
    print()
    
    print_python_banner = qualified_import('replenv.print_python_banner')
    print_warning       = qualified_import('replenv.print_warning')
    replenv_modules     = qualified_import('replenv.modules')
    python2_expires     = qualified_import('replenv.python2_expires')
    is_python2_dead     = qualified_import('replenv.is_python2_dead')
    
    assert qualified_name(print_python_banner) == 'replenv.print_python_banner'
    assert qualified_name(print_warning)       == 'replenv.print_warning'
    # assert qualified_name(replenv_modules)     == 'replenv.modules' # huh.
    # assert qualified_name(python2_expires)     == 'replenv.python2_expires'
    # assert qualified_name(is_python2_dead)     == 'replenv.is_python2_dead'
    
    print_separator()
    print('qualified_name(print_python_banner):', qualified_name(print_python_banner), '', repr(Clade.of(print_python_banner)))
    print('qualified_name(print_warning):      ',       qualified_name(print_warning), '      ', repr(Clade.of(print_warning)))
    print('qualified_name(replenv_modules):    ',     qualified_name(replenv_modules), '            ', repr(Clade.of(replenv_modules)))
    print('qualified_name(python2_expires):    ',     qualified_name(python2_expires), '    ', repr(Clade.of(python2_expires)))
    print('qualified_name(is_python2_dead):    ',     qualified_name(is_python2_dead), '    ', repr(Clade.of(is_python2_dead)))
    print_separator()
    print()

def test_determine_module():
    """ » Checking `determine_module(…)` against `pickle.whichmodule(…)` …"""
    print(test_determine_module.__doc__)
    print()
    import pickle
    mismatches = 0
    print_separator()
    for name, thing in exporter.exports().items():
        clade = Clade.of(thing, name_hint=name)
        determination = determine_module(thing)
        whichmodule = pickle.whichmodule(thing, None)
        try:
            assert determination == whichmodule
        except AssertionError:
            mismatches += 1
            print("»»» Module-lookup mismatch for %s “%s”" % (clade.to_string(), name))
            print("»»»   determine_module(…) → %s" % determination)
            print("»»» pickle.whichmodule(…) → %s" % whichmodule)
            print()
    
    print("≠≠≠ TOTAL EXPORTED THING COUNT: %i" % len(exporter))
    print("≠≠≠ TOTAL MISMATCHES FOUND: %i" % mismatches)
    print_separator()
    print()

def test():
    """ Inline tests for replutilities.py """
    
    # Print the full exporter diagnostics:
    exporter.print_diagnostics(__all__, __dir__)
    
    # Individual test sections:
    test_attr_accessor()
    test_lambda_naming()
    test_boolean_predicates()
    test_namespace_instance_docstring()
    test_dict_and_namespace_merge()
    test_qualified_name()
    if not TEXTMATE:
        test_qualified_import()
    test_determine_module()
    
    # Re-print search-by-ID cache info and clade histogram:
    print("≠≠≠ POST-HOC EXPORTER STATS:")
    exporter._print_clade_histogram()
    # print_separator()
    if PY3:
        exporter._print_cache_info()
    print_separator()
    print()
    

if __name__ == '__main__':
    test()