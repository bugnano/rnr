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

from .tilde_layout import TildeLayout
from .tline_widget import TLineWidget


class DlgDirscan(urwid.WidgetWrap):
	def __init__(self, controller, cwd, q):
		self.controller = controller
		self.q = q

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
		on_yes = None
		on_no = None
		self.btn_yes = urwid.AttrMap(urwid.Button('Abort', on_yes), 'dialog', 'dialog_focus')
		self.btn_no = urwid.AttrMap(urwid.Button('Skip', on_no), 'dialog', 'dialog_focus')
		w = urwid.Columns([urwid.Divider(' '), (9, self.btn_yes), (1, urwid.Text(' ')), (8, self.btn_no), urwid.Divider(' ')])
		w = urwid.LineBox(urwid.Filler(w), tline='')

		w = urwid.Pile([
			(1, urwid.Filler(urwid.Text(' '))),
			(4, top),
			(1, urwid.Padding(urwid.Filler(TLineWidget(urwid.Text(''))), left=1, right=1)),
			(2, urwid.Padding(w, left=1, right=1)),
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
		elif key == 'esc':
			self.btn_no.keypress(size, 'enter')

	def on_pipe_data(self, data):
		info = None
		while not self.q.empty():
			info = self.q.get()

		if not info:
			pass
		elif 'result' in info:
			self.controller.loop.remove_watch_pipe(self.fd)
			self.controller.close_dialog()
		else:
			self.current.set_text(info['current'])
			self.files.set_text(f'Files: {info["files"]}')
			self.bytes.set_text(f'Total size: {info["bytes"]}')

