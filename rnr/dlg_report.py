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

from atomicwrites import atomic_write

from .database import DataBase
from .utils import (human_readable_size, format_seconds, TildeLayout)
from .debug_print import (debug_print, debug_pprint)


class DlgReport(urwid.WidgetWrap):
	def __init__(self, controller, completed_list, error_list, skipped_list, aborted_list, operation, files, cwd, dest, scan_error, scan_skipped, job_id):
		self.controller = controller
		self.command_bar = controller.screen.command_bar
		self.completed_list = completed_list
		self.error_list = error_list
		self.skipped_list = skipped_list
		self.aborted_list = aborted_list
		self.operation = operation
		self.files = files
		self.cwd = cwd
		self.dest = dest
		self.scan_error = scan_error
		self.scan_skipped = scan_skipped
		self.job_id = job_id

		if scan_error or error_list or aborted_list:
			attr = 'error'
			title_attr = 'error_title'
			focus_attr = 'error_focus'
		else:
			attr = 'dialog'
			title_attr = 'dialog_title'
			focus_attr = 'dialog_focus'

		self.messages = []
		self.messages.extend([f'ERROR (scan) [{x["message"]}]: {str(Path(x["file"]).relative_to(cwd))}' for x in scan_error])
		self.messages.extend([f'SKIPPED (scan) [{x["message"]}]: {str(Path(x["file"]).relative_to(cwd))}' for x in scan_skipped])
		self.messages.extend([f'ERROR [{x["message"]}]: {str(Path(x["file"]).relative_to(cwd))}' for x in error_list])
		self.messages.extend([f'SKIPPED [{x["message"]}]: {str(Path(x["file"]).relative_to(cwd))}' for x in skipped_list])
		if aborted_list:
			self.messages.extend([f'{("WARNING" if x["message"] else "DONE")} [{x["message"]}]: {str(Path(x["file"]).relative_to(cwd))}' for x in completed_list])
			self.messages.extend([f'ABORTED [{x["message"]}]: {str(Path(x["file"]).relative_to(cwd))}' for x in aborted_list])
		else:
			self.messages.extend([f'WARNING [{x["message"]}]: {str(Path(x["file"]).relative_to(cwd))}' for x in completed_list if x['message']])

		l = [urwid.Text(x, layout=TildeLayout) for x in self.messages]
		w = urwid.SimpleListWalker(l)
		self.listbox = urwid.ListBox(w)
		w = urwid.LineBox(urwid.Padding(self.listbox, left=1, right=1), 'Report', title_attr=title_attr, bline='')
		top = urwid.Padding(w, left=1, right=1)

		self.btn_close = urwid.Button('Close', lambda x: self.on_close())
		attr_btn_close = urwid.AttrMap(self.btn_close, attr, focus_attr)
		self.btn_save = urwid.Button('Save', lambda x: self.on_save())
		attr_btn_save = urwid.AttrMap(self.btn_save, attr, focus_attr)
		w = urwid.Columns([urwid.Divider(' '), (9, attr_btn_close), (1, urwid.Text(' ')), (8, attr_btn_save), urwid.Divider(' ')])
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
		elif key in ('g', 'home'):
			self.listbox.keypress(size, 'home')
		elif key in ('G', 'end'):
			self.listbox.keypress(size, 'end')

	def on_close(self):
		if self.controller.dbfile:
			db = DataBase(self.controller.dbfile)
			db.delete_job(self.job_id)
			del db

		self.controller.screen.close_dialog()
		self.command_bar.reset()

		if self.controller.pending_jobs:
			self.controller.show_next_pending_job()
		else:
			self.controller.reload()

	def on_save(self):
		self.command_bar.save(Path(self.cwd) / 'rnr-report.txt', self.do_save, forced_focus=False)

	def do_save(self, file):
		try:
			with atomic_write(str(file)) as f:
				f.write(f'Operation: {self.operation}\n')
				f.write(f'From: {str(self.cwd)}\n')
				if self.dest:
					f.write(f'To: {str(self.dest)}\n')

				f.write('Files:\n')
				for file in self.files:
					f.write(f'{str(file.relative_to(self.cwd))}\n')

				f.write('\n')
				f.write('------------------------------------------------------------------------------\n')
				f.write('\n')

				for message in self.messages:
					f.write(f'{message}\n')

			self.on_close()
		except OSError as e:
			self.command_bar.error(f'{e.strerror} ({e.errno})')

