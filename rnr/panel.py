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

import stat
import pwd
import grp
import datetime
import functools
import collections
import shutil
import subprocess
import signal

from pathlib import Path

import urwid

from fuzzyfinder import fuzzyfinder

from .tilde_layout import TildeLayout
from .tline_widget import TLineWidget
from .debug_print import debug_print


def human_readable_size(size):
	if size < 1024:
		return f'{size:d}B'

	for suffix in ['K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']:
		size /= 1024
		if size < 1024:
			break

	return f'{size:.{max(4 - len(str(int(size))), 1)}f}{suffix}'

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


class SelectableColumns(urwid.Columns):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self._selectable = True

	def keypress(self, size, key):
		return key


class VimListBox(urwid.ListBox):
	def keypress(self, size, key):
		if self.controller.leader:
			return key

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
		elif key == 'f3':
			try:
				self.model.view(self.model.walker.get_focus()[0].model)
			except AttributeError:
				pass
		elif key == 'f4':
			try:
				self.model.edit(self.model.walker.get_focus()[0].model)
			except AttributeError:
				pass
		elif key in ('insert', ' '):
			if self.model.tag_toggle():
				if (self.focus_position + 1) < len(self.model.walker):
					super().keypress(size, 'down')
		elif key in ('*', 'v'):
			self.model.tag_toggle_all()
		else:
			return super().keypress(size, key)


