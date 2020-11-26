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

from .utils import TildeLayout
from .debug_print import (debug_print, debug_pprint)


class DlgCancelable(urwid.WidgetWrap):
	def __init__(self, controller, title, message, on_cancel):
		self.controller = controller

		w = urwid.Filler(urwid.Text(f' {message} ', align='center', layout=TildeLayout))
		w = urwid.LineBox(w, title, title_attr='dialog_title', bline='')
		top = urwid.Padding(w, left=1, right=1)

		self.btn_cancel = urwid.Button('Cancel', lambda x: on_cancel())
		attr_btn_cancel = urwid.AttrMap(self.btn_cancel, 'dialog', 'dialog_focus')
		w = urwid.Columns([urwid.Divider(' '), (10, attr_btn_cancel), urwid.Divider(' ')])
		w = urwid.LineBox(urwid.Filler(w), tlcorner='├', trcorner='┤')
		bottom = urwid.Padding(w, left=1, right=1)

		w = urwid.Pile([
			(1, urwid.Filler(urwid.Text(' '))),
			(2, top),
			(3, bottom),
			(1, urwid.Filler(urwid.Text(' '))),
		])
		w = urwid.AttrMap(w, 'dialog')

		super().__init__(w)

	def keypress(self, size, key):
		if key in ('esc', 'f10'):
			self.btn_cancel.keypress(size, 'enter')
			return

		if key in (' ', 'enter'):
			return super().keypress(size, key)

