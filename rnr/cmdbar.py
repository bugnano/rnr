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

import urwid

from .debug_print import debug_print


class CmdEdit(urwid.Edit):
	def keypress(self, size, key):
		if key in ('up', 'down'):
			pass
		elif key == 'backspace':
			if self.edit_pos:
				return super().keypress(size, key)
		else:
			return super().keypress(size, key)


class CmdBar(urwid.WidgetWrap):
	def __init__(self, controller, screen):
		self.controller = controller
		self.screen = screen

		self.action = None
		self.leader = ''
		self.file = None

		self.edit = CmdEdit()

		w = urwid.AttrMap(self.edit, 'default')

		super().__init__(w)

		urwid.connect_signal(self.edit, 'change', self.on_change)

	def on_change(self, edit, new_edit_text):
		if self.action == 'filter':
			self.screen.center.focus.filter(new_edit_text)
			self.screen.center.focus.force_focus()

	def reset(self):
		self.edit.set_caption('')
		self.edit.set_edit_text('')
		self.screen.pile.focus_position = 0
		self.screen.center.focus.remove_force_focus()

		self.action = None
		self.leader = ''

	def execute(self):
		if self.action == 'mkdir':
			new_dir = pathlib.Path(self.edit.get_edit_text())
			if new_dir.is_absolute():
				new_dir = pathlib.Path(os.path.normpath(new_dir))
			else:
				new_dir = pathlib.Path(os.path.normpath(self.file / new_dir))

			try:
				os.makedirs(new_dir, exist_ok=True)
				self.controller.reload()
			except (PermissionError, FileExistsError) as e:
				self.controller.error(f'{e.strerror} ({e.errno})')
		if self.action == 'rename':
			new_name = pathlib.Path(self.edit.get_edit_text())
			if new_name.is_absolute():
				new_name = pathlib.Path(os.path.normpath(new_name))
			else:
				new_name = pathlib.Path(os.path.normpath(self.file.parent / new_name))

			try:
				if new_name.exists():
					self.controller.error(f'File already exists')
				else:
					self.file.rename(new_name)
					self.controller.reload(new_name, old_focus=self.file, preserve_pos=True)
			except OSError as e:
				self.controller.error(f'{e.strerror} ({e.errno})')

		self.action = None
		self.leader = ''

		self.edit.set_caption('')
		self.edit.set_edit_text('')
		self.screen.pile.focus_position = 0
		self.screen.center.focus.remove_force_focus()

	def set_leader(self, leader):
		self.leader = leader
		self.edit.set_caption(self.leader)

	def prepare_action(self, action, caption, text, edit_pos=-1):
		self.action = action
		self.edit.set_caption(caption)
		self.edit.set_edit_text(text)
		if edit_pos < 0:
			self.edit.set_edit_pos(len(text))
		else:
			self.edit.set_edit_pos(edit_pos)
		self.screen.pile.focus_position = 1
		self.screen.center.focus.force_focus()

	def filter(self):
		self.prepare_action('filter', '/', self.screen.center.focus.file_filter)

	def mkdir(self, cwd):
		self.file = cwd
		self.prepare_action('mkdir', 'mkdir: ', '')

	def rename(self, file, mode):
		self.file = file
		text = file.name
		if mode == 'replace':
			text = ''
			edit_pos = -1
		elif mode == 'insert':
			edit_pos = 0
		elif mode == 'append_before':
			edit_pos = len(file.stem)
		else:
			edit_pos = -1

		self.prepare_action('rename', 'rename: ', text, edit_pos)

