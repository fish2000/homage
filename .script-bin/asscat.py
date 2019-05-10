#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# 
#       asscat.py
# 
#       Generate a properly scaled 1x/2x/3x set of PNGs, optionally with
#       generated JSON metadata and/or subfolders, for each single given image.
#       For use with, like, all those Xcode asset catalogs and shit.
#       Requires the Pillow and docopt modules; optionally makes use of six.
# 
#       © 2016 - 2019 Alexander Böhn, All Rights Reserved.
# 
u"""
Usage:
  asscat.py SOURCE... [   -d DIRECTORY  |  --destination=DIRECTORY  ]
                      [   -s SIZE       |  --size=SIZE              ]
                      [   -i METHOD     |  --interpolation=METHOD   ]
                      [ [ -c NAME       |  --catalog=NAME         ] |
                        [ -D            |  --catalog-directory    ] ]
                      [   -f            |  --create-subfolders      ]
                      [   -j            |  --write-contents-json    ]
                      [   -C            |  --asset-catalog          ]
                      [   -V            |  --verbose                ]
  asscat.py               -S            |  --show-valid-sizes
  asscat.py               -I            |  --show-interpolation-methods
  asscat.py               -O            |  --show-save-options
  asscat.py               -h            |  --help
  asscat.py               -v            |  --version
  
Arguments:
  SOURCE                                source image file(s), in a format or
                                        formats that PIL or Pillow can decode.
  
Options:
  -d DIRECTORY --destination=DIRECTORY  destination directory [default: $CWD].
  -s SIZE --size=SIZE                   size (1x/2x/3x) of inputs [default: 3x].
  -i METHOD --interpolation=METHOD      interpolation method; one of either:
                                       “box”, “bilinear”, “bicubic”, “hamming”,
                                       “lanczos”, or “nearest” — q.v. the Pillow
                                        module source for notes [default: bicubic].
  -c NAME --catalog=NAME                to put generated files into a folder named
                                       “NAME.xcassets” or not [default: «Assets»].
  -D --catalog-directory               “-c Assets” shortcut – the Xcode default;
                                       ‘-c/--catalog’ and ‘-D/--catalog-directory’
                                        options are mutually exclusive.
  -f --create-subfolders                to use subfolders, e.g. Image.imageset/*,
                                        per the asset catalog structure Xcode and
                                       `assetutil` assume, or not [default: not].
  -j --write-contents-json              to write out a “Contents.json” index file,
                                        per the asset catalog structure Xcode and
                                       `assetutil` assume, or not [default: not].
  -C --asset-catalog                    shortcut for specifying “-D -f -j”.
  -V --verbose                          to spew extemporaneous blathery diagnostics
                                        to STDOUT throughout the course of this
                                        programs’ execution, or not [default: not].
  -S --show-valid-sizes                 exit after showing valid “size” arguments.
  -I --show-interpolation-methods       exit after showing possible interpolation-
                                        method arguments.
  -O --show-save-options                exit after showing the output image options
                                        as passed to ‘PIL.Image.Image.save(…)’.
  -h --help                             exit after showing this help text.
  -v --version                          exit after showing this programs’ version.
  
"""

from __future__ import print_function, unicode_literals
from collections import OrderedDict
from docopt import docopt, DocoptExit
from PIL import Image
import warnings
import sys, os
import json
import re

DEBUG = bool(os.environ.get('DEBUG', False))
PY3 = False

try:
    import six
except ImportError:
    PY3 = sys.version_info.major > 2
else:
    PY3 = six.PY3

if PY3:
    unicode = str

class DebugExit(SystemExit):
    """ A signal to the caller to exit cleanly """
    pass

class DisplayAndExit(SystemExit):
    """ Another signal to the caller to exit cleanly """
    pass

class ArgumentError(ValueError):
    """ An issue with the supplied arguments """
    pass

class FilesystemError(IOError):
    """ A problem in dealing with the filesystem """
    pass

class OptionsWarning(RuntimeWarning):
    """ A potential issue with the supplied arguments """
    pass

def interpol(name):
    """ Return a PIL/Pillow image interpolation method constant by name """
    return getattr(Image, name.upper())

# q.v. PIL.Image constants of the same (yet uppercased) names:
interpol.methods = frozenset({
                        "box",
                        "bilinear", "bicubic",
                        "hamming", "lanczos",
                        "nearest" })

