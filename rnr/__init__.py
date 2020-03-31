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

import argparse
import pathlib
import shutil
import stat

import urwid

import xdg.BaseDirectory

CONFIG_DIR = pathlib.Path(xdg.BaseDirectory.save_config_path('rnr'))

sys.path.insert(0, str(CONFIG_DIR))
_dont_write_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True

try:
	from config import *
except ModuleNotFoundError:
	try:
		shutil.copy(pathlib.Path(__file__).parent / 'config.py', CONFIG_DIR)
		print(sys.path)
		from config import *
	except (ModuleNotFoundError, FileNotFoundError, PermissionError, IsADirectoryError):
		from .config import *

sys.dont_write_bytecode = _dont_write_bytecode
del _dont_write_bytecode
sys.path.pop(0)

from . import panel
from . import cmdbar
from . import buttonbar

from .bookmarks import (Bookmarks, BOOKMARK_KEYS)
from .dlg_error import (DlgError)
from .debug_print import (debug_print, set_debug_fh)


__version__ = '0.0.1'


PALETTE = [
	('default', 'default', 'default'),

	('panel', PANEL_FG, PANEL_BG),
	('reverse', REVERSE_FG, REVERSE_BG),
	('selected', SELECTED_FG, SELECTED_BG),
	('marked', MARKED_FG, PANEL_BG),
	('markselect', MARKSELECT_FG, SELECTED_BG),

	('directory', DIRECTORY_FG, PANEL_BG),
	('executable', EXECUTABLE_FG, PANEL_BG),
	('symlink', SYMLINK_FG, PANEL_BG),
	('stalelink', STALELINK_FG, PANEL_BG),
	('device', DEVICE_FG, PANEL_BG),
	('special', SPECIAL_FG, PANEL_BG),
	('archive', ARCHIVE_FG, PANEL_BG),

	('hotkey', HOTKEY_FG, HOTKEY_BG),

	('error', ERROR_FG, ERROR_BG),
	('error_title', ERROR_TITLE_FG, ERROR_BG),
]


class Screen(urwid.WidgetWrap):
	def __init__(self, controller):
		self.left = panel.Panel(controller)
		self.right = panel.Panel(controller)
		self.center = urwid.Columns([self.left, self.right])
		self.command_bar = cmdbar.CmdBar(controller, self)
		w = urwid.Filler(self.command_bar)
		pile_widgets = [self.center, (1, w)]

		if SHOW_BUTTONBAR:
			bottom = buttonbar.ButtonBar()
			w = urwid.Filler(bottom)
			pile_widgets.append((1, w))

		self.pile = urwid.Pile(pile_widgets)
		self.pile.focus_position = 0
		self.update_focus()

		super().__init__(self.pile)

	def update_focus(self):
		for i, e in enumerate(self.center.contents):
			if i == self.center.focus_position:
				e[0].set_title_attr('reverse')
			else:
				e[0].set_title_attr('panel')


