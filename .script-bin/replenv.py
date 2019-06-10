# -*- encoding: utf-8 -*-
"""
replenv.py

• Default module imports and other configgy code,
• For generic use in python repls – both the python2 and python3 interactive
  interpreters, as well as bpython, ipython, ptpython, pyzo, PyCharm, and
  whatever else; code specific to any given repl module lives in the config
  files, per whatever that packages’ demands may be.

Created by FI$H 2000 on 2019-02-27.
Copyright (c) 2012-2025 Objects In Space And Time, LLC. All rights reserved.

"""
from __future__ import print_function, unicode_literals

if __name__ == '__main__':
    # take your executions elsewhere:
    raise RuntimeError(
        "%s is for module import or star-import only" % __file__)

# Python version figlet banners:
banners = {}

banners['python3.x'] = """
                  888    888                         .d8888b.                
                  888    888                        d88P  Y88b               
                  888    888                             .d88P               
88888b.  888  888 888888 88888b.   .d88b.  88888b.      8888"      888  888  
888 "88b 888  888 888    888 "88b d88""88b 888 "88b      "Y8b.     `Y8bd8P'  
888  888 888  888 888    888  888 888  888 888  888 888    888       X88K    
888 d88P Y88b 888 Y88b.  888  888 Y88..88P 888  888 Y88b  d88P d8b .d8""8b.  
88888P"   "Y88888  "Y888 888  888  "Y88P"  888  888  "Y8888P"  Y8P 888  888  
888           888                                                            
888      Y8b d88P                                                            
888       "Y88P"                                                             
                                                                             
"""

banners['python3.8'] = """
                  888    888                         .d8888b.       .d8888b.  
                  888    888                        d88P  Y88b     d88P  Y88b 
                  888    888                             .d88P     Y88b .d88P 
88888b.  888  888 888888 88888b.   .d88b.  88888b.      8888"       "888888"  
888 "88b 888  888 888    888 "88b d88""88b 888 "88b      "Y8b.     .d8Y""Y8b. 
888  888 888  888 888    888  888 888  888 888  888 888    888     888    888 
888 d88P Y88b 888 Y88b.  888  888 Y88..88P 888  888 Y88b  d88P d8b Y88b  d88P 
88888P"   "Y88888  "Y888 888  888  "Y88P"  888  888  "Y8888P"  Y8P  "Y8888P"  
888           888                                                             
888      Y8b d88P                                                             
888       "Y88P"                                                              
                                                                              
"""

banners['python3.7'] = """
                  888    888                         .d8888b.      8888888888 
                  888    888                        d88P  Y88b           d88P 
                  888    888                             .d88P          d88P  
88888b.  888  888 888888 88888b.   .d88b.  88888b.      8888"          d88P   
888 "88b 888  888 888    888 "88b d88""88b 888 "88b      "Y8b.      88888888  
888  888 888  888 888    888  888 888  888 888  888 888    888       d88P     
888 d88P Y88b 888 Y88b.  888  888 Y88..88P 888  888 Y88b  d88P d8b  d88P      
88888P"   "Y88888  "Y888 888  888  "Y88P"  888  888  "Y8888P"  Y8P d88P       
888           888                                                             
888      Y8b d88P                                                             
888       "Y88P"                                                              
                                                                              
"""

banners['python2.7'] = """
                  888    888                         .d8888b.      8888888888 
                  888    888                        d88P  Y88b           d88P 
                  888    888                               888          d88P  
88888b.  888  888 888888 88888b.   .d88b.  88888b.       .d88P         d88P   
888 "88b 888  888 888    888 "88b d88""88b 888 "88b  .od888P"       88888888  
888  888 888  888 888    888  888 888  888 888  888 d88P"            d88P     
888 d88P Y88b 888 Y88b.  888  888 Y88..88P 888  888 888"       d8b  d88P      
88888P"   "Y88888  "Y888 888  888  "Y88P"  888  888 888888888  Y8P d88P       
888           888                                                             
888      Y8b d88P                                                             
888       "Y88P"                                                              
                                                                              
"""