interpol.default = "bicubic"

# for our purposes a “size” is one of these:
sizes = frozenset({ '1x', '2x', '3x' })

def sizer(factor=2):
    """ Return a lambda suitable for applying to an image size tuple """
    return lambda x: int(factor * x)

def scaler(image, factor=2, interpolation=interpol.default, verbose=False):
    """ Scale an image by a numeric (int or float) factor """
    width, height = image.size
    dim_scaler = sizer(factor)
    new_size = (dim_scaler(width),
                dim_scaler(height))
    if verbose:
        print("» Rescaling %s x %s image by factor %0.2f with method “%s”" % (
              width, height,
              factor,
              interpolation))
    return image.resize(new_size, interpol(interpolation))

def intify(size):
    """ Convert a size descriptor (e.g. 1x, 2x, 3x) to an integer """
    return int(size[0])

def scale(size, denominator_size):
    """ Compute a scaling factor from two size descriptors """
    denominator = intify(denominator_size)
    if denominator == 1:
        return intify(size)
    return float(intify(size)) / float(denominator)

def ensure_path_is_valid(pth):
    """ Raise an exception if we can’t write to the specified path """
    if os.path.exists(pth):
        if os.path.isdir(pth):
            raise FilesystemError("Can’t save over directory: %s" % pth)
        raise FilesystemError("Output file exists: %s" % pth)
    parent_dir = os.path.dirname(pth)
    if not os.path.isdir(parent_dir):
        raise FilesystemError("Directory doesn’t exist: %s" % parent_dir)

def save(image, pth, verbose=False):
    """ Save a PIL image object to a specified path """
    ensure_path_is_valid(pth)
    image.save(pth, **save.options)
    image_file = os.path.basename(pth)
    if verbose:
        statbuf = os.lstat(pth)
        print("» Wrote %i bytes to image file %s" % (statbuf.st_size,
                                                          image_file))
    return image_file

# PIL options for image file output:
save.options  = { 'compress_level' : 9,
                        'optimize' : True,
                          'format' : 'png' }

def generate(image, size, interpolation=interpol.default, verbose=False):
    """ Generate a full set of sized images – 1x/2x/3x – from a source
        image, whose scale factor is specified by a size descriptor
    """
    target_sizes = sizes - { size }
    out = { size : image }
    image.load()
    for new_size in sorted(target_sizes):
        out[new_size] = scaler(image, verbose=verbose,
                                      interpolation=interpolation,
                                      factor=scale(new_size, size))
    return out

def keyed(function):
    """ Assign an attribute “key” to a target function derived
        from that functions’ name – if the function has the name
       “yo_dogg_i_heard_you_like” the derived key attribute will
        be set as one would use as a command-line flag, to e.g.
       “--yo-dogg-i-heard-you-like”. Used to auto-assign the key
        values for functions that just print stuff and then exit:
    """
    code = None
    if hasattr(function, '__code__'):
        code = function.__code__
    elif hasattr(function, 'func_code'):
        code = function.func_code
    if code is not None:
        if hasattr(code, 'co_name'):
            dashed = keyed.underscore_re.subn('-', code.co_name)
            function.key = "--%s" % (dashed and dashed[0] or code.co_name)
            keyed.functions[function.key] = function
    return function

# Dictionary matching keyed function names to display-and-exit functions:
keyed.functions = {}

# Regular expression matching function-name underscores:
keyed.underscore_re = re.compile(r'_')

@keyed
def show_valid_sizes():
    """ Print a list of the valid sizes to STDOUT before exiting """
    print("» TOTAL VALID SIZE ARGUMENTS: %i" % len(sizes))
    print()
    for size in sorted(sizes):
        print("» “%s” – ∫cale ƒactor %i" % (size, intify(size)))

@keyed
def show_interpolation_methods():
    """ Print a list of the valid interpolation methods to STDOUT
        before exiting. These method names come from within Pillow,
        q.v. https://git.io/fhFxV
    """
    howmany = len(interpol.methods)
    print("» TOTAL VALID INTERPOLATION-MODE ARGUMENTS: %i" % howmany)
    print("• N.B. modes may be given in lowercase, UPPERCASE or MixedCase;")
    print("• For the (literal) source of these, q.v. https://git.io/fhFxV")
    print()
    by_constant = {}
    for method_name in interpol.methods:
        pil_constant = interpol(method_name)
        by_constant[pil_constant] = method_name
    for pil_constant in sorted(by_constant.keys()):
        method_name = by_constant[pil_constant]
        print("» ∞(%s) § “%s” %s" % (pil_constant,
                                     method_name.upper(),
                                     method_name == interpol.default and '» (default)' or ''))

