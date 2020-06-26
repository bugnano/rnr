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

import json

from pathlib import Path

import urwid

from atomicwrites import atomic_write

from .database import DataBase
from .utils import (human_readable_size, format_seconds, TildeLayout)
from .debug_print import (debug_print, debug_pprint)


class DlgPendingJob(urwid.WidgetWrap):
	def __init__(self, controller, pending_job):
		self.controller = controller
		self.command_bar = controller.screen.command_bar
		self.pending_job = pending_job

		attr = 'dialog'
		title_attr = 'dialog_title'
		focus_attr = 'dialog_focus'

		self.messages = [
			f'Status: {pending_job["status"]}',
			f'Operation: {pending_job["operation"]}',
			f'From: {str(pending_job["cwd"])}',
		]

		if pending_job['dest']:
			self.messages.append(f'To: {str(pending_job["dest"])}')

		self.messages.append('Files:')
		for file in json.loads(pending_job['files']):
			self.messages.append(f'{str(Path(file).relative_to(pending_job["cwd"]))}')

		l = [urwid.Text(x, layout=TildeLayout) for x in self.messages]
		w = urwid.SimpleListWalker(l)
		self.listbox = urwid.ListBox(w)
		w = urwid.LineBox(urwid.Padding(self.listbox, left=1, right=1), 'Interrupted Job', title_attr=title_attr, bline='')
		top = urwid.Padding(w, left=1, right=1)

		self.btn_continue = urwid.Button('Continue', lambda x: self.on_continue())
		attr_btn_continue = urwid.AttrMap(self.btn_continue, attr, focus_attr)
		self.btn_skip = urwid.Button('Skip', lambda x: self.on_skip())
		attr_btn_skip = urwid.AttrMap(self.btn_skip, attr, focus_attr)
		self.btn_abort = urwid.Button('Abort', lambda x: self.on_abort())
		attr_btn_abort = urwid.AttrMap(self.btn_abort, attr, focus_attr)
		w = urwid.Columns([urwid.Divider(' '), (12, attr_btn_continue), (1, urwid.Text(' ')), (8, attr_btn_skip), (1, urwid.Text(' ')), (9, attr_btn_abort), urwid.Divider(' ')])
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

	def on_continue(self):
		self.controller.screen.close_dialog()

		job_id = self.pending_job['id']

		if self.controller.dbfile:
			db = DataBase(self.controller.dbfile)
			file_list = db.get_file_list(job_id)
			del db
		else:
			file_list = []

		scan_error = json.loads(self.pending_job['scan_error'])
		scan_skipped = json.loads(self.pending_job['scan_skipped'])
		files = json.loads(self.pending_job['files'])
		cwd = self.pending_job['cwd']
		dest = self.pending_job['dest']
		on_conflict = self.pending_job['on_conflict']
		operation = self.pending_job['operation']

		if self.pending_job['status'] in ('ABORTED', 'DONE'):
			if operation == 'Delete':
				file_list.sort(key=lambda x: x['file'], reverse=True)
			else:
				file_list.sort(key=lambda x: x['file'])

			error_list = [{'file': x['file'], 'message': x['message']} for x in file_list if x['status'] == 'ERROR']
			skipped_list = [{'file': x['file'], 'message': x['message']} for x in file_list if x['status'] == 'SKIPPED']
			completed_list = [{'file': x['file'], 'message': x['message']} for x in file_list if x['status'] == 'DONE']
			if self.pending_job['status'] == 'ABORTED':
				aborted_list = [{'file': x['file'], 'message': (x['message'] or '')} for x in file_list if x['status'] not in ('DONE', 'ERROR', 'SKIPPED')]
			else:
				aborted_list = []

			self.controller.on_finish(completed_list, error_list, skipped_list, aborted_list, operation, files, cwd, dest, scan_error, scan_skipped, job_id)
		else:
			if operation == 'Delete':
				self.controller.do_delete(file_list, scan_error, scan_skipped, files, cwd, job_id)
			elif operation == 'Copy':
				self.controller.do_copy(file_list, scan_error, scan_skipped, files, cwd, dest, on_conflict, job_id)
			elif operation == 'Move':
				self.controller.do_move(file_list, scan_error, scan_skipped, files, cwd, dest, on_conflict, job_id)
			else:
				if self.controller.pending_jobs:
					self.controller.show_next_pending_job()
				else:
					self.controller.reload()

	def on_skip(self):
		self.controller.screen.close_dialog()

		if self.controller.pending_jobs:
			self.controller.show_next_pending_job()
		else:
			self.controller.reload()

	def on_abort(self):
		if self.controller.dbfile:
			db = DataBase(self.controller.dbfile)
			db.delete_job(self.pending_job['id'])
			del db

		self.controller.screen.close_dialog()

		if self.controller.pending_jobs:
			self.controller.show_next_pending_job()
		else:
			self.controller.reload()

