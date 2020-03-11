#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (C) 2020  Franco Bugnano
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sys
import os

import pathlib

import urwid


class SelectableText(urwid.Text):
	_selectable = True

	def keypress(self, size, key):
		return key


class VimListBox(urwid.ListBox):
	def keypress(self, size, key):
		if key == 'h':
			pass
		elif key == 'j':
			return super().keypress(size, 'down')
		elif key == 'k':
			return super().keypress(size, 'up')
		elif key == 'l':
			pass
		elif key == 'g':
			return super().keypress(size, 'home')
		elif key == 'G':
			return super().keypress(size, 'end')
		elif key == 'ctrl b':
			return super().keypress(size, 'page up')
		elif key == 'ctrl f':
			return super().keypress(size, 'page down')
		else:
			return super().keypress(size, key)


class Panel(urwid.WidgetWrap):
	def __init__(self):
		cwd = pathlib.Path.cwd()
		files = list(cwd.iterdir())
		dirs = [files.pop(i) for i, e in reversed(list(enumerate(files))) if e.is_dir()]
		labels = [urwid.AttrMap(SelectableText('../'), 'dir', 'focus')]
		labels.extend([urwid.AttrMap(SelectableText(f'{x.name}/'), 'dir', 'focus') for x in sorted(dirs)])
		labels.extend([urwid.AttrMap(SelectableText(f'{x.name}'), 'bg', 'focus') for x in sorted(files)])
		w = VimListBox(urwid.SimpleFocusListWalker(labels))

		w = urwid.LineBox(w, str(cwd), 'left')
		w = urwid.AttrMap(w, 'bg')

		urwid.WidgetWrap.__init__(self, w)

