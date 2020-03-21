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

import urwid

from . import panel
from . import cmdarea
from . import f_area

from .debug_print import (debug_print, set_debug_fp)


__version__ = '0.0.1'

COLOUR_PANEL_BG = 'dark blue'
COLOUR_SELECT_BG = 'dark cyan'
COLOUR_MENU_BG = 'dark cyan'

palette = [
	('banner', 'black', 'light gray'),
	('streak', 'black', 'dark red'),
	('bg', 'light gray', COLOUR_PANEL_BG),
	('dir', 'white', COLOUR_PANEL_BG),
	('executable', 'light green', COLOUR_PANEL_BG),
	('focus', 'black', COLOUR_SELECT_BG),
	('menu', 'black', COLOUR_MENU_BG),
	('normal', 'default', 'default'),
	('white_on_black', 'white', 'black'),
]


class Screen(urwid.WidgetWrap):
	def __init__(self):
		self.left = panel.Panel()
		self.right = panel.Panel()
		self.center = urwid.Columns([self.left, self.right])
		self.command_area = cmdarea.CmdArea(self)
		bottom = f_area.FArea()
		self.pile = urwid.Pile([self.center, (1, self.command_area), (1, bottom)])
		self.pile.focus_position = 0

		super().__init__(self.pile)


class App(object):
	def __init__(self, printwd):
		self.printwd = printwd

		self.screen = Screen()
		self.leader = ''

	def run(self):
		loop = urwid.MainLoop(self.screen, palette, unhandled_input=self.keypress)
		loop.run()

	def keypress(self, key):
		if key == 'esc':
			self.screen.command_area.reset()
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

			self.screen.command_area.reset()
			self.leader = ''
		else:
			if key in ('q', 'Q', 'f10'):
				if self.printwd:
					try:
						with open(self.printwd, 'w') as fp:
							fp.write(str(self.screen.center.focus.cwd))
					except (FileNotFoundError, PermissionError):
						pass

				raise urwid.ExitMainLoop()
			elif key == 'tab':
				if self.screen.pile.focus_position == 0:
					self.screen.center.focus_position ^= 1
			elif key in ('f', '/'):
				self.screen.command_area.filter()
			elif key == 'enter':
				self.screen.command_area.execute()
			elif key == 'backspace':
				self.screen.left.toggle_hidden()
				self.screen.right.toggle_hidden()
			elif key == 's':
				self.leader = 's'
				self.screen.command_area.set_leader(self.leader)
			elif key == 'meta i':
				cwd = self.screen.center.focus.cwd

				if (self.screen.left is not self.screen.center.focus) and (self.screen.left.cwd != cwd):
					self.screen.left.chdir(cwd)

				if (self.screen.right is not self.screen.center.focus) and (self.screen.right.cwd != cwd):
					self.screen.right.chdir(cwd)


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('-V', '--version', action='version', version=f'%(prog)s {__version__}')
	parser.add_argument('-P', '--printwd', help='Print last working directory to specified file', metavar='<file>')
	parser.add_argument('-d', '--debug', help='activate debug mode', action='store_true')
	args = parser.parse_args()

	if args.debug:
		set_debug_fp(open('rnr.log', 'w', buffering=1))

	app = App(args.printwd)
	app.run()


if __name__ == '__main__':
	sys.exit(main())

