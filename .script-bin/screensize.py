#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# 
#       screensize.py
# 
#       Return a dictionary with information about the current screen --
#       resolution, viewable size rectanges, raw pixel dimensions, and
#       other assorted miscellaneous data and metadata.
# 
#       Requires PyObjC and NumPy; ANSI color output requires Pygments
#       and Colorama.
# 
#       © 2019 Alexander Böhn, All Rights Reserved.
# 
u"""
Usage:
  screensize.py   [ -D  |  --debug ] | 
  screensize.py   [ -A  |  --ansi  ]
  screensize.py     -h  |  --help
  screensize.py     -v  |  --version

Options:
  -D --debug        pretty-print human-readable JSON.
  -A --ansi         pretty-print ANSI-highlighted‡ JSON.
  -h --help         exit after showing this help text.
  -v --version      exit after showing this programs’ version.

Environment Variables:
  DEBUG             set to 1 to enable (same as passing -D/--debug)

Returns:
  JSON-formatted screen information.

Notes:
  ‡ ANSI syntax highlighting equires Pygments.
"""
from __future__ import print_function, unicode_literals

objc = None

import json
import sys
import os
import numpy

DEBUG = bool(int(os.environ.get('DEBUG', '0'), base=10))

class CoreGraphicsError(RuntimeError):
    """ An error was returned from a CoreGraphics function """
    pass

class DisplayAndExit(SystemExit):
    """ A signal to the caller to exit cleanly """
    pass

def swizzle(cls, SEL, func):
    """ Pythonic method swizzling! Courtesy pytest-osxnotify:
            https://github.com/dbader/pytest-osxnotify
    """
    old_IMP = getattr(cls, SEL, None)
    if old_IMP is None:
        # This will work on OS X <= 10.9
        old_IMP = cls.instanceMethodForSelector_(SEL)
    
    def wrapper(self, *args, **kwargs):
        return func(self, old_IMP, *args, **kwargs)
    
    new_IMP = objc.selector(
        wrapper,
        selector=old_IMP.selector,
        signature=old_IMP.signature
    )
    objc.classAddMethod(cls, SEL.encode(), new_IMP)

def swizzled_bundleIdentifier(self, original):
    return bool(os.environ.get('TM_PYTHON')) and 'com.macromates.TextMate' \
                                              or 'com.apple.Terminal'

def clamp(value, min=None, max=None):
    """ Clamp a value within the bounds of an unsigned 8-bit integer """
    min = min or clamp.info.min
    max = max or clamp.info.max
    return numpy.clip(value, a_min=min,
                             a_max=max)

# Specify the numpy type to use with `clamp(…)`:
clamp.type = numpy.uint8

# Supply the upper and lower bounds for the `clamp(…)` type:
clamp.info = numpy.iinfo(clamp.type)

def screensize(*, screen_idx=0):
    """ Return a dict full of information about the “main screen” --
        as per the whim of the return value furnished by a call to
        the `(NSRect*)[NSScreen mainScreen]` method.
        
        This function currently requires a recent release of PyObjC
    """
    # Memoize, and possibly swizzle, the `objc` module:
    global objc
    if not objc:
        objc = __import__('objc')
        swizzle(objc.lookUpClass('NSBundle'),
                                 'bundleIdentifier',
                                  swizzled_bundleIdentifier)
    
    # Import NSScreen from QuartzCore (*not* Foundation):
    import Quartz
    import Quartz.QuartzCore
    _ = dir(Quartz.QuartzCore)
    NSScreen = objc.lookUpClass('NSScreen')
    
    # Get the “active display list” via a CoreGraphics call --
    # If you have two displays set up to mirror one another,
    # this function counts them as one thing; for all the things
    # regardless of mirroring, one calls `CGGetOnlineDisplayList`
    # instead, with like the same call signature and shit.
    dmax = clamp.info.max
    error, screens, screen_count = Quartz.CGGetActiveDisplayList(dmax, None, None)
    
    # Error value check:
    if error:
        raise CoreGraphicsError("CGGetActiveDisplayList(…) error: %s" % error)
    
    # Clamp “screen_idx” argument before indexing with it:
    screen_idx = clamp(screen_idx, min=0, max=screen_count)
    
    # Pick an NSScreen instance, defaulting to the main screen:
    screen = (screen_idx > 0) and NSScreen.screens()[screen_idx] \
                               or NSScreen.mainScreen()
    
    # Gather dimension data from the specified screen,
    # using the public NSScreen API:
    devpixels = screen.devicePixelCounts()      # NSSize of the raw pixel counts
    visible = screen.visibleFrame()             # NSRect of the “visible” frame (?)
    frame = screen.frame()                      # NSRect of the screen frame
    depth = screen.depth()                      # Int -- not sure what this is actually
    
    # Gather additional data from the specified screen,
    # from private and/or undocumented methods:
    settings = screen._currentSetting()         # Giant, miscellaneous info-dump
    displayID = screen._displayID()             # Internal Objective-C target ID
    menuBarHeight = screen._menuBarHeight()     # Height of the menu bar, like duh
    resolution = screen._resolution()           # NSSize, like as in DPI
    
    # Build an output dict stuffed with everything
    # we got back from the NSScreen instances:
    screen_info = {
            
        'devicePixels' : { 'width' : int(devpixels.width),
                          'height' : int(devpixels.height) },
        'visibleFrame' : { 'width' : int(visible.size.width),
                          'height' : int(visible.size.height) },
               'frame' : { 'width' : int(frame.size.width),
                          'height' : int(frame.size.height) },
          'resolution' : {     'x' : int(resolution.width),
                               'y' : int(resolution.height) },
            
       'menuBarHeight' : int(menuBarHeight),
               'depth' : int(depth),
           'displayID' : int(displayID),
         'displayList' : list(screens),
        'displayCount' : int(screen_count),
            'settings' : dict(settings)
            
    }
    
    # Manually release the NSScreen class and instance,
    # and the settings NSDictionary:
    del NSScreen
    del settings
    del screen
    
    # Return the output dict:
    return screen_info

