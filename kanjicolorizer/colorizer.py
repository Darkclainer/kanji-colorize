#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

# colorizer.py is part of kanji-colorize which makes KanjiVG data
# into colored stroke order diagrams
#
# Copyright 2012 Cayenne Boyer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <http://www.gnu.org/licenses/>.

# Usage: See README and/or run with --help option.
# Configuration is now specified on the command line instead of here.

# Note: this module is in the middle of being refactored.

import os
import itertools
import re
from errno import ENOENT as FILE_NOT_FOUND
import sys

# Anki add-on compatibility
try:
    import colorsys
except ModuleNotFoundError:
    from . import colorsys  # Anki add-on
try:
    import argparse
except ModuleNotFoundError:
    from . import argparse  # Anki add-on
try:
    from xml.dom import minidom
except ModuleNotFoundError:
    from .xml.dom import minidom

# Function that I want to have after refactoring, currently implemented using
# existing interface


def colorize(character,
             mode="spectrum",
             saturation=0.95,
             value=0.75,
             image_size=327):
    """
    Returns a string containing the colorized svg for the character

    >>> svg = colorize('a', mode='spectrum', image_size=100,
    ...                saturation=0.95, value=0.75)
    >>> 'has been modified' in svg
    True

    """
    arg_fmt = '--mode {} --saturation {} --value {} --image-size {}'
    arg_string = arg_fmt.format(mode, saturation, value, image_size)
    colorizer = KanjiColorizer(arg_string)

    return colorizer.get_colored_svg(character)


# Setup

source_directory = os.path.join(os.path.dirname(__file__), 'data', 'kanjivg',
                                'kanji')

# Classes


class KanjiVG(object):
    '''
    Class to create kanji objects containing KanjiVG data and some more
    basic qualities of the character
    '''

    def __init__(self, character, variant=''):
        '''
        Create a new KanjiVG object

        Either give just the character

        >>> k1 = KanjiVG('漢')
        >>> print(k1.character)
        漢
        >>> k1.variant
        ''

        Or if the character has a variant, give that as a second
        argument

        >>> k2 = KanjiVG('字', 'Kaisho')
        >>> print(k2.character)
        字
        >>> k2.variant
        'Kaisho'

        Raises InvalidCharacterError if the character and variant don't
        correspond to known data

        >>> k = KanjiVG('Л')
        Traceback (most recent call last):
            ...
        InvalidCharacterError: ('Л', '')

        '''
        self.character = character
        self.variant = variant
        if self.variant is None:
            self.variant = ''
        try:
            with open(os.path.join(source_directory, self.ascii_filename),
                      'r',
                      encoding='utf-8') as f:
                self.svg = f.read()
        except FileNotFoundError as e:  # file not found
            raise InvalidCharacterError(character, variant) from e

    @classmethod
    def _create_from_filename(cls, filename):
        '''
        Alternate constructor that uses a KanjiVG filename; used by
        get_all().

        >>> k = KanjiVG._create_from_filename('00061.svg')
        >>> k.character
        'a'
        '''
        m = re.match('^([0-9a-f]*)-?(.*?).svg$', filename)
        return cls(chr(int(m.group(1), 16)), m.group(2))

    @property
    def ascii_filename(self):
        '''
        An SVG filename in ASCII using the same format KanjiVG uses.

        >>> k = KanjiVG('漢')
        >>> k.ascii_filename
        '06f22.svg'

        May raise InvalidCharacterError for some kinds of invalid
        character/variant combinations; this should only happen during
        KanjiVG object initialization.
        '''
        try:
            code = '%05x' % ord(self.character)
        except TypeError:  # character not a character
            raise InvalidCharacterError(self.character, self.variant)
        if not self.variant:
            return code + '.svg'
        else:
            return '%s-%s.svg' % (code, self.variant)

    @property
    def character_filename(self):
        '''
        An SVG filename that uses the unicode character

        >>> k = KanjiVG('漢')
        >>> print(k.character_filename)
        漢.svg
        '''
        if not self.variant:
            return '%s.svg' % self.character
        else:
            return '%s-%s.svg' % (self.character, self.variant)

    @classmethod
    def get_all(cls):
        '''
        Returns a complete list of KanjiVG objects; everything there is
        data for

        >>> kanji_list = KanjiVG.get_all()
        >>> kanji_list[0].__class__.__name__
        'KanjiVG'
        '''
        kanji = []
        for file in os.listdir(source_directory):
            kanji.append(cls._create_from_filename(file))
        return kanji


