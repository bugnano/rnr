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
import pwd
import grp
import datetime
import functools
import collections
import shutil

import urwid

from fuzzyfinder import fuzzyfinder

from .debug_print import debug_print


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


def sort_by_name(a, b, reverse=False):
	if stat.S_ISDIR(a['stat'].st_mode) and (not stat.S_ISDIR(b['stat'].st_mode)):
		return (1 if reverse else -1)
	elif (not stat.S_ISDIR(a['stat'].st_mode)) and stat.S_ISDIR(b['stat'].st_mode):
		return (-1 if reverse else 1)
	elif a['name'] < b['name']:
		return -1
	elif a['name'] > b['name']:
		return 1
	else:
		return 0

def sort_by_extension(a, b, reverse=False):
	if stat.S_ISDIR(a['stat'].st_mode) and (not stat.S_ISDIR(b['stat'].st_mode)):
		return (1 if reverse else -1)
	elif (not stat.S_ISDIR(a['stat'].st_mode)) and stat.S_ISDIR(b['stat'].st_mode):
		return (-1 if reverse else 1)
	elif a['extension'] < b['extension']:
		return -1
	elif a['extension'] > b['extension']:
		return 1
	else:
		return sort_by_name(a, b, reverse)

def sort_by_date(a, b, reverse=False):
	if stat.S_ISDIR(a['stat'].st_mode) and (not stat.S_ISDIR(b['stat'].st_mode)):
		return (1 if reverse else -1)
	elif (not stat.S_ISDIR(a['stat'].st_mode)) and stat.S_ISDIR(b['stat'].st_mode):
		return (-1 if reverse else 1)
	elif a['lstat'].st_mtime < b['lstat'].st_mtime:
		return -1
	elif a['lstat'].st_mtime > b['lstat'].st_mtime:
		return 1
	else:
		return sort_by_name(a, b, reverse)

def sort_by_size(a, b, reverse=False):
	if stat.S_ISDIR(a['stat'].st_mode) and (not stat.S_ISDIR(b['stat'].st_mode)):
		return (1 if reverse else -1)
	elif (not stat.S_ISDIR(a['stat'].st_mode)) and stat.S_ISDIR(b['stat'].st_mode):
		return (-1 if reverse else 1)
	elif a['length'] < b['length']:
		return -1
	elif a['length'] > b['length']:
		return 1
	else:
		return sort_by_name(a, b, reverse)


class Cache(collections.defaultdict):
	def __missing__(self, key):
		if self.default_factory is None:
			raise KeyError(key)

		self[key] = value = self.default_factory(key)

		return value


