#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import plistlib
import zict
import os

import appdirs
from replutilities import attr, isstring, isbytes

# UTILITY STUFF: Exceptions
class KeyValueError(ValueError):
    pass

# UTILITY STUFF: Directory class
try:
    from instakit.utils.filesystem import Directory

except (ImportError, SyntaxError):
    
    class Directory(object):
        
        def __init__(self, pth=None):
            self.target = pth and str(pth) or os.getcwd()
        
        @property
        def name(self):
            return self.target
        
        @property
        def exists(self):
            return os.path.isdir(self.target)
        
        def makedirs(self, pth=None):
            os.makedirs(os.path.abspath(
                        os.path.join(self.name, pth or os.curdir)), exist_ok=False)
            return self
        
        def __str__(self):
            return self.target


# UTILITY STUFF: AppDirs wrapper
class ReplEnvDirs(appdirs.AppDirs):
    
    def __init__(self):
        """ Initialize with a fixed “appname” parameter `replenv` """
        super(ReplEnvDirs, self).__init__(appname='replenv')
        self.mode = 'linux' # use Linux directory layout
    
    @property
    def mode(self):
        """ The “appdirs.system” global module variable controls the
            operation of the properties of all `appdirs.AppDirs` instances.
        """
        return appdirs.system
    
    @mode.setter
    def mode(self, value):
        if value not in ('darwin', 'linux'):
            raise ValueError("invalid mode: %s" % value)
        appdirs.system = value
    
    @property
    def site_config(self):
        return Directory(self.site_config_dir)
    
    @property
    def site_data(self):
        return Directory(self.site_data_dir)
    
    @property
    def user_cache(self):
        return Directory(self.user_cache_dir)
    
    @property
    def user_config(self):
        return Directory(self.user_config_dir)
    
    @property
    def user_data(self):
        return Directory(self.user_data_dir)
    
    @property
    def user_log(self):
        return Directory(self.user_log_dir)
    
    @property
    def user_state(self):
        return Directory(self.user_state_dir)


renvdirs = ReplEnvDirs()

if not renvdirs.user_config.exists:
    renvdirs.user_config.makedirs()

ENCODING = 'UTF-8'
zfile = zict.File(str(renvdirs.user_config), mode='a')
zutf8 = zict.Func(dump=attr(plistlib, 'dumps', 'writePlistToString'),
                  load=attr(plistlib, 'loads', 'readPlistFromString'),
                  d=zfile)
zfunc = zict.Func(dump=lambda value: isstring(value) and value.encode(ENCODING) or value,
                  load=lambda value: isbytes(value) and value.decode(ENCODING) or value,
                  d=zutf8)

def has(key):
    """ Test if a key is contained in the key-value store. """
    return key in zfunc

def count():
    """ Return the number of items in the key-value store. """
    return len(zfunc)

def get(key, default_value=None):
    """ Return a value from the ReplEnv user-config key-value store. """
    if not key:
        return default_value
    try:
        return zfunc[key]
    except KeyError:
        return default_value

def set(key, value):
    """ Set and return a value in the ReplEnv user-config key-value store. """
    if not key:
        raise KeyValueError("Non-Falsey key required (k: %s, v: %s)" % (key, value))
    if not value:
        raise KeyValueError("Non-Falsey value required (k: %s, v: %s)" % (key, value))
    zfunc[key] = value
    return get(key)

def delete(key):
    """ Delete a value from the ReplEnv user-config key-value store. """
    if not key:
        raise KeyValueError("Non-Falsey key required for deletion (k: %s)" % key)
    del zfunc[key]

def iterate():
    """ Return an iterator for the key-value store. """
    return iter(zfunc)

def keys():
    """ Return an iterable with all of the keys in the key-value store. """
    return zfunc.keys()

def values():
    """ Return an iterable with all of the values in the key-value store. """
    return zfunc.values()

def items():
    """ Return an iterable yielding (key, value) for all items in the key-value store. """
    return zfunc.items()

__dir__ = lambda: ('KeyValueError',
                   'has', 'count',
                   'get', 'set', 'delete', 'iterate',
                   'keys', 'values', 'items')