@keyed
def show_save_options():
    """ Print the output image `save.options` dictionary, as passed to
       ‘PIL.Image.Image.save(…)’ internally, formatted in a human-readable
        fashion, before exiting.
    """
    print("» OUTPUT IMAGE SAVE OPTIONS:")
    print()
    print(dictionary_to_json(save.options))

def filename_with_size(filename, size):
    """ Compute an output filename for a size descriptor, using
        a given size descriptor and a source filename, with the
        format specified in the `save.options` settings dictionary
    """
    base, ext = os.path.splitext(filename)
    newname = base
    for matcher in filename_with_size.matchers:
        # … This, obviously, would be more efficient to use
        # a single, properly-generalized regex – but there
        # are only so many premature operations one can cram
        # into a single day, you know? I mean, you can’t risk
        # cutting into your gratuitously-circumlocutious-and-
        # verbose-comment-writing time or anything dogg.
        if matcher.search(base):
            newname = matcher.sub("", base)
            break
    newname += "@%s.%s" % (size, save.options.get('format'))
    return newname

# tuple of regexes for matching our size descriptors in filenames:
filename_with_size.matchers = tuple(re.compile(r"@%s" % size) for size in sorted(sizes))

def output_path_with_size(input_path, output_dir, size):
    """ Compute a destination image filename, including size, using the
        source images’ path, the destination directory, and the destination
        target images’ size descriptor
    """
    return os.path.join(output_dir, filename_with_size(
                                    os.path.basename(input_path),
                                    size))

CATALOG_NAME_DEFAULT = "Assets"

def catalog_folder_path(input_path, name=None):
    """ Derive a path for an asset catalog root from an output directory """
    return "%s.xcassets" % os.path.join(os.path.abspath(input_path),
                                        name or CATALOG_NAME_DEFAULT)

def imageset_folder_name(input_path):
    """ Derive the name for an imageset directory from an image path name """
    return "%s.imageset" % os.path.splitext(
                           os.path.basename(input_path))[0]

def dictionary_to_json(dictionary):
    """ Encode a Python dict as a JSON dictionary, using the same
        formatting properties used by Xcode in Apple’s asset catalog
        metadata JSON files
    """
    return json.dumps(dictionary, indent=4,
                                  separators=(',', ' : '),
                                  sort_keys=True)

# the “info” dictionary used throughout all JSON metadata:
JSON_INFO = { 'version' : 1,
               'author' : "asscat.py" }

# the filename for JSON metadata output:
JSON_FILENAME = "Contents.json"

def json_file_path(input_path):
    """ Derive a path for a JSON file from an output directory """
    return os.path.join(os.path.abspath(input_path), JSON_FILENAME)

def stub_json():
    """ Get the stub dictionary for an asset catalogs’ root-level metadata
        file – consisting only of an “info” entry – encoded as a JSON string
        ready for output """
    return dictionary_to_json({ 'info' : JSON_INFO })

def namelist_to_json(namelist, verbose=False):
    """ Transform a list of dictionaries – each dictionary specifying a filename
        (“filename”) and a size descriptor (“scale”) – into the proper structure
        of an asset catalog metadata dictionary, encode it as JSON, and return
        this JSON data as a string ready for output """
    if verbose:
        print("» Assembling metadata catalog for %s entries…" % len(namelist))
    outlist = []
    for namedict in namelist:
        namedict['idiom'] = 'universal'
        outlist.append(namedict)
    return dictionary_to_json({ 'images' : outlist,
                                'info'   : JSON_INFO })

UTF8_ENCODING = 'UTF-8'

def utf8_encode(source):
    """ Encode a source as bytes using the UTF-8 codec """
    if PY3:
        if type(source) is bytes:
            return source
        elif type(source) is bytearray:
            return bytes(source)
        return bytes(source, encoding=UTF8_ENCODING)
    if type(source) is unicode:
        return source.encode(UTF8_ENCODING)
    elif type(source) is bytearray:
        return str(source)
    return source

