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

import pytest

from kanjicolorizer import colorizer


class TestKanjiVGInit:

    @pytest.mark.parametrize(
        'character,variant,expected_variant',
        [
            # basic acii character
            ('a', '', ''),
            # nonascii character
            ('あ', '', ''),
            # character with variant
            ('字', 'Kaisho', 'Kaisho'),
            # None variant defaults to ''
            ('a', None, ''),
        ])
    def test_init(self, character, variant, expected_variant):
        k = colorizer.KanjiVG(character, variant)
        assert k.character == character
        assert k.variant == expected_variant

    @pytest.mark.parametrize(
        'character,variant,stroke_group',
        [
            # basic acii character
            ('a', '', 'kvg:StrokePaths_00061'),
            # nonascii character
            ('あ', '', 'kvg:StrokePaths_03042'),
            # character with variant
            ('字', 'Kaisho', 'kvg:StrokePaths_05b57-Kaisho'),
        ])
    def test_valid_character_contains_named_stroke_group(
            self, character, variant, stroke_group):
        '''
        This is a proxy for having read the correct file
        '''
        k = colorizer.KanjiVG(character, variant)
        assert stroke_group in k.svg

    @pytest.mark.parametrize(
        'character,variant,expected_variant',
        [
            # invalid character
            ('Л', None, ''),
            # multiple characters
            ('漢字', None, ''),
            # nonexisting variant
            ('字', 'gobbledygook', 'gobbledygook'),
            # mismatched variant
            ('漢', 'Kaisho', 'Kaisho'),
            # TODO check if variant appeared?
            #('字', '')
            # not engough parameters
            (None, None, ''),
        ])
    def test_invalid_character_raises_correct_exception(
            self, character, variant, expected_variant):
        with pytest.raises(colorizer.InvalidCharacterError) as exception_info:
            colorizer.KanjiVG(character, variant)
        assert exception_info.value.args[0] == character
        assert exception_info.value.args[1] == expected_variant
        if character is not None and character != '':
            assert repr(character) in repr(exception_info.value)
        if expected_variant != '':
            assert repr(expected_variant) in repr(exception_info.value)

    def test_permission_denied_error_propogated(
            self, monkeypatch: pytest.MonkeyPatch):
        '''
        Errors other than file not found are unknown problems; the
        exception should not be caught or changed
        '''

        def mock_open(*argv, **argk):
            raise IOError(31, 'Permission denied')

        monkeypatch.setattr('builtins.open', mock_open)
        with pytest.raises(IOError):
            colorizer.KanjiVG('a')

    @pytest.mark.parametrize(
        'character,variant,filename',
        [
            # without variant
            ('あ', None, '03042.svg'),
            # with variant
            ('字', 'Kaisho', '05b57-Kaisho.svg'),
            # five digit unicode character
            ('𦥑', None, '26951.svg'),
        ])
    def test_correct_ascii_filename(self, character: str, variant: str | None,
                                    filename: str):
        k = colorizer.KanjiVG(character, variant)
        assert k.ascii_filename == filename

    @pytest.mark.parametrize(
        'character,variant,filename',
        [
            # without variant
            ('あ', None, 'あ.svg'),
            # with variant
            ('字', 'Kaisho', '字-Kaisho.svg'),
        ])
    def test_correct_character_filename(self, character: str,
                                        variant: str | None, filename: str):
        k = colorizer.KanjiVG(character, variant)
        assert k.character_filename == filename


class TestKanjiVGCreateFromFilename:

    @pytest.mark.parametrize(
        'filename,character,variant',
        [
            # without variant
            ('06f22.svg', '漢', ''),
            # with variant
            ('05b57-Kaisho.svg', '字', 'Kaisho'),
            # five digit
            ('26951.svg', '𦥑', ''),
        ])
    def test_ok(self, filename: str, character: str, variant: str):
        k = colorizer.KanjiVG._create_from_filename(filename)
        assert k.character == character
        assert k.variant == variant

    @pytest.mark.parametrize(
        'filename',
        [
            # correct format nonexistent file
            ('1000.svg'),
            # incorrect format
            ('5b57'),
        ])
    def test_exception(self, filename: str):
        '''
        As a private method, the precise exception is unimportant
        '''
        with pytest.raises(Exception):
            colorizer.KanjiVG._create_from_filename(filename)


class TestKanjiVGetAll:

    def test_has_correct_amount(self, total_characters: int):
        all_kanji = colorizer.KanjiVG.get_all()
        assert len(all_kanji) == total_characters

    def test_first_is_a_kanji(self):
        all_kanji = colorizer.KanjiVG.get_all()
        assert isinstance(all_kanji[0], colorizer.KanjiVG)
