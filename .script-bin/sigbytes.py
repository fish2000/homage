#!/usr/bin/env python
# -*- encoding: utf-8 -*-
#
#       sigbytes.py
#
#       Read and print the first 8 or so bytes of a file,
#       For, like, tests and stuff
#       (c) 2015 Alexander Bohn, All Rights Reserved
#
"""
Usage:
  sigbytes.py INFILE...  [ -o OUTFILE   | --output=OUTFILE  ]
                         [ -s SIZE      | --size=SIZE       ]
                         [ -c           | --clean           ]
                         [ -V           | --verbose         ]
  
  sigbytes.py              -h           | --help
  sigbytes.py              -v           | --version

Arguments:
  INFILE                                Source file(s) to be read.

Options:
  -o OUTFILE --output=OUTFILE           Output file [default: stdout].
  -s SIZE --size=SIZE                   Size of bytes to read [default: 8].
  -c --clean                            Clean output: strip slash-x characters.
  -V --verbose                          Spew verbose output to stdout.
  -h --help                             Show this text.
  -v --version                          Print the program version and exit.

"""

from __future__ import print_function
from collections import OrderedDict
from os.path import exists, isdir, dirname, expanduser
from docopt import docopt
import sys, re

class ArgumentError(ValueError):
    """ An issue with the supplied arguments """
    pass

VERSION = u'sigbytes.py 0.2.0 © 2015-2019 Alexander Böhn / OST, LLC'

def cli(argv=None):
    if not argv:
        argv = sys.argv
    
    arguments = docopt(__doc__, argv=argv[1:],
                                help=True,
                                version=VERSION)
    
    # print(argv)
    # print(arguments)
    # sys.exit()
    
    if not len(arguments.get('INFILE')) > 0:
        raise ArgumentError("No input files")
    
    ipths = (expanduser(pth) for pth in arguments.get('INFILE'))
    opth = expanduser(arguments.get('--output'))
    siz = int(arguments.get('--size', 8))
    clean = bool(arguments.get('--clean'))
    verbose = bool(arguments.get('--verbose'))
    
    cleanr = lambda b: repr(b).replace(r'\x', ' ').upper()
    process_bytes = clean and cleanr or repr
    
    signatures = OrderedDict()
    
    for ipth in ipths:
        with open(ipth, 'rb') as fh:
            header_bytes = fh.read(siz)
            signatures.update({ ipth : header_bytes })
    
    if verbose:
        print("")
        print("*** Found %s byte signatures" % len(signatures))
    
    filehandle = None
    if opth != 'stdout':
        if exists(opth) or not isdir(dirname(opth)):
            raise ArgumentError("Bad output file")
        else:
            filehandle = open(opth, 'wb')
    
    for pth, signature in signatures.items():
        if opth == 'stdout':
            if verbose:
                print(">>> Header bytes (%s) for %s:" % (siz, pth))
                print(">>> %s" % process_bytes(signature)[2:-1].strip())
            else:
                print(process_bytes(signature)[2:-1].strip())
        else:
            filehandle.write(signature)
            filehandle.write(b"\n")
    
    if filehandle is not None:
        filehandle.flush()
        filehandle.close()
    elif verbose:
        print("")

def main():
    try:
        cli(sys.argv)
    except ArgumentError:
        print("[error] bad arguments passed:",
              file=sys.stderr)
        raise
    sys.exit(0)

if __name__ == '__main__':
    main()
