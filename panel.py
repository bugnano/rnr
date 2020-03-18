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

import pathlib
import stat
import datetime
import functools

import urwid

from debug_print import debug_print


def human_readable_size(size):
	if size < 1024:
		return f'{size:d} B'

	for suffix in ['K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']:
		size /= 1024
		if size < 1024:
			break

	return f'{size:.{max(4 - len(str(int(size))), 1)}f} {suffix}'

def format_date(d):
	d = datetime.datetime.fromtimestamp(d)
	today = datetime.date.today()
	if d.date() == today:
		return d.strftime('%H:%M').center(7)
	elif d.year == today.year:
		return d.strftime('%b %d').center(7)
	else:
		return d.strftime('%Y-%m').center(7)


def sort_by_name(a, b):
	if stat.S_ISDIR(a['stat'].st_mode) and (not stat.S_ISDIR(b['stat'].st_mode)):
		return -1
	elif (not stat.S_ISDIR(a['stat'].st_mode)) and stat.S_ISDIR(b['stat'].st_mode):
		return 1
	elif a['file'].name < b['file'].name:
		return -1
	elif a['file'].name > b['file'].name:
		return 1
	else:
		return 0

def sort_by_extension(a, b):
	if stat.S_ISDIR(a['stat'].st_mode) and (not stat.S_ISDIR(b['stat'].st_mode)):
		return -1
	elif (not stat.S_ISDIR(a['stat'].st_mode)) and stat.S_ISDIR(b['stat'].st_mode):
		return 1
	elif a['file'].suffix < b['file'].suffix:
		return -1
	elif a['file'].suffix > b['file'].suffix:
		return 1
	else:
		return sort_by_name(a, b)

def sort_by_date(a, b):
	if stat.S_ISDIR(a['stat'].st_mode) and (not stat.S_ISDIR(b['stat'].st_mode)):
		return -1
	elif (not stat.S_ISDIR(a['stat'].st_mode)) and stat.S_ISDIR(b['stat'].st_mode):
		return 1
	elif a['stat'].st_mtime < b['stat'].st_mtime:
		return -1
	elif a['stat'].st_mtime > b['stat'].st_mtime:
		return 1
	else:
		return sort_by_name(a, b)

def sort_by_size(a, b):
	if stat.S_ISDIR(a['stat'].st_mode) and (not stat.S_ISDIR(b['stat'].st_mode)):
		return -1
	elif (not stat.S_ISDIR(a['stat'].st_mode)) and stat.S_ISDIR(b['stat'].st_mode):
		return 1
	elif a['length'] < b['length']:
		return -1
	elif a['length'] > b['length']:
		return 1
	else:
		return sort_by_name(a, b)


class SelectableColumns(urwid.Columns):
	def __init__(self, widget_list, dividechars=0, focus_column=None, min_width=1, box_columns=None):
		super().__init__(widget_list, dividechars, focus_column, min_width, box_columns)

		self._selectable = True

	def keypress(self, size, key):
		return key


class VimListBox(urwid.ListBox):
	def keypress(self, size, key):
		if key in ('h', 'left'):
			self.model.chdir(self.model.cwd.parent)
		elif key in ('j', 'down'):
			try:
				if (self.focus_position + 1) < len(self.model.walker):
					return super().keypress(size, 'down')
			except IndexError:
				pass
		elif key in ('k', 'up'):
			try:
				if self.focus_position > 0:
					return super().keypress(size, 'up')
			except IndexError:
				pass
		elif key in ('l', 'right', 'enter'):
			try:
				self.model.execute(self.model.walker.get_focus()[0].model)
			except AttributeError:
				pass
		elif key == 'g':
			return super().keypress(size, 'home')
		elif key == 'G':
			return super().keypress(size, 'end')
		elif key == 'ctrl b':
			return super().keypress(size, 'page up')
		elif key == 'ctrl f':
			return super().keypress(size, 'page down')
		else:
			return super().keypress(size, key)


class TildeTextLayout(urwid.TextLayout):
	def layout(self, text, width, align, wrap):
		if len(text) <= width:
			return [[(len(text), 0, text.encode('utf-8'))]]

		full_len = max(width - 1, 2)
		half = int(full_len / 2)
		left = half
		right = full_len - left

		return [[(width, 0, f'{text[:left]}~{text[-right:]}'[:width].encode('utf-8'))]]

	def pack(self, maxcol, layout):
		maxwidth = 0
		for l in layout:
			for line in l:
				maxwidth = max(line[0], maxwidth)

		return min(maxwidth, maxcol)

TildeLayout = TildeTextLayout()


class Panel(urwid.WidgetWrap):
	def __init__(self):
		self.walker = urwid.SimpleFocusListWalker([])
		self.listbox = VimListBox(self.walker)
		self.listbox.model = self

		self.border = urwid.LineBox(self.listbox, '.', 'left')

		# WARNING: title_widget and tline_widget are implementation details, and could break in the future
		self.border.title_widget = urwid.Text(' . ', layout=TildeLayout)
		self.border.tline_widget.contents[0] = (self.border.title_widget, self.border.tline_widget.options('pack'))

		w = urwid.AttrMap(self.border, 'bg')

		self.cwd = None
		self.files = []
		self.shown_files = []
		self.filtered_files = []
		self.chdir('.')
		self.walker.set_focus(0)

		super().__init__(w)

	def chdir(self, cwd):
		old_cwd = self.cwd
		self.cwd = pathlib.Path(cwd).resolve()

		self.files = []
		try:
			for file in self.cwd.iterdir():
				obj = {
					'file': file,
				}

				try:
					obj['stat'] = file.stat()
					if stat.S_ISDIR(obj['stat'].st_mode):
						if file.is_symlink():
							obj['name'] = f'~{file.name}'
						else:
							obj['name'] = f'/{file.name}'

						obj['palette'] = 'dir'

						try:
							obj['length'] = len(list(file.iterdir()))
							obj['size'] = str(obj['length'])
						except (FileNotFoundError, PermissionError):
							obj['length'] = -1
							obj['size'] = '?'
					else:
						if stat.S_ISLNK(obj['stat'].st_mode):
							obj['name'] = f'@{file.name}'
							obj['palette'] = 'bg'
						elif obj['stat'].st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
							obj['name'] = f'*{file.name}'
							obj['palette'] = 'executable'
						else:
							obj['name'] = f' {file.name}'
							obj['palette'] = 'bg'

						obj['length'] = obj['stat'].st_size
						obj['size'] = human_readable_size(obj['length'])

					self.files.append(obj)
				except (FileNotFoundError, PermissionError):
					pass
		except PermissionError:
			self.cwd = old_cwd
			return

		self.shown_files = [x for x in self.files if not x['file'].name.startswith('.')]
		self.filtered_files = self.shown_files[:]
		self.filtered_files.sort(key=functools.cmp_to_key(sort_by_name))

		focus = 0
		labels = []
		for file in self.filtered_files:
			w = urwid.AttrMap(SelectableColumns([urwid.Text(file['name'], layout=TildeLayout), ('pack', urwid.Text(file['size'])), ('pack', urwid.Text(format_date(file['stat'].st_mtime)))], dividechars=1), file['palette'], 'focus')
			w.model = file

			if file['file'] == old_cwd:
				focus = len(labels)

			labels.append(w)

		self.walker[:] = labels
		self.walker.set_focus(focus)

		self.border.set_title(str(self.cwd))

	def execute(self, file):
		if stat.S_ISDIR(file['stat'].st_mode):
			self.chdir(file['file'])

	def filter(self, filter):
		debug_print(f'filter: {filter}')

