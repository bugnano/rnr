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
				new_dir = new_dir.resolve()
			else:
				new_dir = (self.screen.center.focus.cwd / new_dir).resolve()

			try:
				os.makedirs(new_dir, exist_ok=True)
			except (PermissionError, FileExistsError) as e:
				self.controller.error(f'{e.strerror} ({e.errno})')

			self.controller.reload()

		self.action = None
		self.leader = ''

		self.edit.set_caption('')
		self.edit.set_edit_text('')
		self.screen.pile.focus_position = 0
		self.screen.center.focus.remove_force_focus()

	def set_leader(self, leader):
		self.leader = leader
		self.edit.set_caption(self.leader)

	def prepare_action(self, action, caption, text):
		self.action = action
		self.edit.set_caption(caption)
		self.edit.set_edit_text(text)
		self.edit.set_edit_pos(len(text))
		self.screen.pile.focus_position = 1
		self.screen.center.focus.force_focus()

	def filter(self):
		self.prepare_action('filter', '/', self.screen.center.focus.file_filter)

	def mkdir(self):
		self.prepare_action('mkdir', 'mkdir: ', '')

