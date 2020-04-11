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

from .utils import (human_readable_size, format_seconds, TildeLayout)


class DlgDeleteProgress(urwid.WidgetWrap):
	def __init__(self, controller, num_files, total_size, q, ev_skip, ev_suspend, ev_abort, on_complete):
		self.controller = controller
		self.num_files = num_files
		self.total_size = total_size
		self.q = q
		self.ev_skip = ev_skip
		self.ev_suspend = ev_suspend
		self.ev_abort = ev_abort
		self.on_complete = on_complete

		self.current = urwid.Text(' ', layout=TildeLayout)
		w = urwid.Filler(self.current)
		w = urwid.LineBox(urwid.Padding(w, left=1, right=1), 'Delete', title_attr='dialog_title', bline='')
		top = urwid.Padding(w, left=1, right=1)

		self.files = urwid.Text(f'Files processed: 0/{self.num_files}', layout=TildeLayout)
		self.time = urwid.Text(f'Time: {format_seconds(0)} ETA {format_seconds(0)}', layout=TildeLayout)
		self.progress = urwid.ProgressBar('dialog', 'progress', 0, (num_files or 1))
		w = urwid.Columns([(1, urwid.Text('[')), self.progress, (1, urwid.Text(']'))])
		w = urwid.Pile([
			(1, urwid.Filler(w)),
			(1, urwid.Filler(self.files)),
			(1, urwid.Filler(self.time)),
		])
		self.divider = urwid.LineBox(urwid.Padding(w, left=1, right=1), f'Total: {human_readable_size(0)}/{human_readable_size(self.total_size)}', tlcorner='├', trcorner='┤', bline='')
		middle = urwid.Padding(self.divider, left=1, right=1)

		self.btn_skip = urwid.Button('Skip', lambda x: self.on_skip())
		attr_btn_skip = urwid.AttrMap(self.btn_skip, 'dialog', 'dialog_focus')
		self.btn_suspend = urwid.Button('Suspend', lambda x: self.on_suspend())
		attr_btn_suspend = urwid.AttrMap(self.btn_suspend, 'dialog', 'dialog_focus')
		self.btn_abort = urwid.Button('Abort', lambda x: self.on_abort())
		attr_btn_abort = urwid.AttrMap(self.btn_abort, 'dialog', 'dialog_focus')
		w = urwid.Columns([urwid.Divider(' '), (8, attr_btn_skip), (1, urwid.Text(' ')), (12, attr_btn_suspend), (1, urwid.Text(' ')), (9, attr_btn_abort), urwid.Divider(' ')])
		w = urwid.LineBox(urwid.Filler(w), tlcorner='├', trcorner='┤')
		bottom = urwid.Padding(w, left=1, right=1)

		w = urwid.Pile([
			(1, urwid.Filler(urwid.Text(' '))),
			(2, top),
			(4, middle),
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
			self.controller.close_dialog()
			self.controller.abort.discard(self.ev_abort)
			self.controller.suspend.discard(self.ev_suspend)
			self.on_complete(info['result'], info['error'], info['skipped'])
		else:
			self.current.set_text(info['current'])
			self.divider.set_title(f'Total: {human_readable_size(info["bytes"])}/{human_readable_size(self.total_size)}')
			self.files.set_text(f'Files processed: {info["files"]}/{self.num_files}')

			fps = info['files'] / (info['time'] or 1)
			eta = max(int(round((self.num_files - info['files']) / (fps or 1))), 0)
			self.time.set_text(f'Time: {format_seconds(info["time"])} ETA {format_seconds(eta)}')

			self.progress.set_completion(info['files'])

		return retval

	def on_skip(self):
		self.ev_skip.set()

		if not self.ev_suspend.is_set():
			self.on_suspend()

	def on_suspend(self):
		if self.ev_suspend.is_set():
			self.ev_suspend.clear()
			self.btn_suspend.set_label('Continue')
		else:
			self.ev_suspend.set()
			self.btn_suspend.set_label('Suspend')

	def on_abort(self):
		self.ev_abort.set()
		self.controller.abort.discard(self.ev_abort)
		self.controller.suspend.discard(self.ev_suspend)
		self.controller.close_dialog()
		self.controller.reload()

		if not self.ev_suspend.is_set():
			self.on_suspend()

		return False

