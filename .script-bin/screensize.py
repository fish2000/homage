#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# 
#       screensize.py
# 
#       Return a dictionary with information about the current screen --
#       resolution, viewable size rectanges, raw pixel dimensions, and
#       other assorted miscellaneous data and metadata.
#       Requires PyObjC; ANSI color output requires Pygments and Colorama.
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
  -D --debug        print human-readable formatted JSON.
  -A --ansi         print ANSI-highlighted formatted JSON (requires Pygments).
  -h --help         exit after showing this help text.
  -v --version      exit after showing this programs’ version.

Returns:
  JSON-formatted screen information.
"""
from __future__ import print_function, unicode_literals

import json
import sys
import os

DEBUG = bool(int(os.environ.get('DEBUG', '0'), base=10))

class DisplayAndExit(SystemExit):
    """ A signal to the caller to exit cleanly """
    pass

def screensize(*, screen_idx=0):
    """ Return a dict full of information about the “main screen” --
        as per the whim of the return value furnished by a call to
        the `(NSRect*)[NSScreen mainScreen]` method.
        
        This function currently requires a recent PyObjC.
    """
    # Import NSScreen from QuartzCore (*not* Foundation):
    from Quartz.QuartzCore import NSScreen
    
    # Pick an NSScreen instance, defaulting to the main screen:
    screen = (screen_idx > 1) and NSScreen.screens()[screen_idx] \
                               or NSScreen.mainScreen()
    
    # Gather dimension data from the main screen:
    devpixels = screen.devicePixelCounts()      # NSRect of the raw pixel counts
    visible = screen.visibleFrame()             # NSRect of the “visible” frame (?)
    frame = screen.frame()                      # NSRect of the screen frame
    depth = screen.depth()                      # Not sure what this is actually
    
    # Gather data from private/undocumented methods:
    settings = screen._currentSetting()         # Giant, miscellaneous info-dump
    displayID = screen._displayID()             # Internal Objective-C target ID
    menuBarHeight = screen._menuBarHeight()     # Height of the menu bar, like duh
    resolution = screen._resolution()           # Like as in DPI
    
    # Build an output dict stuffed with everything
    # we got back from the NSScreen instances:
    screen_info = {
            
        'devicePixels' : { 'width' : int(devpixels.width),
                          'height' : int(devpixels.height) },
        'visibleFrame' : { 'width' : int(visible.size.width),
                          'height' : int(visible.size.height) },
               'frame' : { 'width' : int(frame.size.width),
                          'height' : int(frame.size.height) },
          'resolution' : { 'width' : int(resolution.width),
                          'height' : int(resolution.height) },
            
       'menuBarHeight' : int(menuBarHeight),
               'depth' : int(depth),
           'displayID' : int(displayID),
            'settings' : dict(settings)
            
    }
    
    # Return the output dict:
    return screen_info

def to_json(dictionary, **options):
    return json.dumps(dictionary, **options)

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

def highlight(json_string):
    """ Highlight a given JSON string using inlin ANSI delimiters,
        using `pygments.highlight(…)` and the “Paraiso Dark” theme
    """
    import pygments, pygments.lexers, pygments.formatters
    LexerCls = pygments.lexers.find_lexer_class_by_name('json')
    formatter = pygments.formatters.get_formatter_by_name('terminal256')
    return pygments.highlight(json_string, formatter=formatter,
                                           lexer=LexerCls(style='paraiso-dark'))

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
    
    if '--help' in argv or '-h' in argv:
        show_help()
    elif '--version' in argv or '-v' in argv:
        show_version()
    
    # Deal with arguments:
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

__all__ = ('DEBUG', 'VERSION', 'screensize', 'to_json', 'print_color', 'highlight')
__dir__ = lambda: list(__all__)

if __name__ == '__main__':
    sys.exit(main(sys.argv, debug=DEBUG))
    # sys.exit(main(['python3', 'screensize.py', '--ansi'], debug=DEBUG))
