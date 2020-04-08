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

from pathlib import Path

import urwid

from .utils import (human_readable_size, format_seconds, TildeLayout)


class DlgReport(urwid.WidgetWrap):
	def __init__(self, controller, file_list, error_list, skipped_list, cwd, scan_error, scan_skipped):
		self.controller = controller
		self.file_list = file_list
		self.error_list = error_list
		self.skipped_list = skipped_list

		if error_list or scan_error:
			attr = 'error'
			title_attr = 'error_title'
			focus_attr = 'error_focus'
		else:
			attr = 'dialog'
			title_attr = 'dialog_title'
			focus_attr = 'dialog_focus'

		l = []
		l.extend([urwid.Columns([('pack', urwid.Text(f'ERROR [{x["error"]}]:', wrap='clip')), urwid.Text(str(Path(x['file']).relative_to(cwd)), layout=TildeLayout)], dividechars=1) for x in scan_error])
		l.extend([urwid.Columns([('pack', urwid.Text(f'ERROR [{x["error"]}]:', wrap='clip')), urwid.Text(str(Path(x['file']).relative_to(cwd)), layout=TildeLayout)], dividechars=1) for x in error_list])
		l.extend([urwid.Columns([('pack', urwid.Text('SKIPPED:', wrap='clip')), urwid.Text(str(Path(x).relative_to(cwd)), layout=TildeLayout)], dividechars=1) for x in scan_skipped])
		l.extend([urwid.Columns([('pack', urwid.Text('SKIPPED:', wrap='clip')), urwid.Text(str(Path(x).relative_to(cwd)), layout=TildeLayout)], dividechars=1) for x in skipped_list])
		w = urwid.SimpleListWalker(l)
		self.listbox = urwid.ListBox(w)
		w = urwid.LineBox(urwid.Padding(self.listbox, left=1, right=1), 'Report', title_attr=title_attr, bline='')
		top = urwid.Padding(w, left=1, right=1)

		self.btn_ok = urwid.Button('OK', lambda x: self.on_ok())
		attr_btn_ok = urwid.AttrMap(self.btn_ok, attr, focus_attr)
		w = urwid.Columns([urwid.Divider(' '), (6, attr_btn_ok), urwid.Divider(' ')])
		w = urwid.LineBox(urwid.Filler(w), tlcorner='├', trcorner='┤')
		bottom = urwid.Padding(w, left=1, right=1)

		w = urwid.Pile([
			(1, urwid.Filler(urwid.Text(' '))),
			top,
			(3, bottom),
			(1, urwid.Filler(urwid.Text(' '))),
		])
		w.set_focus(2)
		w = urwid.AttrMap(w, attr)

		super().__init__(w)

	def keypress(self, size, key):
		if key in ('left', 'right', ' ', 'enter'):
			return super().keypress(size, key)
		elif key == 'h':
			return super().keypress(size, 'left')
		elif key == 'l':
			return super().keypress(size, 'right')
		elif key in ('j', 'down', 'ctrl f', 'page down'):
			self.listbox.keypress(size, 'page down')
		elif key in ('k', 'up', 'ctrl b', 'page up'):
			self.listbox.keypress(size, 'page up')

	def on_ok(self):
		self.controller.close_dialog()
		self.controller.reload()

