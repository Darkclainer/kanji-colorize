#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# test_colorizer.py is part of kanji-colorize which makes KanjiVG data
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

# pylint: disable=no-self-use
# pylint: disable=protected-access
# pylint: disable=invalid-name

from typing import Dict, Tuple, List
import os
import argparse
import itertools
from xml.dom import minidom

import pytest

from kanjicolorizer import colorizer


class MockFile:

    def __enter__(self):
        return self

    def __exit__(self, exectype, execinst, exectb):
        self.close()

    def write(self, v: str) -> int:
        return len(v)

    def read(self) -> str:
        return ''

    def close(self):
        pass


class MockOpen:

    opened_files: Dict[Tuple[str, str], int]

    def __init__(self):
        self.opened_files = dict()

    def open(self, path: str, mode: str, *argv, **argk) -> MockFile:
        if 'r' in mode and not os.path.isfile(path):
            raise FileNotFoundError(path)
        filename = os.path.split(path)[1]
        key = (filename, mode)
        count = self.opened_files.get(key)
        if count is None:
            count = 0
        count += 1
        self.opened_files[key] = count
        return MockFile()

    def filter_mode(self, mode: str) -> Dict[str, int]:
        return {
            key[0]: value
            for key, value in self.opened_files.items() if mode in key[1]
        }


@pytest.fixture
def mock_open(monkeypatch: pytest.MonkeyPatch) -> MockOpen:
    mock = MockOpen()
    monkeypatch.setattr("builtins.open", mock.open)
    return mock


class TestKanjiColorizerInit:

    @pytest.mark.parametrize(
        'characters',
        [
            # ascii
            ('a'),
            # nonascii
            ('あ'),
            # multiple characters
            ('漢字'),
        ])
    def test_characters_settings(self, characters: str):
        kc = colorizer.KanjiColorizer(f'--characters {characters}')
        assert kc.settings.characters == characters


class TestKanjiColorizerWriteAll:

    def test_default_writes_correct_number(self, mock_open: MockOpen,
                                           total_characters: int):
        kc = colorizer.KanjiColorizer()
        kc.write_all()
        assert len(mock_open.filter_mode('w')) == total_characters

    def test_default_writes_some_characters(self, mock_open: MockOpen):
        kc = colorizer.KanjiColorizer()
        kc.write_all()
        written_files = mock_open.filter_mode('w')
        assert 'a.svg' in written_files
        assert 'あ.svg' in written_files

    @pytest.mark.parametrize(
        'characters,expected_files',
        [
            # only character
            ('あ', ['あ.svg']),
            # excactly two correct characters
            ('漢字', ['漢.svg', '字.svg']),
            # invalid character doesn't write file
            ('Л', []),
            # invalid after valid character
            ('あЛ', ['あ.svg']),
            # invalid before valid character
            ('Лあ', ['あ.svg']),
        ])
    def test_writes_specific_characters(self, mock_open: MockOpen,
                                        characters: str,
                                        expected_files: List[str]):
        kc = colorizer.KanjiColorizer()
        kc.settings.characters = characters
        kc.write_all()
        written_files = mock_open.filter_mode('w')
        for filename in expected_files:
            assert filename in written_files
        assert len(written_files) == len(expected_files)


def test_kanjicolorizer_init_parser():
    kc = colorizer.KanjiColorizer()
    # we want to show that _init_parse initialize _init-parser
    # TODO: refactor this type error next time
    kc._parser = None

    kc._init_parser()
    assert isinstance(kc._parser, argparse.ArgumentParser)
    assert kc._parser.get_default('mode') == 'spectrum'


def test_kanjicolorizer_read_cl_args(monkeypatch: pytest.MonkeyPatch):
    kc = colorizer.KanjiColorizer()
    kc.settings.mode = 'spectrum'
    monkeypatch.setattr('sys.argv', ['this.py', '--mode', 'contrast'])
    kc.read_cl_args()
    assert kc.settings.mode == 'contrast'


def test_kanjicolorizer_read_arg_string():
    kc = colorizer.KanjiColorizer()
    kc.settings.mode = 'spectrum'
    kc.read_arg_string('--mode contrast')
    assert kc.settings.mode == 'contrast'


def test_kanjicolorizer_get_colored_svg():
    # TODO: refactor brittle test
    kc = colorizer.KanjiColorizer()
    svg = kc.get_colored_svg('a')
    assert svg.splitlines()[0] == '<?xml version="1.0" encoding="UTF-8"?>'
    assert svg.find('00061') == 1938
    assert svg.find('has been modified') == 53


@pytest.mark.parametrize('character', [
    ('a'),
    ('あ'),
    ('漢'),
])
def test_kanjicolorizer_write_all(character: str, testdata_dir: str,
                                  tmp_path: str):
    kc = colorizer.KanjiColorizer(
        f'--characters {character} --output {tmp_path}')
    kc.write_all()

    character_filename = f'{character}.svg'
    written_path = os.path.join(tmp_path, character_filename)
    goldsvg_path = os.path.join(testdata_dir, 'kanji-colorize-spectrum',
                                character_filename)
    assert_files_equal(goldsvg_path, written_path)