class KanjiColorizer:
    """
    Class that creates colored stroke order diagrams out of kanjivg
    data, and writes them to file.

    Initialize with no arguments to take the command line settings, or
    an empty string to use default settings

    Settings can set by initializing with a string in the same format as
    the command line.
    >>> test_output_dir = os.path.join('test', 'colorized-kanji')
    >>> my_args = ' '.join(['--characters', 'aあ漢',
    ...                     '--output', test_output_dir])
    >>> kc = KanjiColorizer(my_args)

    To get an svg for a single character
    >>> colored_svg = kc.get_colored_svg('a')

    To create a set of diagrams:
    >>> kc.write_all()

    Note: This class is in the middle of having stuff that shouldn't be
    included factored out.  Some things have already been moved to the
    KanjiVG class; more stuff will move.
    """

    def __init__(self, argstring=''):
        '''
        Creates a new instance of KanjiColorizer, which stores settings
        and provides various methods to produce colored kanji SVGs.

        Takes an option alrgument of with an argument string; see
        read_arg_string documentation for information on how this is
        used.
        '''
        self._init_parser()
        self.read_arg_string(argstring)

    def _init_parser(self):
        r"""
        Initializes argparse.ArgumentParser self._parser

        >>> kc = KanjiColorizer()

        To show that it really is creating it:
        >>> kc._parser = None

        Then when this method is run:
        >>> kc._init_parser()
        >>> type(kc._parser)
        <class 'argparse.ArgumentParser'>

        >>> kc._parser.get_default('mode')
        'spectrum'

        """
        self._parser = argparse.ArgumentParser(description='Create a set of '
                                               'colored stroke order svgs')
        self._parser.add_argument(
            '--mode',
            default='spectrum',
            choices=['spectrum', 'contrast'],
            help='spectrum: color progresses evenly through the'
            ' spectrum; nice for seeing the way the kanji is'
            ' put together at a glance, but has the disadvantage'
            ' of using similar colors for consecutive strokes '
            'which can make it less clear which number goes '
            'with which stroke.  contrast: maximizes contrast '
            'among any group of consecutive strokes, using the '
            'golden ratio; also provides consistency by using '
            'the same sequence for every kanji.  (default: '
            '%(default)s)')
        self._parser.add_argument(
            '--saturation',
            default=0.95,
            type=float,
            help='a decimal indicating saturation where 0 is '
            'white/gray/black and 1 is completely  colorful '
            '(default: %(default)s)')
        self._parser.add_argument(
            '--group-mode',
            action='store_true',
            help='Color kanji groups instead of stroke by stroke '
            '(default: %(default)s)')
        self._parser.add_argument(
            '--value',
            default=0.75,
            type=float,
            help='a decimal indicating value where 0 is black '
            'and 1 is colored or white '
            '(default: %(default)s)')
        self._parser.add_argument(
            '--image-size',
            default=327,
            type=int,
            help="image size in pixels; they're square so this "
            'will be both height and width '
            '(default: %(default)s)')
        self._parser.add_argument(
            '--characters',
            type=str,
            help='a list of characters to include, without '
            'spaces; if this option is used, no variants '
            'will be included; if this option is not '
            'used, all characters will be included, '
            'including variants')
        self._parser.add_argument(
            '--filename-mode',
            default='character',
            choices=['character', 'code'],
            help='character: rename the files to use the '
            'unicode character as a filename.  code: leave it '
            'as the code.  '
            '(default: %(default)s)')
        self._parser.add_argument('-o',
                                  '--output-directory',
                                  default='colorized-kanji')

    # Public methods

    def read_cl_args(self):
        """
        Sets the settings to what's indicated in command line arguments

        >>> kc = KanjiColorizer()
        >>> kc.settings.mode
        'spectrum'
        >>> sys.argv = ['this.py', '--mode', 'contrast']
        >>> kc.read_cl_args()
        >>> kc.settings.mode
        'contrast'
        """
        self.settings = self._parser.parse_args()

    def read_arg_string(self, argstring):
        """
        >>> kc = KanjiColorizer()
        >>> kc.settings.mode
        'spectrum'
        >>> kc.read_arg_string('--mode contrast')
        >>> kc.settings.mode
        'contrast'
        """
        self.settings = self._parser.parse_args(argstring.split())

    def get_colored_svg(self, character):
        """
        Returns a string containing a colored stroke order diagram svg
        for character.

        >>> kc = KanjiColorizer()
        >>> svg = kc.get_colored_svg('a')
        >>> svg.splitlines()[0]
        '<?xml version="1.0" encoding="UTF-8"?>'
        >>> svg.find('00061')
        1938
        >>> svg.find('has been modified')
        53

        """
        svg = KanjiVG(character).svg
        svg = self._modify_svg(svg)
        return svg

    def write_all(self):
        """
        Converts all svgs (or only those specified with the --characters
        option) and prints them to files in the destination directory.

        Silently ignores invalid characters.

        >>> test_output_dir = os.path.join('test', 'colorized-kanji')
        >>> kc = KanjiColorizer(' '.join(['--characters', 'aあ漢',
        ...                               '--output', test_output_dir]))
        >>> kc.write_all()

        These should be the correct files:
        >>> import difflib
        >>> for file in os.listdir(test_output_dir):
        ...     our_svg = open(
        ...         os.path.join(test_output_dir, file),
        ...         'r', encoding='utf-8').read()
        ...     desired_svg = open(
        ...         os.path.join('test', 'default_results',
        ...             'kanji-colorize-spectrum',  file),
        ...             'r', encoding='utf-8').read()
        ...     for line in difflib.context_diff(our_svg.splitlines(1),
        ...            desired_svg.splitlines(1)):
        ...         print(line)
        ...

        Clean up doctest
        >>> import shutil
        >>> shutil.rmtree(test_output_dir) 

        """
        self._setup_dst_dir()
        if not self.settings.characters:
            characters = KanjiVG.get_all()
        else:
            characters = []
            if ',' in self.settings.characters \
                    and len(self.settings.characters) > 1:
                self.settings.characters = self.settings.characters.split(',')
            for c in self.settings.characters:
                var = ''
                if '-' in c:
                    varsplit = c.split('-')
                    c = varsplit[0]
                    var = '-'.join(varsplit[1:])
                try:
                    characters.append(KanjiVG(c, var))
                except InvalidCharacterError:
                    pass
        for kanji in characters:
            svg = self._modify_svg(kanji.svg)
            dst_file_path = os.path.join(self.settings.output_directory,
                                         self._get_dst_filename(kanji))
            with open(dst_file_path, 'w', encoding='utf-8') as f:
                f.write(svg)

    def _modify_svg(self, src_svg):
        """
        Applies all desired changes to the SVG

        >>> kc = KanjiColorizer('')
        >>> original_svg = open(
        ...    os.path.join(source_directory, '06f22.svg'),
        ...    'r', encoding='utf-8').read()
        >>> desired_svg = open(
        ...    os.path.join(
        ...        'test', 'default_results', 'kanji-colorize-spectrum',
        ...        '漢.svg'),
        ...    'r', encoding='utf-8').read()
        >>> import difflib
        >>> for line in difflib.context_diff(
        ...        kc._modify_svg(original_svg).splitlines(1),
        ...        desired_svg.splitlines(1)):
        ...     print(line)
        ...
        """
        dom = minidom.parseString(src_svg)
        _remove_empty_text(dom)
        svg: minidom.Document = dom.getElementsByTagName('svg')[0]

        if self.settings.group_mode:
            self._color_svg_groups(svg)
        else:
            self._color_svg_strokes(svg)

        self._resize_svg(dom, svg)
        self._comment_copyright(dom)
        return dom.toprettyxml(encoding='UTF-8', newl='\n').decode()

    # Private methods for working with files and directories

    def _setup_dst_dir(self):
        """
        Creates the destination directory args.output_directory if
        necessary

        (Set up the doctest environment)
        >>> current_directory = os.path.abspath(os.path.curdir)
        >>> os.mkdir(os.path.join('test', 'doctest-tmp'))
        >>> os.chdir(os.path.join('test', 'doctest-tmp'))
        >>> kc = KanjiColorizer('')

        This creates the directory
        >>> kc._setup_dst_dir()
        >>> os.listdir(os.path.curdir)
        ['colorized-kanji']

        But doesn't do anything or throw an error if it already exists
        >>> kc._setup_dst_dir()
        >>> os.listdir(os.path.curdir)
        ['colorized-kanji']

        (done; reseting environment for other doctests)
        >>> os.rmdir(kc.settings.output_directory)
        >>> os.chdir(os.path.pardir)
        >>> os.rmdir('doctest-tmp')
        >>> os.chdir(current_directory)
        """
        if not (os.path.exists(self.settings.output_directory)):
            os.mkdir(self.settings.output_directory)

    def _get_dst_filename(self, kanji):
        """
        Return the correct filename, based on args.filename-mode

        >>> kc = KanjiColorizer('--filename-mode code')
        >>> kc._get_dst_filename(KanjiVG('a'))
        '00061.svg'
        >>> kc = KanjiColorizer('--filename-mode character')
        >>> kc._get_dst_filename(KanjiVG('a'))
        'a.svg'

        """
        if (self.settings.filename_mode == 'character'):
            return kanji.character_filename
        return kanji.ascii_filename

    # private methods for modifying svgs
    def _color_svg_groups(self, svg: minidom.Document):
        groups = _get_nonempty_elements(svg, 'kvg:element')
        colors = self._color_generator(len(groups))
        all_texts = svg.getElementsByTagName('text')
        for group in groups:
            color = next(colors)
            paths = _get_direct_paths(group)
            texts = all_texts[:len(paths)]
            all_texts = all_texts[len(paths):]
            for path, text in itertools.zip_longest(paths, texts):
                path.attributes['style'] = 'stroke: %s;' % color
                if text is not None:
                    text.attributes['style'] = 'fill: %s;' % color

    def _color_svg_strokes(self, svg: minidom.Document):
        """
        Color the svg with colors from _color_generator, which uses
        configuration from settings

        This adds a style attribute to path (stroke) and text (stroke
        number) elements.  Both of these already have attributes, so we
        can expect a space.  Not all SVGs include stroke numbers.

        >>> kc = KanjiColorizer('')
        >>> svg_src = "<svg><path /><path /><text >1</text><text >2</text></svg>"
        >>> dom = minidom.parseString(svg_src)
        >>> svg = dom.getElementsByTagName('svg')[0]
        >>> kc._color_svg_strokes(svg)
        >>> svg.toxml()
        '<svg><path style="stroke: #bf0909;"/><path style="stroke: #09bfbf;"/><text style="fill: #bf0909;">1</text><text style="fill: #09bfbf;">2</text></svg>'
        >>> svg_src = "<svg><path /><path /></svg>"
        >>> dom = minidom.parseString(svg_src)
        >>> svg = dom.getElementsByTagName('svg')[0]
        >>> kc._color_svg_strokes(svg)
        >>> svg.toxml()
        '<svg><path style="stroke: #bf0909;"/><path style="stroke: #09bfbf;"/></svg>'
        """
        color_iterator = self._color_generator(self._stroke_count(svg))

        paths = svg.getElementsByTagName('path')
        texts = svg.getElementsByTagName('text')
        for color, path, text in itertools.zip_longest(color_iterator, paths,
                                                       texts):
            path.attributes['style'] = 'stroke: %s;' % color
            if text is not None:
                text.attributes['style'] = 'fill: %s;' % color

    def _comment_copyright(self, dom: minidom.Document):
        """
        Add a comment about what this script has done to the copyright notice

        >>> svg_src = '''<!--
        ... Copyright (C) copyright holder (etc.)
        ... -->
        ... <svg></svg>
        ... '''

        This contains the notice:

        >>> kc = KanjiColorizer('')
        >>> dom = minidom.parseString(svg_src)
        >>> kc._comment_copyright(dom)
        >>> dom.toxml().count('This file has been modified')
        1

        And depends on the settings it is run with:

        >>> kc = KanjiColorizer('--mode contrast')
        >>> dom = minidom.parseString(svg_src)
        >>> kc._comment_copyright(dom)
        >>> dom.toxml().count('contrast')
        1
        >>> kc = KanjiColorizer('--mode spectrum')
        >>> dom = minidom.parseString(svg_src)
        >>> kc._comment_copyright(dom)
        >>> dom.toxml().count('contrast')
        0
        """
        note = f"""This file has been modified from the original version by the kanji_colorize.py
script (available at http://github.com/Darkclainer/kanji-colorize,
that is fork of https://github.com/cayennes/kanji-colorize) with these
settings:
    mode: {self.settings.mode}
    saturation: {str(self.settings.saturation)}
    value: {str(self.settings.value)}
    image_size: {str(self.settings.image_size)}
It remains under a Creative Commons-Attribution-Share Alike 3.0 License.

The original SVG has the following copyright:

"""
        comment = next(
            filter(lambda v: v.nodeType == minidom.Document.COMMENT_NODE,
                   dom.childNodes))
        comment.data = note + comment.data

    def _resize_svg(self, dom: minidom.Document, svg: minidom.Element):
        """
        Resize the svg according to args.image_size, by changing the 109s
        in the <svg> attributes, and adding a transform scale to the
        groups enclosing the strokes and stroke numbers

        >>> kc = KanjiColorizer('--image-size 100')
        >>> svg_src = '<svg  width="109" height="109" viewBox="0 0 109 109"><g id="a"><path /></g></svg>'
        >>> svg = minidom.parseString(svg_src)
        >>> kc._resize_svg(svg, svg.documentElement)
        >>> svg.documentElement.toxml()
        '<svg width="100" height="100" viewBox="0 0 100 100"><g id="scaleTransform" transform="scale(0.9174311926605505,0.9174311926605505)"><g id="a"><path/></g></g></svg>'
        """
        ratio = repr(float(self.settings.image_size) / 109)
        size = str(self.settings.image_size)
        svg.attributes['width'].value = size
        svg.attributes['height'].value = size
        svg.attributes['viewBox'].value = "0 0 %s %s" % (size, size)

        scale_g: minidom.Element = dom.createElement('g')
        scale_g.attributes['id'] = 'scaleTransform'
        scale_g.attributes['transform'] = 'scale(%s,%s)' % (ratio, ratio)

        childs = list(svg.childNodes)
        for child in childs:
            scale_g.appendChild(child)

        svg.appendChild(scale_g)

    # Private utility methods

    def _stroke_count(self, svg: minidom.Document) -> int:
        """
        Return the number of strokes in the svg, based on occurences of
        "<path "

        >>> dom = minidom.parseString("<svg><path /><path /><path /></svg>")
        >>> svg = dom.getElementsByTagName('svg')[0]
        >>> kc = KanjiColorizer('')
        >>> kc._stroke_count(svg)
        3
        """
        return len(svg.getElementsByTagName('path'))

    def _hsv_to_rgbhexcode(self, h, s, v):
        """
        Convert an h, s, v color into rgb form #000000

        >>> kc = KanjiColorizer('')
        >>> kc._hsv_to_rgbhexcode(0, 0, 0)
        '#000000'
        >>> kc._hsv_to_rgbhexcode(2.0/3, 1, 1)
        '#0000ff'
        >>> kc._hsv_to_rgbhexcode(0.5, 0.95, 0.75)
        '#09bfbf'
        """
        color = colorsys.hsv_to_rgb(h, s, v)
        return '#%02x%02x%02x' % tuple([int(i * 255) for i in color])

    def _color_generator(self, n):
        """
        Create an iterator that loops through n colors twice (so that
        they can be used for both strokes and stroke numbers) using
        mode, saturation, and value from the args namespace

        >>> my_args = '--mode contrast --saturation 1 --value 1'
        >>> kc = KanjiColorizer(my_args)
        >>> [color for color in kc._color_generator(3)]
        ['#ff0000', '#004aff', '#94ff00']
        >>> my_args = '--mode spectrum --saturation 0.95 --value 0.75'
        >>> kc = KanjiColorizer(my_args)
        >>> [color for color in kc._color_generator(2)]
        ['#bf0909', '#09bfbf']
        """
        if (self.settings.mode == "contrast"):
            angle = 0.618033988749895  # conjugate of the golden ratio
            for i in range(n):
                yield self._hsv_to_rgbhexcode(i * angle,
                                              self.settings.saturation,
                                              self.settings.value)
        else:  # spectrum is default
            for i in range(n):
                yield self._hsv_to_rgbhexcode(
                    float(i) / n, self.settings.saturation,
                    self.settings.value)


