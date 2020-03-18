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

import panel
import cmdarea
import f_area

from debug_print import (debug_print, set_debug_fp)


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
		left = panel.Panel()
		right = panel.Panel()
		self.center = urwid.Columns([left, right])
		self.command_area = cmdarea.CmdArea()
		bottom = f_area.FArea()
		self.pile = urwid.Pile([self.center, (1, self.command_area), (1, bottom)])
		self.pile.focus_position = 0

		super().__init__(self.pile)


class App(object):
	def __init__(self, printwd):
		self.printwd = printwd

		self.screen = Screen()
		self.center = self.screen.center
		self.command_area = self.screen.command_area.edit

		urwid.connect_signal(self.command_area, 'change', self.on_change_command_area)

	def run(self):
		loop = urwid.MainLoop(self.screen, palette, unhandled_input=self.keypress)
		loop.run()

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
			if self.screen.pile.focus_position == 0:
				self.center.focus_position ^= 1
		elif key in ('f', '/'):
			self.command_area.set_caption('/')
			self.screen.pile.focus_position = 1
		elif key == 'esc':
			self.screen.pile.focus_position = 0
			self.command_area.set_caption('')
			self.command_area.set_edit_text('')

	def on_change_command_area(self, edit, new_edit_text):
		self.center.focus.filter(new_edit_text)


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('-V', '--version', action='version', version=f'%(prog)s {__version__}')
	parser.add_argument('-P', '--printwd', help='Print last working directory to specified file', metavar='<file>')
	parser.add_argument('-d', '--debug', help='activate debug mode', action='store_true')
	args = parser.parse_args()

	if args.debug:
		set_debug_fp(open('rrr.log', 'w', buffering=1))

	app = App(args.printwd)
	app.run()


if __name__ == '__main__':
	sys.exit(main())