def test_kanjicolorizer_modify_svg(testdata_dir: str, tmp_path: str):
    kc = colorizer.KanjiColorizer('')
    original_svg = open(os.path.join(colorizer.source_directory, '06f22.svg'),
                        'r',
                        encoding='utf-8').read()
    goldsvg_path = os.path.join(testdata_dir, 'kanji-colorize-spectrum',
                                '漢.svg')
    written_path = os.path.join(tmp_path, 'tmp.svg')
    with open(written_path, 'w') as dst:
        dst.write(kc._modify_svg(original_svg))
    assert_files_equal(goldsvg_path, written_path)


def test_kanjicolorizer_setup_dst_dir(tmp_path: str,
                                      monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    kc = colorizer.KanjiColorizer('')

    # this creates the directory
    kc._setup_dst_dir()
    assert os.listdir(os.path.curdir) == ['colorized-kanji']

    # but doesn't do anything or throw an error if it already exists
    kc._setup_dst_dir()
    assert os.listdir(os.path.curdir) == ['colorized-kanji']


@pytest.mark.parametrize('mode,filename', [
    ('code', '00061.svg'),
    ('character', 'a.svg'),
])
def test_kanjicolorizer_get_dst_filename(mode: str, filename: str):
    kc = colorizer.KanjiColorizer(f'--filename-mode {mode}')
    assert kc._get_dst_filename(colorizer.KanjiVG('a')) == filename


@pytest.mark.parametrize('src,expected', [
    ('<svg><path /><path /><text >1</text><text >2</text></svg>',
     '<svg><path style="stroke: #bf0909;"/><path style="stroke: #09bfbf;"/><text style="fill: #bf0909;">1</text><text style="fill: #09bfbf;">2</text></svg>'
     ),
    ('<svg><path /><path /></svg>',
     '<svg><path style="stroke: #bf0909;"/><path style="stroke: #09bfbf;"/></svg>'
     )
])
def test_kanjicolorizer_color_svg_strokes(src: str, expected: str):
    kc = colorizer.KanjiColorizer('')
    dom = minidom.parseString(src)
    svg = dom.getElementsByTagName('svg')[0]
    kc._color_svg_strokes(svg)
    assert svg.toxml() == expected


@pytest.mark.parametrize('mode', [
    ('contrast'),
    ('spectrum'),
])
def test_kanjicolorizer_comment_copyright(mode: str):
    svg_src = '''<!--
Copyright (C) copyright holder (etc.)
-->
<svg></svg>
'''
    kc = colorizer.KanjiColorizer(f'--mode {mode}')
    dom = minidom.parseString(svg_src)
    kc._comment_copyright(dom)
    xml = dom.toxml()
    assert xml.count('This file has been modified') == 1
    assert xml.count(mode) == 1


def test_kanjicolorizer_resize_svg():
    kc = colorizer.KanjiColorizer('--image-size 100')
    svg_src = '<svg  width="109" height="109" viewBox="0 0 109 109"><g id="a"><path /></g></svg>'
    svg = minidom.parseString(svg_src)
    kc._resize_svg(svg, svg.documentElement)
    factor = 100 / 109
    assert svg.documentElement.toxml(
    ) == f'<svg width="100" height="100" viewBox="0 0 100 100"><g id="scaleTransform" transform="scale({factor},{factor})"><g id="a"><path/></g></g></svg>'


def test_kanjicolorizer_stroke_count():
    dom = minidom.parseString("<svg><path /><path /><path /></svg>")
    svg = dom.getElementsByTagName('svg')[0]
    kc = colorizer.KanjiColorizer('')
    assert kc._stroke_count(svg) == 3


@pytest.mark.parametrize('hsv,rgbhexcode', [
    ((0., 0., 0.), '#000000'),
    ((2.0 / 3, 1, 1), '#0000ff'),
    ((0.5, 0.95, 0.75), '#09bfbf'),
])
def test_kanjicolorizer_hsv_to_rgbhexcode(hsv: Tuple[float, float, float],
                                          rgbhexcode: str):
    kc = colorizer.KanjiColorizer('')
    assert kc._hsv_to_rgbhexcode(*hsv) == rgbhexcode


@pytest.mark.parametrize('mode,saturation,value,colors', [
    ('contrast', 1., 1., ['#ff0000', '#004aff', '#94ff00']),
    ('spectrum', 0.95, 0.75, ['#bf0909', '#09bfbf']),
])
def test_kanjicolorizer_color_generator(mode: str, saturation: float,
                                        value: float, colors: List[str]):
    kc = colorizer.KanjiColorizer(
        f'--mode {mode} --saturation {saturation} --value {value}')
    actual_colors = [color for color in kc._color_generator(len(colors))]
    assert actual_colors == colors


def assert_files_equal(expected_path: str, actual_path: str):
    with open(expected_path, 'r', encoding='utf8') as expected, \
         open(actual_path, 'r', encoding='utf8') as actual:
        lines = enumerate(itertools.zip_longest(expected, actual), start=1)
        for index, (expected_line, actual_line) in lines:
            if expected_line == actual_line:
                continue
            pytest.fail(
                f'expected file "{expected_path}" is not equal to actual file "{actual_path}"\n\n'
                'first unequal line is (first expected, then actual):\n'
                f'{_format_index_line(expected_line, index)}\n'
                f'{_format_index_line(actual_line, index)}')


def _format_index_line(line: str | None, index: int) -> str:
    if line is None:
        return f'no line {index}'
    return f'{index}: {repr(line)}'
