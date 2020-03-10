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

import menu
import panel
import cmdarea
import f_area


palette = [
	('banner', 'black', 'light gray'),
	('streak', 'black', 'dark red'),
	('bg', 'light gray', 'dark blue'),
	('menu', 'black', 'dark cyan'),
	('normal', 'default', 'default'),
	('white_on_black', 'white', 'black'),
]


def exit_on_q(key):
    if key in ('q', 'Q'):
        raise urwid.ExitMainLoop()


class Screen(urwid.WidgetWrap):
	def __init__(self):
		top = menu.Menu()
		left = panel.Panel('Left')
		right = panel.Panel('Right')
		center = urwid.Columns([left, right])
		command_area = cmdarea.CmdArea()
		bottom = f_area.FArea()
		w = urwid.Pile([(1, top), center, (1, command_area), (1, bottom)])

		urwid.WidgetWrap.__init__(self, w)


def main():
	screen = Screen()
	loop = urwid.MainLoop(screen, palette, unhandled_input=exit_on_q)
	loop.run()


if __name__ == '__main__':
	sys.exit(main())

