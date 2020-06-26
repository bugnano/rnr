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


class DlgCpMvProgress(urwid.WidgetWrap):
	def __init__(self, controller, title, num_files, total_size, q, ev_skip, ev_suspend, ev_abort, ev_nodb, on_complete):
		self.controller = controller
		self.num_files = num_files
		self.total_size = total_size
		self.q = q
		self.ev_skip = ev_skip
		self.ev_suspend = ev_suspend
		self.ev_abort = ev_abort
		self.ev_nodb = ev_nodb
		self.on_complete = on_complete

		self.aborted = False

		self.source = urwid.Text(' ', layout=TildeLayout)
		self.target = urwid.Text(' ', layout=TildeLayout)
		self.progress_current = urwid.ProgressBar('dialog', 'progress')
		self.time_current = urwid.Text(f'{human_readable_size(0)}/{human_readable_size(0)} ETA {format_seconds(0)} ({human_readable_size(0)}/s)', layout=TildeLayout)
		w = urwid.Columns([(1, urwid.Text('[')), self.progress_current, (1, urwid.Text(']'))])
		w = urwid.Pile([
			(1, urwid.Filler(urwid.Text('Source'))),
			(1, urwid.Filler(self.source)),
			(1, urwid.Filler(urwid.Text('Target'))),
			(1, urwid.Filler(self.target)),
			(1, urwid.Filler(w)),
			(1, urwid.Filler(self.time_current)),
		])
		w = urwid.LineBox(urwid.Padding(w, left=1, right=1), title, title_attr='dialog_title', bline='')
		top = urwid.Padding(w, left=1, right=1)

		self.files = urwid.Text(f'Files processed: 0/{self.num_files}', layout=TildeLayout)
		self.time = urwid.Text(f'Time: {format_seconds(0)} ETA {format_seconds(0)} ({human_readable_size(0)}/s)', layout=TildeLayout)
		self.progress_total = urwid.ProgressBar('dialog', 'progress', 0, (total_size or 1))
		w = urwid.Columns([(1, urwid.Text('[')), self.progress_total, (1, urwid.Text(']'))])
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
		self.btn_nodb = urwid.Button('No DB', lambda x: self.on_nodb())
		attr_btn_nodb = urwid.AttrMap(self.btn_nodb, 'dialog', 'dialog_focus')
		w = urwid.Columns([urwid.Divider(' '), (8, attr_btn_skip), (1, urwid.Text(' ')), (12, attr_btn_suspend), (1, urwid.Text(' ')), (9, attr_btn_abort), (1, urwid.Text(' ')), (9, attr_btn_nodb), urwid.Divider(' ')])
		w = urwid.LineBox(urwid.Filler(w), tlcorner='├', trcorner='┤')
		bottom = urwid.Padding(w, left=1, right=1)

		w = urwid.Pile([
			(1, urwid.Filler(urwid.Text(' '))),
			(7, top),
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
			self.controller.screen.close_dialog()
			self.controller.suspend.discard(self.ev_suspend)
			self.on_complete(info['result'], info['error'], info['skipped'], info['aborted'])
		else:
			self.source.set_text(info['cur_source'])
			self.target.set_text(info['cur_target'])
			self.progress_current.done = info['cur_size'] or 1

			bps = info['cur_bytes'] / (info['cur_time'] or 1)
			eta = max(int(round((info['cur_size'] - info['cur_bytes']) / (bps or 1))), 0)
			self.time_current.set_text(f'{human_readable_size(info["cur_bytes"])}/{human_readable_size(info["cur_size"])} ETA {format_seconds(eta)} ({human_readable_size(int(round(bps)))}/s)')
			self.progress_current.set_completion(info['cur_bytes'])

			self.divider.set_title(f'Total: {human_readable_size(info["bytes"])}/{human_readable_size(self.total_size)}')
			self.files.set_text(f'Files processed: {info["files"]}/{self.num_files}')

			bps = info['bytes'] / (info['time'] or 1)
			eta = max(int(round((self.total_size - info['bytes']) / (bps or 1))), 0)
			self.time.set_text(f'Time: {format_seconds(info["time"])} ETA {format_seconds(eta)} ({human_readable_size(int(round(bps)))}/s)')
			self.progress_total.set_completion(info['bytes'])

		return retval

	def on_skip(self):
		if self.aborted:
			return

		self.ev_skip.set()

		if not self.ev_suspend.is_set():
			self.on_suspend()

	def on_suspend(self):
		if self.aborted:
			return

		if self.ev_suspend.is_set():
			self.ev_suspend.clear()
			self.btn_suspend.set_label('Continue')
		else:
			self.ev_suspend.set()
			self.btn_suspend.set_label('Suspend')

	def on_abort(self):
		if self.aborted:
			return

		self.ev_abort.set()

		if not self.ev_suspend.is_set():
			self.on_suspend()

		self.aborted = True

	def on_nodb(self):
		self.ev_nodb.set()

