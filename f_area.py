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

import urwid


texts = [
	'Help',
	'Menu',
	'View',
	'Edit',
	'Copy',
	'RenMov',
	'Mkdir',
	'Delete',
	'PullDn',
	'Quit',
]


class FArea(urwid.WidgetWrap):
	def __init__(self):
		widgets = []
		for i, label in enumerate(texts):
			w = urwid.Text(f'{i + 1}', align='right')
			w = urwid.Filler(w)
			w = urwid.AttrMap(w, 'white_on_black')
			widgets.append((2, w))

			w = urwid.Text(label)
			w = urwid.Filler(w)
			w = urwid.AttrMap(w, 'menu')
			widgets.append(w)

		w = urwid.Columns(widgets)

		super().__init__(w)

