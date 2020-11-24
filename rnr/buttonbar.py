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

from .debug_print import (debug_print, debug_pprint)


class ButtonBar(urwid.WidgetWrap):
	def __init__(self, controller, labels):
		self.controller = controller
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

	def mouse_event(self, size, event, button, col, row, focus):
		super().mouse_event(size, event, button, col, row, focus)

		if ('press' not in event.split()) or (button != 1):
			return

		column_widths = self.columns.column_widths(size, focus)
		total_width = 0
		for i, width in enumerate(column_widths):
			total_width += width
			if total_width > col:
				self.controller.loop.process_input([f'f{((i // 2) + 1)}'])
				break

