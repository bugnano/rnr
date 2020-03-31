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


class TLineWidget(urwid.WidgetWrap):
	def __init__(self, title, title_align='center', title_attr=None, lcorner='├', tline='─', rcorner='┤'):
		self.title_widget = title
		self.title_attr = urwid.AttrMap(self.title_widget, title_attr)
		tline_divider = urwid.Divider(tline)

		if title_align == 'left':
			tline_widgets = [('pack', self.title_attr), tline_divider]
		else:
			tline_widgets = [tline_divider, ('pack', self.title_attr)]
			if title_align == 'center':
				tline_widgets.append(tline_divider)

		self.tline_widget = urwid.Columns(tline_widgets)

		w = urwid.Columns([(1, urwid.Text(lcorner)), (1, urwid.Text(tline)), self.tline_widget, (1, urwid.Text(tline)), (1, urwid.Text(rcorner))])

		super().__init__(w)

	def set_title(self, text):
		self.title_widget.set_text(text)

	def set_title_attr(self, attr):
		self.title_attr.set_attr_map({None: attr})

