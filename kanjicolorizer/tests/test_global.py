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

from typing import List
from xml.dom import minidom

import pytest

from kanjicolorizer import colorizer


def test_colorizer():
    svg = colorizer.colorize('a',
                             mode='spectrum',
                             image_size=100,
                             saturation=0.95,
                             value=0.75)
    assert 'has been modified' in svg


@pytest.mark.parametrize('src,elements', [
    ('<svg><g><path /><path /></g></svg>', []),
    ('<svg><g e="a"><path/></g></svg>', ['a']),
    ('<svg><g e="a"></g></svg>', []),
    ('<svg><g e="a"><g e="b"><path/></g></g></svg>', ['b']),
])
def test_get_nonempty_elements(src: str, elements: List[str]):
    node = minidom.parseString(src).documentElement
    actual_elements = list(
        map(lambda v: v.attributes['e'].value,
            colorizer._get_nonempty_elements(node, 'e')))
    assert actual_elements == elements


@pytest.mark.parametrize('src,has', [
    ('<g><path /><path /></g>', True),
    ('<g><text></text></g>', False),
])
def test_has_direct_path(src: str, has: bool):
    node = minidom.parseString(src).documentElement
    assert colorizer._has_direct_path(node) == has
