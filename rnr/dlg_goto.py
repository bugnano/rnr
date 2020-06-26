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


class DlgGoto(urwid.WidgetWrap):
	def __init__(self, screen, on_ok, on_cancel, label='Hex offset: '):
		self.screen = screen
		self.on_ok = on_ok
		self.on_cancel = on_cancel

		len_label = len(label)
		label = urwid.Text(label)

		self.edit = urwid.Edit(wrap='clip')
		w = urwid.AttrMap(self.edit, 'input', 'input')
		w = urwid.Columns([(1, urwid.Text(' ')), (len_label, label), (24 - len_label, w), (1, urwid.Text(' '))])
		w = urwid.LineBox(urwid.Filler(w), 'Goto', title_attr='dialog_title', bline='')
		top = urwid.Padding(w, left=1, right=1)

		self.btn_ok = urwid.Button('OK', self.on_click_ok)
		attr_btn_ok = urwid.AttrMap(self.btn_ok, 'dialog', 'dialog_focus')
		self.btn_cancel = urwid.Button('Cancel', on_cancel)
		attr_btn_cancel = urwid.AttrMap(self.btn_cancel, 'dialog', 'dialog_focus')
		w = urwid.Columns([urwid.Divider(' '), (6, attr_btn_ok), (1, urwid.Text(' ')), (10, attr_btn_cancel), urwid.Divider(' ')])
		w = urwid.LineBox(urwid.Filler(w), tlcorner='├', trcorner='┤')
		bottom = urwid.Padding(w, left=1, right=1)

		self.pile = urwid.Pile([
			(1, urwid.Filler(urwid.Text(' '))),
			(2, top),
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
			if key in ('tab', 'shift tab'):
				self.pile.focus_position = 2
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
			if key in ('tab', 'shift tab'):
				self.pile.focus_position = 1
			elif key in ('left', 'up', 'right', ' ', 'enter'):
				return super().keypress(size, key)
			elif key == 'h':
				return super().keypress(size, 'left')
			elif key == 'k':
				return super().keypress(size, 'up')
			elif key == 'l':
				return super().keypress(size, 'right')

	def on_click_ok(self, button):
		self.on_ok(self.edit.get_edit_text())

