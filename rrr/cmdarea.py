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

from .debug_print import debug_print


class CmdEdit(urwid.Edit):
	def keypress(self, size, key):
		if key in ('up', 'down'):
			pass
		else:
			return super().keypress(size, key)


class CmdArea(urwid.WidgetWrap):
	def __init__(self, screen):
		self.screen = screen

		self.action = None
		self.leader = ''

		self.edit = CmdEdit()
		self.edit.screen = screen

		w = urwid.Filler(self.edit)
		w = urwid.AttrMap(w, 'normal')

		super().__init__(w)

		urwid.connect_signal(self.edit, 'change', self.on_change)

	def on_change(self, edit, new_edit_text):
		if self.action == 'filter':
			self.screen.center.focus.filter(new_edit_text)
			self.screen.center.focus.force_focus()

	def filter(self):
		self.action = 'filter'

		self.edit.set_caption('/')
		self.edit.set_edit_text(self.screen.center.focus.file_filter)
		self.edit.set_edit_pos(len(self.screen.center.focus.file_filter))
		self.screen.pile.focus_position = 1
		self.screen.center.focus.force_focus()

	def reset(self):
		self.edit.set_caption('')
		self.edit.set_edit_text('')
		self.screen.pile.focus_position = 0
		self.screen.center.focus.remove_force_focus()

		self.action = None
		self.leader = ''

	def execute(self):
		self.action = None

		self.edit.set_caption('')
		self.edit.set_edit_text('')
		self.screen.pile.focus_position = 0
		self.screen.center.focus.remove_force_focus()

	def set_leader(self, leader):
		self.leader = leader
		self.edit.set_caption(self.leader)