def to_json(dictionary, **options):
    """ Format a JSON dictionary as a string, with options """
    return json.dumps(dictionary, **options)

# Set up formatting options:
to_json.options = {}

to_json.options['debug']   = dict(indent=4,
                                  allow_nan=False,
                                  skipkeys=False,
                                  sort_keys=False)

to_json.options['release'] = dict(skipkeys=True,
                                  sort_keys=True,
                                  separators=(',', ':'))

def print_color(text, color='', reset=None):
    """ Print text in ANSI color, using optional inline markup
        from `colorama` for terminal color-escape delimiters
    """
    import colorama
    colorama.init()
    for line in text.splitlines():
        print(color + line, sep='')
    print(reset or colorama.Style.RESET_ALL, end='')

def highlight(json_string, language='json',
                             markup='terminal256',
                              style='paraiso-dark'):
    """ Highlight a JSON string with inline 256-color ANSI markup,
        using `pygments.highlight(…)` and the “Paraiso Dark” theme
    """
    import pygments, pygments.lexers, pygments.formatters
    LexerCls = pygments.lexers.find_lexer_class_by_name(language)
    formatter = pygments.formatters.get_formatter_by_name(markup, style=style)
    return pygments.highlight(json_string, lexer=LexerCls(), formatter=formatter)

VERSION = u'screensize.py 0.1.0 © 2019 Alexander Böhn / OST, LLC'

def show_help():
    """ Show the help information """
    print(__doc__) # No docopt!
    raise DisplayAndExit()

def show_version():
    """ Show the version string """
    print(VERSION) # No docopt!
    raise DisplayAndExit()

def main(argv=None, debug=False):
    """ Main entry point for the screensize.py CLU """
    if not argv:
        argv = sys.argv
    
    # Dispatch any print-and-exit args, if present:
    if '--help' in argv or '-h' in argv:
        show_help()
    elif '--version' in argv or '-v' in argv:
        show_version()
    
    # Deal with normal arguments:
    ansi = '--ansi' in argv or '-A' in argv
    debug = ansi or debug or ('--debug' in argv or '-D' in argv)
    ansi &= not bool(os.environ.get('TM_PYTHON'))
    
    # Call `screensize()`, returning the screen info dict:
    screen_info = screensize()
    
    # Set JSON options -- format for readability when debugging:s
    options = debug and to_json.options['debug'] \
                     or to_json.options['release']
    
    # JSON-ify and print the info dict to stdout:
    if ansi:
        print_color(highlight(to_json(screen_info, **options)))
    else:
        print(to_json(screen_info, **options), file=sys.stdout)
    
    # All is well, return to zero:
    return 0

__all__ = ('DEBUG', 'VERSION', 'clamp', 'screensize',
                               'to_json', 'print_color',
                               'highlight')

__dir__ = lambda: list(__all__)

if __name__ == '__main__':
    sys.exit(main(sys.argv, debug=DEBUG))
    # sys.exit(main(['python3', 'screensize.py', '--ansi'], debug=DEBUG))