class App(object):
	def __init__(self, printwd):
		self.printwd = printwd

		self.opener = OPENER
		self.pager = PAGER
		self.editor = EDITOR

		self.screen = Screen(self)
		self.leader = ''

		self.bookmarks = Bookmarks(CONFIG_DIR / 'bookmarks')
		if 'h' not in self.bookmarks:
			self.bookmarks['h'] = pathlib.Path.home()

	def run(self):
		self.loop = urwid.MainLoop(self.screen, PALETTE, unhandled_input=self.keypress)
		self.loop.run()

	def keypress(self, key):
		if key == 'esc':
			self.screen.command_bar.reset()
			self.leader = ''
		elif self.leader == 's':
			if key == 'n':
				self.screen.left.sort('sort_by_name')
				self.screen.right.sort('sort_by_name')
			elif key == 'N':
				self.screen.left.sort('sort_by_name', reverse=True)
				self.screen.right.sort('sort_by_name', reverse=True)
			elif key == 'e':
				self.screen.left.sort('sort_by_extension')
				self.screen.right.sort('sort_by_extension')
			elif key == 'E':
				self.screen.left.sort('sort_by_extension', reverse=True)
				self.screen.right.sort('sort_by_extension', reverse=True)
			elif key == 'd':
				self.screen.left.sort('sort_by_date')
				self.screen.right.sort('sort_by_date')
			elif key == 'D':
				self.screen.left.sort('sort_by_date', reverse=True)
				self.screen.right.sort('sort_by_date', reverse=True)
			elif key == 's':
				self.screen.left.sort('sort_by_size')
				self.screen.right.sort('sort_by_size')
			elif key == 'S':
				self.screen.left.sort('sort_by_size', reverse=True)
				self.screen.right.sort('sort_by_size', reverse=True)

			self.screen.command_bar.reset()
			self.leader = ''
		elif self.leader == 'm':
			if key in BOOKMARK_KEYS:
				self.bookmarks[key] = self.screen.center.focus.cwd

			self.screen.command_bar.reset()
			self.leader = ''
		elif self.leader in ('`', "'"):
			if key in ('`', "'"):
				if self.screen.center.focus.old_cwd != self.screen.center.focus.cwd:
					self.screen.center.focus.chdir(self.screen.center.focus.old_cwd)
			elif key in BOOKMARK_KEYS:
				try:
					if self.bookmarks[key] != str(self.screen.center.focus.cwd):
						self.screen.center.focus.chdir(self.bookmarks[key])
				except KeyError:
					pass

			self.screen.command_bar.reset()
			self.leader = ''
		else:
			if key in ('q', 'Q', 'f10'):
				if self.printwd:
					try:
						with open(self.printwd, 'w') as fh:
							fh.write(str(self.screen.center.focus.cwd))
					except (FileNotFoundError, PermissionError):
						pass

				raise urwid.ExitMainLoop()
			elif key == 'tab':
				if self.screen.pile.focus_position == 0:
					self.screen.center.focus_position ^= 1
					self.screen.update_focus()
			elif key in ('f', '/'):
				self.screen.command_bar.filter()
			elif key == 'enter':
				self.screen.command_bar.execute()
			elif key == 'backspace':
				self.screen.left.toggle_hidden()
				self.screen.right.toggle_hidden()
			elif key == 's':
				self.leader = key
				self.screen.command_bar.set_leader(self.leader)
			elif key == 'm':
				self.leader = key
				self.screen.command_bar.set_leader(self.leader)
			elif key in ('`', "'"):
				self.leader = key
				self.screen.command_bar.set_leader(self.leader)
			elif key == 'meta i':
				cwd = self.screen.center.focus.cwd

				if (self.screen.left is not self.screen.center.focus) and (self.screen.left.cwd != cwd):
					self.screen.left.chdir(cwd)

				if (self.screen.right is not self.screen.center.focus) and (self.screen.right.cwd != cwd):
					self.screen.right.chdir(cwd)
			elif key == 'meta o':
				cwd = self.screen.center.focus.cwd.parent
				obj = self.screen.center.focus.get_focus()
				try:
					if stat.S_ISDIR(obj['stat'].st_mode):
						cwd = obj['file']
				except TypeError:
					pass

				if (self.screen.left is not self.screen.center.focus) and (self.screen.left.cwd != cwd):
					self.screen.left.chdir(cwd)

				if (self.screen.right is not self.screen.center.focus) and (self.screen.right.cwd != cwd):
					self.screen.right.chdir(cwd)
			elif key == 'ctrl r':
				self.reload()
			elif key == 'f7':
				self.screen.command_bar.mkdir()

	def reload(self):
		self.screen.left.reload()
		self.screen.right.reload()

	def error(self, e):
		self.screen.pile.contents[0] = (urwid.Overlay(DlgError(self, e), self.screen.center,
			'center', ('relative', 50),
			'middle', 'pack',
		), self.screen.pile.options())


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('-V', '--version', action='version', version=f'%(prog)s {__version__}')
	parser.add_argument('-P', '--printwd', help='Print last working directory to specified file', metavar='<file>')
	parser.add_argument('-d', '--debug', help='activate debug mode', action='store_true')
	args = parser.parse_args()

	if args.debug:
		set_debug_fh(open(pathlib.Path.home() / 'rnr.log', 'w', buffering=1))

	app = App(args.printwd)
	app.run()


if __name__ == '__main__':
	sys.exit(main())

