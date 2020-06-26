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

from .utils import (human_readable_size, TildeLayout)


class DlgDirscan(urwid.WidgetWrap):
	def __init__(self, controller, cwd, q, ev_abort, ev_skip, on_complete):
		self.controller = controller
		self.q = q
		self.ev_abort = ev_abort
		self.ev_skip = ev_skip
		self.on_complete = on_complete

		self.current = urwid.Text(cwd, layout=TildeLayout)
		self.files = urwid.Text(f'Files: 0', layout=TildeLayout)
		self.bytes = urwid.Text(f'Total size: 0', layout=TildeLayout)
		w = urwid.Pile([
			(1, urwid.Filler(self.current)),
			(1, urwid.Filler(self.files)),
			(1, urwid.Filler(self.bytes)),
		])
		w = urwid.LineBox(urwid.Padding(w, left=1, right=1), 'Directory scanning', title_attr='dialog_title', bline='')
		top = urwid.Padding(w, left=1, right=1)

		self.btn_abort = urwid.Button('Abort', lambda x: self.on_abort())
		attr_btn_abort = urwid.AttrMap(self.btn_abort, 'dialog', 'dialog_focus')
		self.btn_skip = urwid.Button('Skip', lambda x: self.on_skip())
		attr_btn_skip = urwid.AttrMap(self.btn_skip, 'dialog', 'dialog_focus')
		w = urwid.Columns([urwid.Divider(' '), (9, attr_btn_abort), (1, urwid.Text(' ')), (8, attr_btn_skip), urwid.Divider(' ')])
		w = urwid.LineBox(urwid.Filler(w), tlcorner='├', trcorner='┤')
		bottom = urwid.Padding(w, left=1, right=1)

		w = urwid.Pile([
			(1, urwid.Filler(urwid.Text(' '))),
			(4, top),
			(3, bottom),
			(1, urwid.Filler(urwid.Text(' '))),
		])
		w = urwid.AttrMap(w, 'dialog')

		super().__init__(w)

	def keypress(self, size, key):
		if key in ('left', 'right', ' ', 'enter'):
			return super().keypress(size, key)
		elif key == 'h':
			return super().keypress(size, 'left')
		elif key == 'l':
			return super().keypress(size, 'right')

	def on_pipe_data(self, data):
		retval = None
		info = None
		while not self.q.empty():
			info = self.q.get()

		if not info:
			pass
		elif 'result' in info:
			retval = False
			self.controller.screen.close_dialog()
			if not self.ev_abort.is_set():
				self.on_complete(info['result'], info['error'], info['skipped'])
		else:
			self.current.set_text(info['current'])
			self.files.set_text(f'Files: {info["files"]}')
			self.bytes.set_text(f'Total size: {human_readable_size(info["bytes"])}')

		return retval

	def on_abort(self):
		self.ev_abort.set()
		self.controller.screen.close_dialog()

		return False

	def on_skip(self):
		self.ev_skip.set()