banners['pypy3.x'] = """
                                     .d8888b.                                 
                                    d88P  Y88b                                
                                         .d88P                                
88888b.  888  888 88888b.  888  888     8888"      888  888                   
888 "88b 888  888 888 "88b 888  888      "Y8b.     `Y8bd8P'                   
888  888 888  888 888  888 888  888 888    888       X88K                     
888 d88P Y88b 888 888 d88P Y88b 888 Y88b  d88P d8b .d8""8b.                   
88888P"   "Y88888 88888P"   "Y88888  "Y8888P"  Y8P 888  888                   
888           888 888           888                                           
888      Y8b d88P 888      Y8b d88P                                           
888       "Y88P"  888       "Y88P"                                            
                                                                              
"""

banners['pypy3.8'] = """
                                     .d8888b.       .d8888b.                  
                                    d88P  Y88b     d88P  Y88b                 
                                         .d88P     Y88b .d88P                 
88888b.  888  888 88888b.  888  888     8888"       "888888"                  
888 "88b 888  888 888 "88b 888  888      "Y8b.     .d8Y""Y8b.                 
888  888 888  888 888  888 888  888 888    888     888    888                 
888 d88P Y88b 888 888 d88P Y88b 888 Y88b  d88P d8b Y88b  d88P                 
88888P"   "Y88888 88888P"   "Y88888  "Y8888P"  Y8P  "Y8888P"                  
888           888 888           888                                           
888      Y8b d88P 888      Y8b d88P                                           
888       "Y88P"  888       "Y88P"                                            
                                                                              
"""

banners['pypy3.7'] = """
                                     .d8888b.      8888888888                 
                                    d88P  Y88b           d88P                 
                                         .d88P          d88P                  
88888b.  888  888 88888b.  888  888     8888"          d88P                   
888 "88b 888  888 888 "88b 888  888      "Y8b.      88888888                  
888  888 888  888 888  888 888  888 888    888       d88P                     
888 d88P Y88b 888 888 d88P Y88b 888 Y88b  d88P d8b  d88P                      
88888P"   "Y88888 88888P"   "Y88888  "Y8888P"  Y8P d88P                       
888           888 888           888                                           
888      Y8b d88P 888      Y8b d88P                                           
888       "Y88P"  888       "Y88P"                                            
                                                                              
"""

banners['pypy3.6'] = """
                                     .d8888b.       .d8888b.                  
                                    d88P  Y88b     d88P  Y88b                 
                                         .d88P     888                        
88888b.  888  888 88888b.  888  888     8888"      888d888b.                  
888 "88b 888  888 888 "88b 888  888      "Y8b.     888P "Y88b                 
888  888 888  888 888  888 888  888 888    888     888    888                 
888 d88P Y88b 888 888 d88P Y88b 888 Y88b  d88P d8b Y88b  d88P                 
88888P"   "Y88888 88888P"   "Y88888  "Y8888P"  Y8P  "Y8888P"                  
888           888 888           888                                           
888      Y8b d88P 888      Y8b d88P                                           
888       "Y88P"  888       "Y88P"                                            
                                                                              
"""

banners['pypy2.7'] = """
                                     .d8888b.      8888888888                 
                                    d88P  Y88b           d88P                 
                                           888          d88P                  
88888b.  888  888 88888b.  888  888      .d88P         d88P                   
888 "88b 888  888 888 "88b 888  888  .od888P"       88888888                  
888  888 888  888 888  888 888  888 d88P"            d88P                     
888 d88P Y88b 888 888 d88P Y88b 888 888"       d8b  d88P                      
88888P"   "Y88888 88888P"   "Y88888 888888888  Y8P d88P                       
888           888 888           888                                           
888      Y8b d88P 888      Y8b d88P                                           
888       "Y88P"  888       "Y88P"                                            
                                                                              
"""

# Add miscellaneous necessities:
from PIL import Image
from pprint import pprint, pformat
import sys, os, re
import appdirs
import argparse
import collections
import colorama
import contextlib
import copy
import datetime
import decimal
import functools
import inspect
import itertools
import math
import requests
import shutil
import six
import sysconfig
import termcolor
import types
import xerox

# Determine if we’re on PyPy:
PYPY = hasattr(sys, 'pypy_version_info')
prefix = PYPY and 'pypy' or 'python'

