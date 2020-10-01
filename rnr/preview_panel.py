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

import re
import stat
import pwd
import grp
import functools
import collections
import shutil
import subprocess
import signal
import unicodedata

from pathlib import Path

import urwid

from fuzzyfinder import fuzzyfinder

from . import rnrview

from .utils import (human_readable_size, format_date, tar_stem, tar_suffix, TildeLayout, TLineWidget)
from .debug_print import (debug_print, debug_pprint)


class PreviewPanel(urwid.WidgetWrap):
	def __init__(self, controller):
		self.controller = controller

		self.title = TLineWidget(urwid.Text(' (Preview) ', layout=TildeLayout), title_align='left', lcorner='┌', rcorner='┐')
		title = urwid.AttrMap(self.title, 'panel')

		self.walker = urwid.SimpleFocusListWalker([])
		self.listbox = rnrview.FileViewListBox(controller, controller.tabsize, use_line_highlight=True)
		self.attr_listbox = urwid.AttrMap(self.listbox, 'Text')
		listbox = urwid.LineBox(self.attr_listbox, tline='', bline='')
		listbox = urwid.AttrMap(listbox, 'panel')

		self.footer = TLineWidget(urwid.Text('', layout=TildeLayout), title_align='right', lcorner='└', rcorner='┘')
		footer = urwid.AttrMap(self.footer, 'panel')

		self.pile = urwid.Pile([('pack', title), listbox, ('pack', footer)])

		self.focused = False

		self.cwd = Path.cwd()

		super().__init__(self.pile)

	def read_file(self, filename, file_size):
		try:
			self.attr_listbox.set_attr_map({None: 'Text'})
			self.listbox.read_file(filename, file_size)
			self.cwd = Path(filename).parent
		except OSError:
			self.listbox.clear()

	def read_directory(self, filename):
		try:
			self.attr_listbox.set_attr_map({None: 'panel'})
			self.listbox.read_directory(filename)
			self.cwd = Path(filename)
		except OSError:
			self.listbox.clear()

	def clear(self):
		self.listbox.clear()

	def set_title_attr(self, attr):
		self.title.set_title_attr(attr)

	def set_title(self, title):
		self.title.set_title(f' (Preview) {str(title)} ')

	def clear_title(self):
		self.title.set_title(f' (Preview) ')

