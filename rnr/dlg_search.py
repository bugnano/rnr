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

from types import SimpleNamespace

from .utils import TildeLayout


class DlgSearch(urwid.WidgetWrap):
	def __init__(self, screen, on_ok, on_cancel, text_file=True, backwards=False):
		self.screen = screen
		self.on_ok = on_ok
		self.on_cancel = on_cancel

		label = urwid.Text('Enter search string:', layout=TildeLayout)
		self.edit = urwid.Edit(wrap='clip')
		w = urwid.AttrMap(self.edit, 'input', 'input')
		w = urwid.SimpleFocusListWalker([
			label,
			w,
		])
		w = urwid.ListBox(w)
		w = urwid.LineBox(urwid.Padding(w, left=1, right=1), 'Search', title_attr='dialog_title', bline='')
		top = urwid.Padding(w, left=1, right=1)

		bgroup = []
		self.btn_normal = urwid.RadioButton(bgroup, 'Normal')
		attr_btn_normal = urwid.AttrMap(self.btn_normal, 'dialog', 'dialog_focus')
		self.btn_regex = urwid.RadioButton(bgroup, 'Regular expression')
		attr_btn_regex = urwid.AttrMap(self.btn_regex, 'dialog', 'dialog_focus')
		self.btn_hex = urwid.CheckBox('Hexadecimal')
		attr_btn_hex = urwid.AttrMap(self.btn_hex, 'dialog', 'dialog_focus')
		self.btn_wildcard = urwid.RadioButton(bgroup, 'Wildcard search')
		attr_btn_wildcard = urwid.AttrMap(self.btn_wildcard, 'dialog', 'dialog_focus')
		self.btn_normal.set_state(True)
		if text_file:
			w = urwid.SimpleFocusListWalker([
				attr_btn_normal,
				attr_btn_regex,
				attr_btn_wildcard,
			])
			height_middle = 4
		else:
			w = urwid.SimpleFocusListWalker([
				attr_btn_hex,
			])
			height_middle = 2

		left = urwid.BoxAdapter(urwid.ListBox(w), 5)

		self.btn_case = urwid.CheckBox('Case sensitive')
		attr_btn_case = urwid.AttrMap(self.btn_case, 'dialog', 'dialog_focus')
		self.btn_backwards = urwid.CheckBox('Backwards')
		attr_btn_backwards = urwid.AttrMap(self.btn_backwards, 'dialog', 'dialog_focus')
		self.btn_words = urwid.CheckBox('Whole words')
		attr_btn_words = urwid.AttrMap(self.btn_words, 'dialog', 'dialog_focus')
		self.btn_backwards.set_state(backwards)
		if text_file:
			w = urwid.SimpleFocusListWalker([
				attr_btn_case,
				attr_btn_backwards,
				attr_btn_words,
			])
		else:
			w = urwid.SimpleFocusListWalker([
				attr_btn_backwards,
			])

		right = urwid.BoxAdapter(urwid.ListBox(w), 5)

		w = urwid.Columns([urwid.Filler(left), urwid.Filler(right)])
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
			(height_middle, middle),
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
			elif key in ('left', 'down', 'up', 'right', ' ', 'enter'):
				return super().keypress(size, key)
			elif key == 'h':
				return super().keypress(size, 'left')
			elif key == 'j':
				return super().keypress(size, 'down')
			elif key == 'k':
				return super().keypress(size, 'up')
			elif key == 'l':
				return super().keypress(size, 'right')
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
		if self.btn_regex.state:
			mode = 'regex'
		elif self.btn_wildcard.state:
			mode = 'wildcard'
		else:
			mode = 'normal'

		flags = SimpleNamespace(
			hex=self.btn_hex.state,
			case=self.btn_case.state,
			backwards=self.btn_backwards.state,
			words=self.btn_words.state,
		)

		self.on_ok(self.edit.get_edit_text(), mode, flags)