class Panel(urwid.WidgetWrap):
	def __init__(self, controller):
		self.controller = controller

		self.title = TLineWidget(urwid.Text('', layout=TildeLayout), title_align='left', lcorner='┌', rcorner='┐')
		title = urwid.AttrMap(self.title, 'panel')

		self.walker = urwid.SimpleFocusListWalker([])
		self.listbox = VimListBox(self.walker)
		self.listbox.model = self
		self.listbox.controller = controller
		listbox = urwid.LineBox(self.listbox, tline='', bline='')
		listbox = urwid.AttrMap(listbox, 'panel')

		self.details_separator = TLineWidget(urwid.Text('─', layout=TildeLayout))
		details_separator = urwid.AttrMap(self.details_separator, 'panel')

		self.details = urwid.Text(' ', layout=TildeLayout)
		details = urwid.LineBox(self.details, tline='', bline='')
		details = urwid.AttrMap(details, 'panel')

		self.footer = TLineWidget(urwid.Text('', layout=TildeLayout), title_align='right', lcorner='└', rcorner='┘')
		footer = urwid.AttrMap(self.footer, 'panel')

		w = urwid.Pile([('pack', title), listbox, ('pack', details_separator), ('pack', details), ('pack', footer)])

		cwd = Path.cwd()
		self.old_cwd = cwd
		self.cwd = cwd
		self.show_hidden = False
		self.sort_method = 'sort_by_name'
		self.reverse = False
		self.file_filter = ''
		self.forced_focus = None
		self.files = []
		self.shown_files = []
		self.filtered_files = []
		self.tagged_files = set()

		self.chdir(cwd)
		self.walker.set_focus(0)

		super().__init__(w)

	def chdir(self, cwd):
		self.title.set_title(f' {str(cwd)} ')
		self.file_filter = ''
		self.tagged_files.clear()
		self.update_tagged_count()

		if self._reload(cwd, self.cwd):
			self.old_cwd = self.cwd
			self.cwd = cwd
		else:
			self.title.set_title(f' {str(self.cwd)} ')

	def reload(self, focus_path=None):
		try:
			obj, focus_position = self.walker.get_focus()
			if focus_path is None:
				focus_path = obj.model['file']
		except AttributeError:
			focus_path = None
			focus_position = 0

		self._reload(self.cwd, focus_path, focus_position)

	def _reload(self, cwd, focus_path, focus_position=0):
		cwd = Path(cwd)

		uid_cache = Cache(lambda x: pwd.getpwuid(x).pw_name)
		gid_cache = Cache(lambda x: grp.getgrgid(x).gr_name)

		files = []
		try:
			for file in cwd.iterdir():
				obj = {
					'file': file,
					'name': file.name.casefold(),
					'extension': file.suffix.casefold(),
				}

				lstat = file.lstat()
				obj['lstat'] = lstat

				if stat.S_ISLNK(lstat.st_mode):
					try:
						st = file.stat()
						if stat.S_ISDIR(st.st_mode):
							obj['label'] = f'~{file.name}'
							obj['palette'] = 'dir_symlink'
						else:
							obj['label'] = f'@{file.name}'
							obj['palette'] = 'symlink'
					except (FileNotFoundError, PermissionError):
						st = lstat
						obj['label'] = f'!{file.name}'
						obj['palette'] = 'stalelink'
				else:
					st = lstat
					if stat.S_ISDIR(st.st_mode):
						obj['label'] = f'/{file.name}'
						obj['palette'] = 'directory'
					elif stat.S_ISCHR(lstat.st_mode):
						obj['label'] = f'-{file.name}'
						obj['palette'] = 'device'
					elif stat.S_ISBLK(lstat.st_mode):
						obj['label'] = f'+{file.name}'
						obj['palette'] = 'device'
					elif stat.S_ISFIFO(lstat.st_mode):
						obj['label'] = f'|{file.name}'
						obj['palette'] = 'special'
					elif stat.S_ISSOCK(lstat.st_mode):
						obj['label'] = f'={file.name}'
						obj['palette'] = 'special'
					elif lstat.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
						obj['label'] = f'*{file.name}'
						obj['palette'] = 'executable'
					else:
						obj['label'] = f' {file.name}'
						obj['palette'] = 'panel'

				obj['stat'] = st

				if stat.S_ISDIR(st.st_mode):
					try:
						length =len(list(file.iterdir()))
						obj['length'] = (length,)
						obj['size'] = str(length)
					except (FileNotFoundError, PermissionError):
						obj['length'] = (-1,)
						obj['size'] = '?'
				elif stat.S_ISCHR(lstat.st_mode) or stat.S_ISBLK(lstat.st_mode):
						major = os.major(lstat.st_rdev)
						minor = os.minor(lstat.st_rdev)
						obj['length'] = (major, minor)
						obj['size'] = f'{major},{minor}'
				else:
					length = lstat.st_size
					obj['length'] = (length,)
					obj['size'] = human_readable_size(length)

				obj['details'] = f'{stat.filemode(lstat.st_mode)} {lstat.st_nlink} {uid_cache[lstat.st_uid]} {gid_cache[lstat.st_gid]}'

				if stat.S_ISLNK(lstat.st_mode):
					obj['details'] = f'{obj["details"]} -> {os.readlink(file)}'
				else:
					obj['details'] = f'{obj["details"]} {file.name}'

				files.append(obj)
		except PermissionError:
			return False

		self.files = files
		self.apply_hidden(self.show_hidden)
		self.apply_filter(self.file_filter)
		self.update_list_box(focus_path, focus_position)
		self.footer.set_title(f' Free: {human_readable_size(shutil.disk_usage(cwd).free)} ')

		return True

	def update_list_box(self, focus_path, focus_position=0):
		self.filtered_files.sort(key=functools.cmp_to_key(functools.partial(globals()[self.sort_method], reverse=self.reverse)), reverse=self.reverse)

		focus = -1
		labels = []
		for file in self.filtered_files:
			if file['file'] in self.tagged_files:
				attr_map = 'marked'
				focus_map = 'markselect'
			else:
				attr_map = file['palette']
				focus_map = 'selected'

			w = urwid.AttrMap(SelectableColumns([urwid.Text(file['label'], layout=TildeLayout), ('pack', urwid.Text(file['size'])), ('pack', urwid.Text(format_date(file['lstat'].st_mtime)))], dividechars=1), attr_map, focus_map)
			w.model = file

			if file['file'] == focus_path:
				focus = len(labels)

			labels.append(w)

		self.walker[:] = labels

		if focus < 0:
			focus = min(focus_position, len(labels) - 1)

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
		else:
			self.controller.loop.stop()
			subprocess.run([self.controller.opener, file['file'].name], cwd=self.cwd)
			self.controller.loop.start()
			os.kill(os.getpid(), signal.SIGWINCH)
			self.controller.reload()

	def view(self, file):
		if stat.S_ISDIR(file['stat'].st_mode):
			self.chdir(file['file'])
		else:
			self.controller.loop.stop()
			subprocess.run([self.controller.pager, file['file'].name], cwd=self.cwd)
			self.controller.loop.start()
			os.kill(os.getpid(), signal.SIGWINCH)
			self.controller.reload()

	def edit(self, file):
		self.controller.loop.stop()
		subprocess.run([self.controller.editor, file['file'].name], cwd=self.cwd)
		self.controller.loop.start()
		os.kill(os.getpid(), signal.SIGWINCH)
		self.controller.reload()

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
				focus_path = self.get_focus()['file']
			except TypeError:
				focus_path = None

		self.apply_filter(filter)

		if filter:
			try:
				focus_path = self.filtered_files[0]['file']
			except IndexError:
				focus_path = None

		self.update_list_box(focus_path)

	def get_focus(self):
		try:
			return self.walker.get_focus()[0].model
		except AttributeError:
			return None

	def force_focus(self):
		self.remove_force_focus()

		self.forced_focus = self.walker.get_focus()[0]

		try:
			file = self.forced_focus.model

			if file['file'] in self.tagged_files:
				attr_map = 'markselect'
			else:
				attr_map = 'selected'

			self.forced_focus.set_attr_map({None: attr_map})
		except AttributeError:
			pass

	def remove_force_focus(self):
		try:
			file = self.forced_focus.model

			if file['file'] in self.tagged_files:
				attr_map = 'marked'
			else:
				attr_map = file['palette']

			self.forced_focus.set_attr_map({None: attr_map})
		except AttributeError:
			pass

		self.forced_focus = None

	def toggle_hidden(self):
		self.apply_hidden(not self.show_hidden)
		self.apply_filter(self.file_filter)

		try:
			focus_path = self.get_focus()['file']
		except TypeError:
			focus_path = None

		self.update_list_box(focus_path)

	def sort(self, sort_method, reverse=False):
		self.sort_method = sort_method
		self.reverse = reverse

		try:
			focus_path = self.get_focus()['file']
		except TypeError:
			focus_path = None

		self.update_list_box(focus_path)

	def update_tagged_count(self):
		if self.tagged_files:
			self.details_separator.set_title(f' {len(self.tagged_files)} File(s) Tagged ')
			self.details_separator.set_title_attr('marked')
		else:
			self.details_separator.set_title('─')
			self.details_separator.set_title_attr('panel')

	def tag_toggle(self):
		try:
			line = self.walker.get_focus()[0]
			file = line.model['file']
		except AttributeError:
			return False

		if file in self.tagged_files:
			self.tagged_files.discard(file)
			line.set_attr_map({None: line.model['palette']})
			line.set_focus_map({None: 'selected'})
		else:
			self.tagged_files.add(file)
			line.set_attr_map({None: 'marked'})
			line.set_focus_map({None: 'markselect'})

		self.update_tagged_count()

		return True

	def tag_toggle_all(self):
		for line in self.walker:
			file = line.model['file']

			if file in self.tagged_files:
				self.tagged_files.discard(file)
				line.set_attr_map({None: line.model['palette']})
				line.set_focus_map({None: 'selected'})
			else:
				self.tagged_files.add(file)
				line.set_attr_map({None: 'marked'})
				line.set_focus_map({None: 'markselect'})

		self.update_tagged_count()

	def tag_glob(self, pattern):
		try:
			for line in self.walker:
				file = line.model['file']

				if file.match(pattern):
					self.tagged_files.add(file)
					line.set_attr_map({None: 'marked'})
					line.set_focus_map({None: 'markselect'})
		except ValueError:
			pass

		self.update_tagged_count()

	def untag_glob(self, pattern):
		try:
			for line in self.walker:
				file = line.model['file']

				if file.match(pattern):
					self.tagged_files.discard(file)
					line.set_attr_map({None: line.model['palette']})
					line.set_focus_map({None: 'selected'})
		except ValueError:
			pass

		self.update_tagged_count()

	def untag_all(self):
		for line in self.walker:
			file = line.model['file']

			self.tagged_files.discard(file)
			line.set_attr_map({None: line.model['palette']})
			line.set_focus_map({None: 'selected'})

		self.update_tagged_count()

	def get_tagged_files(self):
		if self.tagged_files:
			return sorted(self.tagged_files)
		else:
			try:
				file = self.get_focus()['file']
			except TypeError:
				file = None

			if file:
				return [file]
			else:
				return []

