#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

import argparse

from pathlib import Path

import pygments
import pygments.lexers
import pygments.util

import urwid

from pygments.token import Token

from . import __version__

from .import_config import *
from .__main__ import PALETTE
from .debug_print import (debug_print, debug_pprint, set_debug_fh)


MAX_TEXT_FILE_SIZE = 2097152
NON_PRINTABLE_MASK = '·'


StyleFromToken = {
	Token.Keyword.Namespace: 'Namespace',
	Token.Keyword: 'Keyword',
	Token.Name.Class: 'Class',
	Token.Name.Function: 'Class',
	Token.Name.Tag: 'Keyword',
	Token.Name.Attribute: 'Class',
	Token.Name.Builtin.Pseudo: 'Keyword',
	Token.Literal.String: 'String',
	Token.Literal: 'Literal',
	Token.Operator: 'Operator',
	Token.Punctuation: 'Operator',
	Token.Comment.Preproc: 'Namespace',
	Token.Comment: 'Comment',
}


class Screen(urwid.WidgetWrap):
	def __init__(self, controller, filename, file_size, tabsize):
		self.controller = controller
		self.filename = filename
		self.file_size = file_size
		self.tabsize = tabsize

		text_file = True
		if file_size > MAX_TEXT_FILE_SIZE:
			text_file = False
		else:
			with open(filename, 'rb') as fh:
				data = fh.read(131072)

			if b'\0' in data:
				text_file = False

			if text_file:
				try:
					data.decode(sys.getdefaultencoding())
				except UnicodeDecodeError:
					text_file = False

		self.text_file = text_file
		if text_file:
			walker = self.read_text_file()
		else:
			walker = self.read_binary_file()

		w = urwid.ListBox(walker)
		w = urwid.AttrMap(w, 'Text')

		super().__init__(w)

	def read_text_file(self):
		with open(self.filename) as fh:
			code = fh.read()

		lines = []

		try:
			lexer = pygments.lexers.get_lexer_for_filename(self.filename, stripnl=False, tabsize=self.tabsize)
		except pygments.util.ClassNotFound:
			try:
				lexer = pygments.lexers.guess_lexer(code, stripnl=False, tabsize=self.tabsize)
			except pygments.util.ClassNotFound:
				lexer = pygments.lexers.special.TextLexer(stripnl=False, tabsize=self.tabsize)

		line = []
		result = pygments.lex(code, lexer)
		for tokentype, value in result:
			for k, v in StyleFromToken.items():
				if tokentype in k:
					style = v
					break
			else:
				style = 'Text'

			for l in value.splitlines(keepends=True):
				line.append((style, l.rstrip('\n')))
				if '\n' in l:
					lines.append(line)
					line = []

		digits = len(str(len(lines)))
		lst = [urwid.Columns([(digits, urwid.Text(('Lineno', f'{i+1}'), align='right')), urwid.Text(x, wrap='clip')], dividechars=1) for i, x in enumerate(lines)]
		w = urwid.SimpleListWalker(lst)

		return w

	def read_binary_file(self):
		with open(self.filename, 'rb') as fh:
			data = fh.read(MAX_TEXT_FILE_SIZE)

		chars = []
		for x in data:
			if (x < 0x20) or (x >= 0x7F):
				chars.append(NON_PRINTABLE_MASK)
			else:
				chars.append(chr(x))

		str_data = ''.join(chars)

		lst = [urwid.Text(str_data, wrap='any')]
		w = urwid.SimpleListWalker(lst)

		return w


class App(object):
	def __init__(self, filename, file_size, monochrome, tabsize):
		self.filename = filename
		self.monochrome = monochrome
		self.tabsize = tabsize

		self.screen = Screen(self, filename, file_size, tabsize)

	def run(self):
		self.loop = urwid.MainLoop(self.screen, PALETTE, unhandled_input=self.keypress)

		if self.monochrome:
			self.loop.screen.set_terminal_properties(colors=1)

		self.loop.run()

	def keypress(self, key):
		if key in ('q', 'Q', 'f3', 'f10'):
			raise urwid.ExitMainLoop()


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('FILE', help='the file to view')
	parser.add_argument('-V', '--version', action='version', version=f'%(prog)s {__version__}')
	parser.add_argument('-b', '--nocolor', help='Requests to run in black and white', action='store_true', dest='monochrome')
	parser.add_argument('-t', '--tabsize', help='set tab size (default: %(default)d)', type=int, default=TAB_SIZE)
	parser.add_argument('-d', '--debug', help='activate debug mode', action='store_true')
	args = parser.parse_args()

	filename = args.FILE

	try:
		file_size = os.stat(filename).st_size
	except OSError as e:
		print(e, file=sys.stderr)
		return 1

	if args.debug:
		set_debug_fh(open(Path.home() / 'rnr.log', 'w', buffering=1))

	app = App(filename, file_size, args.monochrome, args.tabsize)
	app.run()


if __name__ == '__main__':
	sys.exit(main())

