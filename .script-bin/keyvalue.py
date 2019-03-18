#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# from __future__ import relative_import

from . import appdirs
from .replutils import attr

# UTILITY STUFF: configuration
try:
    from instakit.utils.filesystem import (which, TemporaryName, Directory,
                                                  TemporaryDirectory,
                                                  TemporaryNamedFile)
except (ImportError, SyntaxError):
    pass
else:
    
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

if False:
    import plistlib
    import zict

    if not renvdirs.user_config.exists:
        renvdirs.user_config.makedirs()

    zfile = zict.File(renvdirs.user_config.to_string(), mode='a')
    zfunc = zict.Func(dump=attr(plistlib, 'dumps', 'writePlistToString'),
                      load=attr(plistlib, 'loads', 'readPlistFromString'),
                      d=zfile)

