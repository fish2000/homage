#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

import os, sys

SSID = os.getenv('SECURITYSESSIONID')

from clu.constants import (DEBUG, HOSTNAME, XDG_RUNTIME_BASE,
                                            XDG_RUNTIME_DIR,
                                            XDG_RUNTIME_MODE, TEXTMATE)

from clu.fs import rm_rf, Directory, FilesystemError
from clu.predicates import attr
from clu.repl.ansi import Text, print_ansi
from clu.sanitizer import utf8_decode

BASEDIR = XDG_RUNTIME_BASE
SYMLINK = XDG_RUNTIME_DIR
CURRENT = os.path.split(SYMLINK)[1]

def name_xdg_runtime_dir(namebase=SSID):
    return HOSTNAME.lower() + '-' + namebase.lower()

def make_xdg_runtime_dir(directory, mode=XDG_RUNTIME_MODE):
    runtime_dir = directory.subdirectory(name_xdg_runtime_dir())
    if runtime_dir.exists:
        rm_rf(runtime_dir)
    runtime_dir.makedirs(mode=mode)
    return runtime_dir

def enumerate_dirs(directory):
    return (pth for pth in iter(directory) \
                 if pth.startswith("%s%s" % (HOSTNAME.lower(), '-')))

def create_symlink(directory, runtime_dir):
    if CURRENT in directory:
        raise FilesystemError("Symlink “%s” already exists" % SYMLINK)
    runtime_dir.symlink(directory.subpath(CURRENT))
    return CURRENT in directory

def remove_symlink(directory):
    if CURRENT in directory:
        os.unlink(directory.subpath(CURRENT))
    return CURRENT not in directory

def remove_existing_dirs(directory):
    if len(directory) > 0:
        if DEBUG:
            return remove_symlink(directory)
        else:
            return all(rm_rf(pth) for pth in enumerate_dirs(directory)) \
                                         and remove_symlink(directory)
    return True

def print_launchd_plist():
    import plistlib
    plist_dumps = attr(plistlib, 'dumps', 'writePlistToString')
    plist_dict = dict(Label="ost.xdg-runtime.script",
                      Program=sys.executable,
                      ProgramArguments=[__file__],
                      RunAtLoad=True,
                      KeepAlive=False)
    print_ansi(utf8_decode(plist_dumps(plist_dict, sort_keys=False)),
               color=(TEXTMATE and Text.NOTHING \
                                or Text.LIGHTCYAN_EX))

def create_xdg_runtime_dir():
    """ Create the XDG_RUNTIME_DIR directory """
    basedir = Directory(BASEDIR)
    
    # First, clear existing directories:
    if not remove_existing_dirs(basedir):
        raise FilesystemError("Couldn’t clear subdirs from %s" % str(basedir))
    
    # Next, make a new runtime directory:
    runtime_dir = make_xdg_runtime_dir(basedir)
    if not runtime_dir.exists:
        raise FilesystemError("Couldn’t create XDG_RUNTIME_DIR %s" % str(runtime_dir))
    
    # Next, symlink the new directory:
    if not create_symlink(basedir, runtime_dir):
        raise FilesystemError("Couldn’t symlink XDG_RUNTIME_DIR %s" % SYMLINK)
    
    return SYMLINK

def main():
    """ Main entry point for xdg-runtime.py script """
    
    pass

if __name__ == '__main__':
    print_launchd_plist()