def write_to_path(data, pth, relative_to=None, verbose=False):
    """ Write data to a new file using a context-managed handle """
    ensure_path_is_valid(pth)
    bytestring = utf8_encode(data)
    with open(pth, "wb") as handle:
        handle.write(bytestring)
        handle.flush()
    if verbose:
        start = relative_to or os.path.dirname(pth)
        print("» Wrote %i bytes to %s" % (len(bytestring),
                                          os.path.relpath(pth,
                                                          start=start)))

VERSION = u'asscat.py 0.4.8 © 2016-2019 Alexander Böhn / OST, LLC'

def cli(argv=None, debug=False):
    """ The primary entry point for the asscat.py command-line tool.
        
        * Pass an argument dictionary to override the use of `sys.argv`
          for testing or targeted script-based usage. Pass “debug=True”
          to print the values for “argv” and “arguments” – the results
          of Docopt’s processing – and exit immediately thereafter.
        
        * asscat.py can process any sort of image file that PIL/Pillow
          is capable of reading; images it generates are always PNGs,
          as per Xcode’s finicky preferences.
        
        * Running asscat.py in verbose mode writes a bunch of messages
          to STDOUT; without specifying verbose mode, a successful run
          won’t write anything whatsoever to the console. Problematic
          command-line options or runtime issues will throw exceptions,
          resulting in termination since no attempts are made to handle
          exceptions with any sort of grace.
    """
    if not argv:
        argv = sys.argv
    
    # Get the command-line arguments and flags from Docopt:
    
    arguments = docopt(__doc__, argv=argv[1:],
                                help=True,
                                version=VERSION)
    
    # If called with “debug=True”, print argument values and exit immediately:
    
    if debug:
        from pprint import pprint
        print()
        print("» ARGV:")
        pprint(argv)
        print()
        print("» ARGUMENTS (post-Docopt):")
        pprint(arguments)
        raise DebugExit()
    
    # If we're just showing lists of valid args, just do that -- quickly call the
    # relevant function, and exit immediately:
    
    for key in keyed.functions.keys():
        if bool(arguments.pop(key)):
            keyed.functions[key]()
            raise DisplayAndExit()
    
    # Set up values and defaults for the remaining standard-execution arguments:
    
    ipths = (os.path.expanduser(pth) for pth in sorted(arguments.get('SOURCE', [])))
    opth = str(arguments.get('--destination', '$CWD'))
    interpolation = str(arguments.get('--interpolation', interpol.default)).lower()
    siz = str(arguments.get('--size', "3x")).lower()
    catalog_flag = bool(arguments.get('--catalog-directory'))
    catalog_name = unicode(arguments.get('--catalog', u"«Assets»")) # unicode == str on PY3
    makefolders = bool(arguments.get('--create-subfolders'))
    writejson = bool(arguments.get('--write-contents-json'))
    shortcut = bool(arguments.get('--asset-catalog'))
    verbose = bool(arguments.get('--verbose'))
    
    # Process arguments:
    
    if opth == "$CWD":
        opth = os.getcwd()
        warnings.warn("Writing images to working directory: %s" % opth,
                      OptionsWarning,
                      source=None, stacklevel=0)
    else:
        opth = os.path.expanduser(opth)
    
    if not siz.endswith('x'):
        siz = "%sx" % siz
    
    if shortcut:
        catalog_name = CATALOG_NAME_DEFAULT
        makefolders = True
        writejson = True
    
    if catalog_name == u"«Assets»":
        catalog_name = catalog_flag and CATALOG_NAME_DEFAULT or ""
    
    catalog = bool(catalog_name)
    
    # Validate arguments:
    
    if not len(arguments.get('SOURCE', [])) > 0:
        raise ArgumentError("No source files provided")
    
    if not os.path.isdir(opth):
        raise ArgumentError("Not a directory: %s" % opth)
    
    if not interpolation in interpol.methods:
        raise ArgumentError("Unknown interpolation method: %s" % interpolation)
    
    if not siz in sizes:
        raise ArgumentError("Unrecognized size: %s" % siz)
    
    if catalog:
        opth = catalog_folder_path(opth, catalog_name)
    
    if writejson:
        # Raise an error if a JSON file exists, before wasting time doing work
        # on all the rest of everything else:
        json_path = json_file_path(opth)
        if os.path.exists(json_path):
            raise FilesystemError("JSON metadata file exists: %s" % json_path)
    
    # Begin verbose output:
    
    if verbose:
        print()
    
    if shortcut and verbose:
        print("» Enabling all asset catalog write options:")
        print("» JSON, root catalog folder, imageset subfolders")
    
    # Create our internal-use data-storage structures:
    
    inputs = OrderedDict()
    outputs = OrderedDict()
    relative_to = catalog and os.path.dirname(opth) or opth
    filenames = []
    closed = 0
    
    # Open image handles for each input image file:
    
    for source_path in ipths:
        inputs[source_path] = Image.open(source_path)
    
    # Generate output images from input image files:
    
    if verbose:
        howmany = len(inputs)
        qualquan = howmany != 1 and "s" or ""
        print("» Generating %s imageset%s from %s source image%s…" % (
              howmany,
              qualquan, siz,
              qualquan))
    
    for source_path, image in inputs.items():
        outputs[source_path] = generate(image, siz,
                                        interpolation=interpolation,
                                        verbose=verbose)
    
    if verbose:
        print("» Generated image sizes:")
        for source_path, output_images in outputs.items():
            for size, image in sorted(output_images.items()):
                width, height = image.size
                print("» %s %s: %s x %s" % (source_path, size, width, height))
        print("» Image generation complete.")
    
    # Create the asset catalog root folder, if it’s called for:
    
    if catalog and not os.path.isdir(opth):
        os.makedirs(opth)
        if verbose:
            print("» Created asset catalog root folder %s" % opth)
    
    if verbose:
        print("» Writing %s output images to %s…" % (len(inputs) * len(sizes), opth))
    
    # This is the primary output loop, iterating over the generated images:
    
    for source_path, output_images in outputs.items():
        output_base_path = opth
        imageset_filenames = []
        
        if makefolders:
            imageset_dir = imageset_folder_name(source_path)
            output_base_path = os.path.join(opth, imageset_dir)
            if not os.path.isdir(output_base_path):
                os.makedirs(output_base_path)
                if verbose:
                    print("» Created imageset subfolder %s" % imageset_dir)
        
        for size, image in sorted(output_images.items()):
            image_filename = save(image, output_path_with_size(source_path,
                                                               output_base_path,
                                                               size), verbose=verbose)
            if writejson:
                imageset_filenames.append({
                              'scale'  :  size,
                           'filename'  :  image_filename })
        if writejson:
            if makefolders:
                # Write a Contents.json file referencing the image files present
                # in the current list of filenames, to the current subfolder:
                write_to_path(namelist_to_json(imageset_filenames,
                                               verbose=verbose),
                              json_file_path(output_base_path),
                              relative_to=relative_to,
                              verbose=verbose)
            else:
                # Tack the current list of filenames onto the master list:
                filenames.extend(imageset_filenames)
    
    # Write a Contents.json file, with either:
    #   1) only the stub JSON (if subfolders were created), or
    #   2) references to *all* of the generated image files (if we
    #      eschewed subfolders and wrote everything to one directory).
    
    if writejson:
        base_json = makefolders and stub_json() or namelist_to_json(filenames,
                                                                    verbose=verbose)
        write_to_path(base_json,
                      json_file_path(opth),
                      relative_to=relative_to,
                      verbose=verbose)
    
    if verbose:
        print("» File I/O complete.")
    
    # Close all open PIL/Pillow image handles:
    
    for output_images in outputs.values():
        for image in output_images.values():
            image.close()
            closed += 1
    
    if verbose:
        print("» Closed %i image handles." % closed)
    
    # End verbose output:
    
    if verbose:
        print("» Thank you for choosing asscat.py!")
        print()

def main(debug=False):
    """ Execute the primary command-line entry point function,
        trapping any exceptions of classes we expect might get raised:
    """
    try:
        cli(sys.argv, debug=debug)
    except ArgumentError:
        print("[error] bad arguments passed:",
              file=sys.stderr)
        raise
    except FilesystemError:
        print("[error] filesystem error encountered:",
              file=sys.stderr)
        raise
    except DocoptExit:
        # This is how default docopt usage gets printed:
        raise
    except DebugExit:
        # This is when we’re printing debug argument values:
        print()
        raise
    except DisplayAndExit:
        # This is when we’re printing lists of valid stuff:
        print()
        raise
    except Exception:
        print("[error] exception during execution:",
              file=sys.stderr)
        raise
    sys.exit(0)

if __name__ == '__main__':
    main(debug=DEBUG)
