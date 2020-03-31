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


class DlgError(urwid.WidgetWrap):
	def __init__(self, controller, e):
		self.controller = controller

		w = urwid.Filler(urwid.Text(f' {e} ', align='center', wrap='clip'), top=1, bottom=1)
		w = urwid.LineBox(w, 'Error', title_attr='error_title')
		w = urwid.Padding(w, left=1, right=1)
		w = urwid.Pile([
			(1, urwid.Filler(urwid.Text(' '))),
			(5, w),
			(1, urwid.Filler(urwid.Text(' '))),
		])
		w = urwid.AttrMap(w, 'error')

		super().__init__(w)

	def keypress(self, size, key):
		self.controller.screen.pile.contents[0] = (self.controller.screen.center, self.controller.screen.pile.options())