class TLineWidget(urwid.WidgetWrap):
	def __init__(self, title, title_align='center', title_attr=None, lcorner='├', tline='─', rcorner='┤'):
		self.title_widget = title
		self.title_attr = urwid.AttrMap(self.title_widget, title_attr)
		tline_divider = urwid.Divider(tline)

		if title_align == 'left':
			tline_widgets = [('pack', self.title_attr), tline_divider]
		else:
			tline_widgets = [tline_divider, ('pack', self.title_attr)]
			if title_align == 'center':
				tline_widgets.append(tline_divider)

		self.tline_widget = urwid.Columns(tline_widgets)

		w = urwid.Columns([(1, urwid.Text(lcorner)), (1, urwid.Text(tline)), self.tline_widget, (1, urwid.Text(tline)), (1, urwid.Text(rcorner))])

		super().__init__(w)

	def set_title(self, text):
		self.title_widget.set_text(text)

	def set_title_attr(self, attr):
		self.title_attr.set_attr_map({None: attr})


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
			retval = None

			try:
				if (self.focus_position + 1) < len(self.model.walker):
					retval = super().keypress(size, 'down')
			except IndexError:
				pass

			try:
				self.model.show_details(self.model.walker.get_focus()[0].model)
			except AttributeError:
				self.model.show_details(None)

			return retval
		elif key in ('k', 'up'):
			retval = None

			try:
				if self.focus_position > 0:
					retval = super().keypress(size, 'up')
			except IndexError:
				pass

			try:
				self.model.show_details(self.model.walker.get_focus()[0].model)
			except AttributeError:
				self.model.show_details(None)

			return retval
		elif key in ('l', 'right', 'enter'):
			try:
				self.model.execute(self.model.walker.get_focus()[0].model)
			except AttributeError:
				pass
		elif key in ('g', 'home'):
			retval = super().keypress(size, 'home')

			try:
				self.model.show_details(self.model.walker.get_focus()[0].model)
			except AttributeError:
				self.model.show_details(None)

			return retval
		elif key in ('G', 'end'):
			retval = super().keypress(size, 'end')

			try:
				self.model.show_details(self.model.walker.get_focus()[0].model)
			except AttributeError:
				self.model.show_details(None)

			return retval
		elif key in ('ctrl b', 'page up'):
			retval = super().keypress(size, 'page up')

			try:
				self.model.show_details(self.model.walker.get_focus()[0].model)
			except AttributeError:
				self.model.show_details(None)

			return retval
		elif key in ('ctrl f', 'page down'):
			retval = super().keypress(size, 'page down')

			try:
				self.model.show_details(self.model.walker.get_focus()[0].model)
			except AttributeError:
				self.model.show_details(None)

			return retval
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
		cwd = pathlib.Path.cwd()

		self.title = TLineWidget(urwid.Text('', layout=TildeLayout), title_align='left', lcorner='┌', rcorner='┐')
		title = urwid.AttrMap(self.title, 'bg')

		self.walker = urwid.SimpleFocusListWalker([])
		self.listbox = VimListBox(self.walker)
		self.listbox.model = self
		listbox = urwid.LineBox(self.listbox, tline='', bline='')
		listbox = urwid.AttrMap(listbox, 'bg')

		self.details_separator = TLineWidget(urwid.Text('', layout=TildeLayout))
		details_separator = urwid.AttrMap(self.details_separator, 'bg')

		self.details = urwid.Text(' ', layout=TildeLayout)
		details = urwid.LineBox(self.details, tline='', bline='')
		details = urwid.AttrMap(details, 'bg')

		self.footer = TLineWidget(urwid.Text('', layout=TildeLayout), title_align='right', lcorner='└', rcorner='┘')
		footer = urwid.AttrMap(self.footer, 'bg')

		w = urwid.Pile([('pack', title), listbox, ('pack', details_separator), ('pack', details), ('pack', footer)])

		self.cwd = None
		self.show_hidden = False
		self.sort_method = 'sort_by_name'
		self.reverse = False
		self.file_filter = ''
		self.forced_focus = None
		self.files = []
		self.shown_files = []
		self.filtered_files = []

		self.chdir(cwd)
		self.walker.set_focus(0)

		super().__init__(w)

	def chdir(self, cwd):
		old_cwd = self.cwd
		self.cwd = pathlib.Path(cwd)
		self.title.set_title(f' {str(self.cwd)} ')

		uid_cache = Cache(lambda x: pwd.getpwuid(x).pw_name)
		gid_cache = Cache(lambda x: grp.getgrgid(x).gr_name)

		files = []
		try:
			for file in self.cwd.iterdir():
				obj = {
					'file': file,
					'name': file.name.casefold(),
					'extension': file.suffix.casefold(),
				}

				try:
					lstat = file.lstat()
					obj['lstat'] = lstat

					if stat.S_ISLNK(lstat.st_mode):
						st = file.stat()
					else:
						st = lstat

					obj['stat'] = st

					if stat.S_ISDIR(st.st_mode):
						if stat.S_ISLNK(lstat.st_mode):
							obj['label'] = f'~{file.name}'
						else:
							obj['label'] = f'/{file.name}'

						obj['palette'] = 'dir'

						try:
							obj['length'] = len(list(file.iterdir()))
							obj['size'] = str(obj['length'])
						except (FileNotFoundError, PermissionError):
							obj['length'] = -1
							obj['size'] = '?'
					else:
						if stat.S_ISLNK(lstat.st_mode):
							obj['label'] = f'@{file.name}'
							obj['palette'] = 'bg'
						elif lstat.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
							obj['label'] = f'*{file.name}'
							obj['palette'] = 'executable'
						else:
							obj['label'] = f' {file.name}'
							obj['palette'] = 'bg'

						obj['length'] = lstat.st_size
						obj['size'] = human_readable_size(obj['length'])

					obj['details'] = f'{stat.filemode(lstat.st_mode)} {lstat.st_nlink} {uid_cache[lstat.st_uid]} {gid_cache[lstat.st_gid]}'

					if stat.S_ISLNK(lstat.st_mode):
						obj['details'] = f'{obj["details"]} -> {os.readlink(file)}'
					else:
						obj['details'] = f'{obj["details"]} {file.name}'

					files.append(obj)
				except (FileNotFoundError, PermissionError):
					pass
		except PermissionError:
			self.cwd = old_cwd
			self.title.set_title(f' {str(self.cwd)} ')
			return

		self.files = files
		self.apply_hidden(self.show_hidden)
		self.apply_filter('')
		self.update_list_box(old_cwd)
		self.footer.set_title(f' Free: {human_readable_size(shutil.disk_usage(self.cwd).free)} ')

	def update_list_box(self, focus_path):
		self.filtered_files.sort(key=functools.cmp_to_key(functools.partial(globals()[self.sort_method], reverse=self.reverse)), reverse=self.reverse)

		focus = 0
		labels = []
		for file in self.filtered_files:
			w = urwid.AttrMap(SelectableColumns([urwid.Text(file['label'], layout=TildeLayout), ('pack', urwid.Text(file['size'])), ('pack', urwid.Text(format_date(file['lstat'].st_mtime)))], dividechars=1), file['palette'], 'focus')
			w.model = file

			if file['file'] == focus_path:
				focus = len(labels)

			labels.append(w)

		self.walker[:] = labels
		self.walker.set_focus(focus)

		try:
			self.show_details(self.filtered_files[focus])
		except IndexError:
			self.show_details(None)

	def apply_hidden(self, show_hidden):
		self.show_hidden = show_hidden

		if show_hidden:
			self.shown_files = self.files[:]
		else:
			self.shown_files = [x for x in self.files if not x['file'].name.startswith('.')]

	def apply_filter(self, filter):
		self.file_filter = filter

		if filter:
			self.filtered_files = list(fuzzyfinder(filter, self.shown_files, accessor=lambda x: x['name']))
		else:
			self.filtered_files = self.shown_files[:]

	def execute(self, file):
		if stat.S_ISDIR(file['stat'].st_mode):
			self.chdir(file['file'])

	def set_title_attr(self, attr):
		self.title.set_title_attr(attr)

	def show_details(self, file):
		if file:
			self.details.set_text(file['details'])
		else:
			self.details.set_text(' ')

	def filter(self, filter):
		if not filter:
			try:
				focus_path = self.walker.get_focus()[0].model['file']
			except AttributeError:
				focus_path = None

		self.apply_filter(filter)

		if filter:
			try:
				focus_path = self.filtered_files[0]['file']
			except IndexError:
				focus_path = None

		self.update_list_box(focus_path)

	def force_focus(self):
		self.remove_force_focus()

		self.forced_focus = self.walker.get_focus()[0]

		try:
			self.forced_focus.set_attr_map({None: 'focus'})
		except AttributeError:
			pass

	def remove_force_focus(self):
		try:
			self.forced_focus.set_attr_map({None: self.forced_focus.model['palette']})
		except AttributeError:
			pass

		self.forced_focus = None

	def toggle_hidden(self):
		self.apply_hidden(not self.show_hidden)
		self.apply_filter(self.file_filter)

		try:
			focus_path = self.walker.get_focus()[0].model['file']
		except AttributeError:
			focus_path = None

		self.update_list_box(focus_path)

	def sort(self, sort_method, reverse=False):
		self.sort_method = sort_method
		self.reverse = reverse

		try:
			focus_path = self.walker.get_focus()[0].model['file']
		except AttributeError:
			focus_path = None

		self.update_list_box(focus_path)