def _get_nonempty_elements(svg: minidom.Document, attribute: str):
    """
    Return all non empty groups that have element attribute.
    Non empty means that they have at least one direct path child.

    >>> node = minidom.parseString("<svg><g><path /><path /></g></svg>").documentElement
    >>> _get_nonempty_elements(node, 'e')
    []
    >>> node = minidom.parseString("<svg><g e='a'><path/></g></svg>").documentElement
    >>> list(map(lambda v: v.attributes['e'].value, _get_nonempty_elements(node, 'e')))
    ['a']
    >>> node = minidom.parseString("<svg><g e='a'></g></svg>").documentElement
    >>> list(map(lambda v: v.attributes['e'].value, _get_nonempty_elements(node, 'e')))
    []
    >>> node = minidom.parseString("<svg><g e='a'><g e='b'><path/></g></g></svg>").documentElement
    >>> list(map(lambda v: v.attributes['e'].value, _get_nonempty_elements(node, 'e')))
    ['b']
    """
    return list(
        filter(
            lambda v: v.hasAttribute(attribute) and _has_direct_path(v),
            svg.getElementsByTagName('g'),
        ))


def _has_direct_path(node: minidom.Document):
    """
    Return True if element has direct path child

    >>> node = minidom.parseString("<g><path /><path /></g>").documentElement
    >>> _has_direct_path(node)
    True
    >>> node = minidom.parseString("<g><text></text></g>").documentElement
    >>> _has_direct_path(node)
    False
    """
    return len(_get_direct_paths(node)) != 0


def _get_direct_paths(node: minidom.Document):
    """
    Return direct paths child
    """
    return list(filter(lambda v: v.nodeName == 'path', node.childNodes))


def _remove_empty_text(dom: minidom.Document):
    childs = list(dom.childNodes)
    for ch in childs:
        if ch.nodeType == minidom.Document.TEXT_NODE and ch.data.isspace():
            dom.removeChild(ch)
        elif ch.nodeType == minidom.Document.ELEMENT_NODE:
            _remove_empty_text(ch)


# Exceptions


class Error(Exception):
    '''
    Base class for this module's exceptions
    '''
    pass


class InvalidCharacterError(Error):
    '''
    Exception thrown when trying to initialize or use a character that
    there isn't data for
    '''
    pass


# Test if run

if __name__ == "__main__":
    import doctest
    doctest.testmod()
