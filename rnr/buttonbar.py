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


class ButtonBar(urwid.WidgetWrap):
	def __init__(self, labels):
		self.columns = urwid.Columns([])
		self.set_labels(labels)

		super().__init__(self.columns)

	def set_labels(self, labels):
		widgets = []
		for i, label in enumerate(labels):
			w = urwid.Text(f'{i + 1}', align='right')
			w = urwid.AttrMap(w, 'hotkey')
			widgets.append((w, self.columns.options('given', 2)))

			w = urwid.Text(label)
			w = urwid.AttrMap(w, 'selected')
			widgets.append((w, self.columns.options()))

		del self.columns.contents[:]
		self.columns.contents.extend(widgets)

