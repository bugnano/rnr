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

import menu
import panel
import cmdarea
import f_area


__version__ = '0.0.1'


COLOUR_PANEL_BG = 'dark blue'
COLOUR_SELECT_BG = 'dark cyan'
COLOUR_MENU_BG = 'dark cyan'

palette = [
	('banner', 'black', 'light gray'),
	('streak', 'black', 'dark red'),
	('bg', 'light gray', COLOUR_PANEL_BG),
	('dir', 'white', COLOUR_PANEL_BG),
	('focus', 'black', COLOUR_SELECT_BG),
	('menu', 'black', COLOUR_MENU_BG),
	('normal', 'default', 'default'),
	('white_on_black', 'white', 'black'),
]


class Screen(urwid.WidgetWrap):
	def __init__(self):
		top = menu.Menu()
		left = panel.Panel()
		right = panel.Panel()
		self.center = urwid.Columns([left, right])
		command_area = cmdarea.CmdArea()
		bottom = f_area.FArea()
		w = urwid.Pile([(1, top), self.center, (1, command_area), (1, bottom)])

		super().__init__(w)


class App(object):
	def __init__(self, printwd):
		self.printwd = printwd
		self.screen = Screen()
		self.center = self.screen.center

	def keypress(self, key):
		if key in ('q', 'Q', 'f10'):
			if self.printwd:
				try:
					with open(self.printwd, 'w') as fp:
						fp.write(str(self.center.focus.cwd))
				except (FileNotFoundError, PermissionError):
					pass

			raise urwid.ExitMainLoop()
		elif key == 'tab':
			self.center.focus_position ^= 1

	def run(self):
		loop = urwid.MainLoop(self.screen, palette, unhandled_input=self.keypress)
		loop.run()


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('-V', '--version', action='version', version=f'%(prog)s {__version__}')
	parser.add_argument('-P', '--printwd', help='Print last working directory to specified file', metavar='<file>')
	args = parser.parse_args()

	app = App(args.printwd)
	app.run()


if __name__ == '__main__':
	sys.exit(main())

