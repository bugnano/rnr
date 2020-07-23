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

from .utils import (human_readable_size, format_seconds, TildeLayout, apply_template)


class DlgCpMv(urwid.WidgetWrap):
	def __init__(self, controller, title, question, dest_dir, on_ok, on_cancel=None):
		self.controller = controller
		self.on_ok = on_ok

		label = urwid.Text(question, layout=TildeLayout)
		self.edit = urwid.Edit(edit_text=dest_dir.replace('%', '%%'), wrap='clip')
		w = urwid.AttrMap(self.edit, 'input', 'input')
		w = urwid.SimpleFocusListWalker([
			label,
			w,
		])
		w = urwid.ListBox(w)
		w = urwid.LineBox(urwid.Padding(w, left=1, right=1), title, title_attr='dialog_title', bline='')
		top = urwid.Padding(w, left=1, right=1)

		label = urwid.Text('On conflict:')
		bgroup = []
		self.btn_overwrite = urwid.RadioButton(bgroup, 'Overwrite')
		attr_btn_overwrite = urwid.AttrMap(self.btn_overwrite, 'dialog', 'dialog_focus')
		self.btn_skip = urwid.RadioButton(bgroup, 'Skip')
		attr_btn_skip = urwid.AttrMap(self.btn_skip, 'dialog', 'dialog_focus')
		self.btn_rename_existing = urwid.RadioButton(bgroup, 'Rename Existing')
		attr_btn_rename_existing = urwid.AttrMap(self.btn_rename_existing, 'dialog', 'dialog_focus')
		self.btn_rename_copy = urwid.RadioButton(bgroup, 'Rename Copy')
		attr_btn_rename_copy = urwid.AttrMap(self.btn_rename_copy, 'dialog', 'dialog_focus')
		self.btn_rename_existing.set_state(True)
		w = urwid.SimpleFocusListWalker([
			label,
			attr_btn_overwrite,
			attr_btn_skip,
			attr_btn_rename_existing,
			attr_btn_rename_copy,
		])
		w = urwid.BoxAdapter(urwid.ListBox(w), 5)
		w = urwid.Columns([urwid.Filler(urwid.Divider(' ')), (19, urwid.Filler(w)), urwid.Filler(urwid.Divider(' '))])
		self.divider = urwid.LineBox(urwid.Padding(w, left=1, right=1), tlcorner='├', trcorner='┤', bline='')
		middle = urwid.Padding(self.divider, left=1, right=1)

		self.btn_ok = urwid.Button('OK', self.on_click_ok)
		attr_btn_ok = urwid.AttrMap(self.btn_ok, 'dialog', 'dialog_focus')
		self.btn_cancel = urwid.Button('Cancel', on_cancel)
		attr_btn_cancel = urwid.AttrMap(self.btn_cancel, 'dialog', 'dialog_focus')
		w = urwid.Columns([urwid.Divider(' '), (6, attr_btn_ok), (1, urwid.Text(' ')), (10, attr_btn_cancel), urwid.Divider(' ')])
		w = urwid.LineBox(urwid.Filler(w), tlcorner='├', trcorner='┤')
		bottom = urwid.Padding(w, left=1, right=1)

		self.pile = urwid.Pile([
			(1, urwid.Filler(urwid.Text(' '))),
			(3, top),
			(6, middle),
			(3, bottom),
			(1, urwid.Filler(urwid.Text(' '))),
		])
		w = urwid.AttrMap(self.pile, 'dialog')

		super().__init__(w)

	def keypress(self, size, key):
		if key in ('esc', 'f10'):
			self.btn_cancel.keypress(size, 'enter')
			return

		if self.pile.focus_position == 1:
			if key == 'tab':
				self.pile.focus_position = 2
			elif key == 'shift tab':
				self.pile.focus_position = 3
			elif key == 'up':
				pass
			elif key.startswith('ctrl ') or key.startswith('meta ') or key.startswith('shift '):
				pass
			elif key.startswith('f') and (len(key) > 1):
				pass
			elif key == 'backspace':
				if self.edit.edit_pos:
					return super().keypress(size, key)
			elif key == 'enter':
				self.btn_ok.keypress(size, 'enter')
				return
			else:
				return super().keypress(size, key)
		elif self.pile.focus_position == 2:
			if key == 'tab':
				self.pile.focus_position = 3
			elif key == 'shift tab':
				self.pile.focus_position = 1
			elif key in ('down', 'up', ' ', 'enter'):
				return super().keypress(size, key)
			elif key == 'j':
				return super().keypress(size, 'down')
			elif key == 'k':
				return super().keypress(size, 'up')
		elif self.pile.focus_position == 3:
			if key == 'tab':
				self.pile.focus_position = 1
			elif key == 'shift tab':
				self.pile.focus_position = 2
			elif key in ('left', 'up', 'right', ' ', 'enter'):
				return super().keypress(size, key)
			elif key == 'h':
				return super().keypress(size, 'left')
			elif key == 'k':
				return super().keypress(size, 'up')
			elif key == 'l':
				return super().keypress(size, 'right')

	def on_click_ok(self, button):
		if self.btn_overwrite.state:
			on_conflict = 'overwrite'
		elif self.btn_rename_existing.state:
			on_conflict = 'rename_existing'
		elif self.btn_rename_copy.state:
			on_conflict = 'rename_copy'
		else:
			on_conflict = 'skip'

		self.on_ok(apply_template(self.edit.get_edit_text(), self.controller.screen, quote=False), on_conflict)

