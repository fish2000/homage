#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import print_function
from collections import namedtuple
from replutilities import attr, ENCODING

import os
import mimetypes
import plistlib

# from instakit.utils.filesystem import Directory, TemporaryDirectory, FilesystemError
from instakit.utils.filesystem import FilesystemError

class plister(object):
    __slots__ = ('dumps', 'loads')
    
    def __init__(self):
        # This deals with Python 2/3 incompatibiliy:
        self.dumps = attr(plistlib, 'dumps', 'writePlistToString')
        self.loads = attr(plistlib, 'loads', 'readPlistFromString')

Resource = namedtuple('Resource', field_names=('url', 'data', 'mimetype', 'encoding'),
                                  defaults=dict(mimetype='text/html',
                                                encoding=ENCODING))

class WebArchiveError(IOError):
    pass

class WebArchive(object):
    __slots__ = ('path', 'primary', 'subordinates')
    
    # Reference to plistlib adapter:
    plist = plister()
    
    def __init__(self, pth):
        if not os.path.exists(pth):
            raise FilesystemError("invalid archive: %s" % pth)
        self.path = os.fspath(pth)
        self.primary = None
        self.subordinates = []
    
    def parse_resource(self, dictionary):
        encoding = dictionary.get('WebResourceTextEncodingName', ENCODING)
        mimetype = dictionary.get('WebResourceMIMEType', mimetypes.guess_type(
                            dictionary['WebResourceURL']))
        resource = Resource(dictionary['WebResourceURL'],
                        str(dictionary['WebResourceData'], encoding=encoding),
                            mimetype,
                            encoding)
        return resource
    
    def parse_file(self, pth):
        with open(self.path, 'rb') as handle:
            plistdata = handle.read()
        plist = self.plist.loads(plistdata)
        if 'WebMainResource' not in plist:
            raise WebArchiveError('no main resource found in archive: %s' % pth)
        self.primary = self.parse_resource(plist.get('WebMainResource'))
        subresources = plist.get('WebSubresources', [])
        for subresource in subresources:
            self.subordinates.append(self.parse_resource(subresource))
        
        