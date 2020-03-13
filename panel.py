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

import urwid


def human_readable_size(size):
	if size < 1024:
		return f'{size:d} B'

	for suffix in ['K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']:
		size /= 1024
		if size < 1024:
			break

	return f'{size:.{max(4 - len(str(int(size))), 1)}f} {suffix}'


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
		elif key == 'j':
			return super().keypress(size, 'down')
		elif key == 'k':
			return super().keypress(size, 'up')
		elif key in ('l', 'right', 'enter'):
			try:
				self.model.execute(*self.model.walker.get_focus()[0].model)
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
		self.chdir('.')
		self.walker.set_focus(0)

		super().__init__(w)

	def chdir(self, cwd):
		old_cwd = self.cwd
		self.cwd = pathlib.Path(cwd).resolve()

		files = []
		dirs = []
		try:
			for file in self.cwd.iterdir():
				try:
					st = file.stat()
					if stat.S_ISDIR(st.st_mode):
						dirs.append((file, st))
					else:
						files.append((file, st))
				except (FileNotFoundError, PermissionError):
					pass
		except PermissionError:
			self.cwd = old_cwd
			return

		files.sort()
		dirs.sort()

		focus = 0
		labels = []
		for file, st in dirs:
			try:
				w = urwid.AttrMap(SelectableColumns([urwid.Text(f'{file.name}/', layout=TildeLayout), ('pack', urwid.Text(f'{len(list(file.iterdir()))}'))], dividechars=1), 'dir', 'focus')
			except PermissionError:
				w = urwid.AttrMap(SelectableColumns([urwid.Text(f'{file.name}/', layout=TildeLayout), ('pack', urwid.Text(f'?'))], dividechars=1), 'dir', 'focus')
			except FileNotFoundError:
				continue

			if file == old_cwd:
				focus = len(labels)

			w.model = (file, st)
			labels.append(w)

		for file, st in files:
			try:
				w = urwid.AttrMap(SelectableColumns([urwid.Text(f'{file.name}', layout=TildeLayout), ('pack', urwid.Text(f'{human_readable_size(st.st_size)}'))], dividechars=1), 'bg', 'focus')
			except FileNotFoundError:
				continue

			w.model = (file, st)
			labels.append(w)

		self.walker[:] = labels
		self.walker.set_focus(focus)

		self.border.set_title(str(self.cwd))

	def execute(self, file, st):
		if stat.S_ISDIR(st.st_mode):
			self.chdir(file)

