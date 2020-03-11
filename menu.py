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
	'Left ',
	'File ',
	'Command ',
	'Options ',
	'Right ',
]


class Menu(urwid.WidgetWrap):
	def __init__(self):
		widgets = []
		for label in texts:
			w = urwid.Text(label, align='center')
			w = urwid.Filler(w)
			w = urwid.AttrMap(w, 'menu')
			widgets.append((len(label) + 4, w))

		w = urwid.Columns(widgets)
		w = urwid.AttrMap(w, 'menu')

		urwid.WidgetWrap.__init__(self, w)