# Configure ANSI-color python banner, per python version:
if six.PY3:
    banner = banners.get('%s3.%s' % (prefix, sys.version_info.minor), banners['%s3.x' % prefix])
    banner_color = colorama.Fore.CYAN
else:
    banner = banners['%s2.7' % prefix]
    banner_color = colorama.Fore.LIGHTGREEN_EX

def print_python_banner(text, color,
                              reset=colorama.Style.RESET_ALL):
    for line in text.splitlines():
        print(color + line, sep='')
    print(reset, end='')

def print_warning(text, color=colorama.Fore.RED,
                        reset=colorama.Style.RESET_ALL):
    print(color + text, sep='')
    print(reset, end='')

# Practice safe star-importing:
__all__ = ('Image',
           'pprint', 'pformat',
           'sys', 'os', 're',
           'appdirs',
           'argparse',
           'collections',
           'colorama',
           'contextlib',
           'copy',
           'datetime',
           'decimal',
           'functools',
           'inspect',
           'itertools',
           'math',
           'reduce',
           'requests',
           'shutil',
           'six',
           'sysconfig',
           'termcolor',
           'types',
           'xerox',
           'print_python_banner',
           'print_warning', 'banner',
                            'banner_color',
           'modules')

now = datetime.datetime.now
python2_expires = 'January 1st, 2020'
is_python2_dead = now() >= now().strptime(python2_expires, '%B %dst, %Y')

try:
    from functools import reduce
except (ImportError, SyntaxError):
    pass

try:
    if six.PY3:
        from replpy3 import *
except (AttributeError, SyntaxError):
    pass
else:
    if six.PY3:
        __all__ += (u'Σ',)

try:
    import numpy
    import scipy
except (ImportError, SyntaxError):
    pass
else:
    # Extend `__all__`:
    __all__ += ('numpy', 'scipy')

try:
    import colorio
    import colormath
except (ImportError, SyntaxError):
    pass
else:
    # Extend `__all__`:
    __all__ += ('colorio', 'colormath')

try:
    import dateutil
except (ImportError, SyntaxError):
    pass
else:
    # Extend `__all__`:
    __all__ += ('dateutil',)

try:
    import abc
    import collections.abc as collectionsabc
    import asciiplotlib
except (ImportError, SyntaxError):
    pass
else:
    # Extend `__all__`:
    __all__ += ('abc', 'collectionsabc', 'asciiplotlib')

try:
    from halogen.filesystem import (which, TemporaryName, Directory,
                                           TemporaryDirectory,
                                           TemporaryNamedFile)
except (ImportError, SyntaxError):
    pass
else:
    # Extend `__all__`:
    __all__ += ('which', 'TemporaryName', 'Directory',
                    'TemporaryDirectory',
                    'TemporaryNamedFile')

try:
    from instakit.utils.static import asset
except (ImportError, SyntaxError):
    pass
else:
    # Extend `__all__`:
    __all__ += ('asset', 'image_paths', 'catimage')
    # Prepare a list of readily open-able image file paths:
    image_paths = list(map(
        lambda image_file: asset.path('img', image_file),
            asset.listfiles('img')))
    # I do this practically every time, so I might as well do it here:
    catimage = Image.open(image_paths[0])

# `__dir__` listifies `__all__`:
__dir__ = lambda: list(__all__)
modules = tuple(__dir__())

# Print python banner before end-of-module --
# if running in TextMate, we use `sys.stderr` instead of ANSI colors,
# as that’s the only way to get any sort of colored output in TextMate’s
# console output window:
if os.environ.get('TM_PYTHON'):
    print(banner, file=sys.stderr)
else:
    colorama.init()
    print_python_banner(banner, banner_color)

if not six.PY3:
    if is_python2_dead:
        warning = u"∞§• ¡LOOK OUT! Python 2.x has been officially declared DEAD!!!!!!!\n"
    else:
        warning = u"∞§• ¡BEWARE! Python 2.x will perish when the clock strikes 2020!!!\n"
    if os.environ.get('TM_PYTHON'):
        print(warning, file=sys.stderr)
    else:
        print_warning(warning)