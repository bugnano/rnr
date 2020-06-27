#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

import re
import argparse
import functools

from pathlib import Path

import pygments
import pygments.lexers
import pygments.util

import urwid

from pygments.token import Token

from . import __version__

from .import_config import *
from .__main__ import PALETTE
from .buttonbar import ButtonBar
from .dlg_goto import DlgGoto
from .dlg_error import DlgError
from .utils import TildeLayout
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


ReNewLine = re.compile(r'''(?:\r\n|[\r\n])$''')


def masked_string(b):
	chars = []
	for x in b:
		if (x < 0x20) or (x >= 0x7F):
			chars.append(NON_PRINTABLE_MASK)
		else:
			chars.append(chr(x))

	return ''.join(chars)


def hex_string(b):
	chars = []
	for i, e in enumerate(b):
		if (i % 4) == 0:
			fmt = ' %02X '
		else:
			fmt = '%02X '

		chars.append(fmt % e)

	return ''.join(chars)


class TopBar(urwid.WidgetWrap):
	def __init__(self, filename):
		w = urwid.Text(os.path.abspath(filename), layout=TildeLayout)
		w = urwid.AttrMap(w, 'selected')
		super().__init__(w)


class BinaryFileWalker(urwid.ListWalker):
	def __init__(self, fh, file_size):
		self.fh = fh
		self.file_size = file_size
		self.focus = 0

		len_address = len(hex(file_size - 1).split('x')[1])
		len_address += len_address % 2
		self.len_address = max(len_address, 8)
		self.fmt_address = f'%0{self.len_address}X'

		self.line_width = 64

	def get_focus(self):
		position = self.focus
		pos = position - (position % self.line_width)
		if (pos < 0) or (pos >= self.file_size):
			return (None, None)

		self.fh.seek(pos)
		w = urwid.Columns([(self.len_address, urwid.Text(('Lineno', self.fmt_address % (pos)), align='right')), urwid.Text(masked_string(self.fh.read(self.line_width)), wrap='clip')], dividechars=1)

		return (w, pos)

	def set_focus(self, position):
		self.focus = position
		self._modified()

	def get_next(self, position):
		pos = (position - (position % self.line_width)) + self.line_width
		if pos >= self.file_size:
			return (None, None)

		self.fh.seek(pos)
		w = urwid.Columns([(self.len_address, urwid.Text(('Lineno', self.fmt_address % (pos)), align='right')), urwid.Text(masked_string(self.fh.read(self.line_width)), wrap='clip')], dividechars=1)

		return (w, pos)

	def get_prev(self, position):
		pos = (position - (position % self.line_width)) - self.line_width
		if pos < 0:
			return (None, None)

		self.fh.seek(pos)
		w = urwid.Columns([(self.len_address, urwid.Text(('Lineno', self.fmt_address % (pos)), align='right')), urwid.Text(masked_string(self.fh.read(self.line_width)), wrap='clip')], dividechars=1)

		return (w, pos)

	def positions(self, reverse=False):
		if reverse:
			return range(self.file_size - 1, -1, -1)
		else:
			return range(self.file_size)

	def change_size(self, size):
		width = size[0]
		old_width = self.line_width

		width -= self.len_address + 1
		line_width = max(width, 16)
		self.line_width = line_width - (line_width % 16)

		if self.line_width != old_width:
			self._modified()


class HexFileWalker(urwid.ListWalker):
	def __init__(self, fh, file_size):
		self.fh = fh
		self.file_size = file_size
		self.focus = 0

		len_address = len(hex(file_size - 1).split('x')[1])
		len_address += len_address % 2
		self.len_address = max(len_address, 8)
		self.fmt_address = f'%0{self.len_address}X'

		self.line_width = 16
		self.hex_width = int(self.line_width / 4) * 13

	def get_focus(self):
		position = self.focus
		pos = position - (position % self.line_width)
		if (pos < 0) or (pos >= self.file_size):
			return (None, None)

		self.fh.seek(pos)
		data = self.fh.read(self.line_width)
		h = hex_string(data)
		w = urwid.Columns([(self.len_address, urwid.Text(('Lineno', self.fmt_address % (pos)), align='right')), (self.hex_width, urwid.Text(('Text', h))), urwid.Text([('Operator', '|'), ('String', masked_string(data)), ('Operator', '|')], wrap='clip')], dividechars=1)

		return (w, pos)

	def set_focus(self, position):
		self.focus = position
		self._modified()

	def get_next(self, position):
		pos = (position - (position % self.line_width)) + self.line_width
		if pos >= self.file_size:
			return (None, None)

		self.fh.seek(pos)
		data = self.fh.read(self.line_width)
		h = hex_string(data)
		w = urwid.Columns([(self.len_address, urwid.Text(('Lineno', self.fmt_address % (pos)), align='right')), (self.hex_width, urwid.Text(('Text', h))), urwid.Text([('Operator', '|'), ('String', masked_string(data)), ('Operator', '|')], wrap='clip')], dividechars=1)

		return (w, pos)

	def get_prev(self, position):
		pos = (position - (position % self.line_width)) - self.line_width
		if pos < 0:
			return (None, None)

		self.fh.seek(pos)
		data = self.fh.read(self.line_width)
		h = hex_string(data)
		w = urwid.Columns([(self.len_address, urwid.Text(('Lineno', self.fmt_address % (pos)), align='right')), (self.hex_width, urwid.Text(('Text', h))), urwid.Text([('Operator', '|'), ('String', masked_string(data)), ('Operator', '|')], wrap='clip')], dividechars=1)

		return (w, pos)

	def positions(self, reverse=False):
		if reverse:
			return range(self.file_size - 1, -1, -1)
		else:
			return range(self.file_size)

	def change_size(self, size):
		width = size[0]
		old_width = self.line_width

		width -= self.len_address + 4
		num_dwords = max(int(width / 17), 1)
		self.line_width = num_dwords * 4
		self.hex_width = int(self.line_width / 4) * 13

		if self.line_width != old_width:
			self._modified()


class TextFileWalker(urwid.ListWalker):
	def __init__(self, fh, file_size, data, code, filename, tabsize):
		self.fh = fh
		self.file_size = file_size
		self.data = data
		self.code = code
		self.filename = filename
		self.tabsize = tabsize
		self.lines = []
		self.focus = 0

		try:
			name = self.filename.name
			if name == name.upper():
				filename = self.filename.parent / self.filename.name.lower()
			else:
				filename = self.filename

			lexer = pygments.lexers.get_lexer_for_filename(filename, stripnl=False, tabsize=self.tabsize)
		except pygments.util.ClassNotFound:
			try:
				lexer = pygments.lexers.guess_lexer(code, stripnl=False, tabsize=self.tabsize)
			except pygments.util.ClassNotFound:
				lexer = pygments.lexers.special.TextLexer(stripnl=False, tabsize=self.tabsize)

		del self.lines[:]
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
				if ReNewLine.search(l):
					line.append((style, ReNewLine.sub('', l)))
					self.lines.append(line)
					line = []
				else:
					line.append((style, l))

		self.len_lines = len(self.lines)
		self.digits = len(str(self.len_lines))

	def get_focus(self):
		pos = self.focus
		if (pos < 0) or (pos >= self.len_lines):
			return (None, None)

		w = urwid.Columns([(self.digits, urwid.Text(('Lineno', f'{pos+1}'), align='right')), urwid.Text(self.lines[pos], wrap='clip')], dividechars=1)

		return (w, pos)

	def set_focus(self, position):
		self.focus = position
		self._modified()

	def get_next(self, position):
		pos = position + 1
		if pos >= self.len_lines:
			return (None, None)

		w = urwid.Columns([(self.digits, urwid.Text(('Lineno', f'{pos+1}'), align='right')), urwid.Text(self.lines[pos], wrap='clip')], dividechars=1)

		return (w, pos)

	def get_prev(self, position):
		pos = position - 1
		if pos < 0:
			return (None, None)

		w = urwid.Columns([(self.digits, urwid.Text(('Lineno', f'{pos+1}'), align='right')), urwid.Text(self.lines[pos], wrap='clip')], dividechars=1)

		return (w, pos)

	def positions(self, reverse=False):
		if reverse:
			return range(self.len_lines - 1, -1, -1)
		else:
			return range(self.len_lines)

	def change_size(self, size):
		pass


class FileViewListBox(urwid.ListBox):
	def __init__(self, controller, filename, file_size, tabsize):
		self.controller = controller
		self.filename = filename
		self.file_size = file_size
		self.tabsize = tabsize

		fh = open(filename, 'rb')

		text_file = True
		if file_size > MAX_TEXT_FILE_SIZE:
			text_file = False
		else:
			data = fh.read(131072)

			if b'\0' in data:
				text_file = False

			if text_file:
				try:
					encoding = sys.getdefaultencoding()
					data.decode(encoding)
				except UnicodeDecodeError:
					if encoding == 'windows-1252':
						text_file = False
					else:
						try:
							encoding = 'windows-1252'
							data.decode(encoding)
						except UnicodeDecodeError:
							text_file = False

		self.text_file = text_file
		if text_file:
			self.walker = self.read_text_file(fh, encoding)
		else:
			self.walker = BinaryFileWalker(fh, self.file_size)

		self.hex_walker = HexFileWalker(fh, self.file_size)

		self.old_size = None

		super().__init__(self.walker)

	def read_text_file(self, fh, encoding):
		fh.seek(0)
		data = fh.read(MAX_TEXT_FILE_SIZE)

		try:
			code = data.decode(encoding)
		except UnicodeDecodeError:
			if encoding == 'windows-1252':
				return BinaryFileWalker(fh, self.file_size)
			else:
				try:
					encoding = 'windows-1252'
					code = data.decode(encoding)
				except UnicodeDecodeError:
					self.text_file = False
					return BinaryFileWalker(fh, self.file_size)

		w = TextFileWalker(fh, self.file_size, data, code, self.filename, self.tabsize)
		self.lines = w.lines
		self.len_lines = w.len_lines

		return w

	def use_hex_offset(self):
		if self.text_file:
			return self.body == self.hex_walker
		else:
			return True

	def render(self, size, *args, **kwargs):
		if size != self.old_size:
			self.old_size = size
			self.body.change_size(size)

		return super().render(size, *args, **kwargs)

	def keypress(self, size, key):
		if key in ('h', 'f4'):
			if self.body == self.walker:
				self.body = self.hex_walker
			else:
				self.body = self.walker

			self.body.change_size(size)

			self._invalidate()
		elif key in ('j', 'down'):
			retval = super().keypress(size, 'down')
			self._invalidate()

			return retval
		elif key in ('k', 'up'):
			retval = super().keypress(size, 'up')
			self._invalidate()

			return retval
		elif key in ('g', 'home'):
			retval = super().keypress(size, 'home')
			self._invalidate()

			return retval
		elif key in ('G', 'end'):
			retval = super().keypress(size, 'end')
			self._invalidate()

			return retval
		elif key in ('ctrl b', 'page up'):
			retval = super().keypress(size, 'page up')
			self._invalidate()

			return retval
		elif key in ('ctrl f', 'page down'):
			retval = super().keypress(size, 'page down')
			self._invalidate()

			return retval
		else:
			return super().keypress(size, key)


class Screen(urwid.WidgetWrap):
	def __init__(self, controller, filename, file_size, tabsize):
		self.controller = controller
		self.filename = filename
		self.file_size = file_size
		self.tabsize = tabsize

		self.in_error = False

		top = TopBar(filename)

		self.list_box = FileViewListBox(controller, filename, file_size, tabsize)
		self.center = urwid.AttrMap(self.list_box, 'Text')

		pile_widgets = [(1, urwid.Filler(top)), self.center]

		if SHOW_BUTTONBAR:
			labels = [
				' ', #'Help',
				' ', #'UnWrap',
				'Quit',
				'Hex', #'Ascii',
				'Goto',
				' ',
				'Search',
				' ', #'Raw',
				' ', #'Format',
				'Quit',
			]
			bottom = ButtonBar(labels)
			w = urwid.Filler(bottom)
			pile_widgets.append((1, w))

		self.pile = urwid.Pile(pile_widgets)

		super().__init__(self.pile)

	def on_goto(self, pos):
		self.close_dialog()

		try:
			if self.list_box.use_hex_offset():
				pos = int(pos, 16)
			else:
				pos = int(pos, 10) - 1
		except ValueError:
			self.error(f'Invalid number: {pos}')
			return

		if self.list_box.use_hex_offset():
			if pos >= self.list_box.file_size:
				pos = self.list_box.file_size - 1
		else:
			if pos >= self.list_box.len_lines:
				pos = self.list_box.len_lines - 1

		if pos < 0:
			pos = 0

		self.list_box.set_focus(pos)
		self.list_box.set_focus_valign('top')

	def close_dialog(self):
		self.pile.contents[1] = (self.center, self.pile.options())

		self.in_error = False

	def error(self, e):
		self.pile.contents[1] = (urwid.Overlay(DlgError(self, e), self.center,
			'center', len(e) + 6,
			'middle', 'pack',
		), self.pile.options())

		self.in_error = True


class App(object):
	def __init__(self, filename, file_size, monochrome, tabsize):
		self.filename = filename
		self.monochrome = monochrome
		self.tabsize = tabsize

		self.screen = Screen(self, filename, file_size, tabsize)

	def run(self):
		self.loop = urwid.MainLoop(self.screen, PALETTE, unhandled_input=functools.partial(keypress, self))

		if self.monochrome:
			self.loop.screen.set_terminal_properties(colors=1)

		self.loop.run()


def keypress(controller, key):
	if controller.screen.in_error:
		controller.screen.close_dialog()
		return

	if key in ('q', 'Q', 'v', 'f3', 'f10'):
		try:
			controller.close_viewer()
		except AttributeError:
			raise urwid.ExitMainLoop()
	elif key == 'f5':
		if controller.screen.list_box.file_size == 0:
			return

		if controller.screen.list_box.use_hex_offset():
			label = 'Hex offset: '
		else:
			label = 'Line number: '

		controller.screen.pile.contents[1] = (urwid.Overlay(DlgGoto(controller.screen, controller.screen.on_goto, lambda x: controller.screen.close_dialog(), label=label), controller.screen.center,
			'center', 30,
			'middle', 'pack',
		), controller.screen.pile.options())


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('FILE', help='the file to view')
	parser.add_argument('-V', '--version', action='version', version=f'%(prog)s {__version__}')
	parser.add_argument('-b', '--nocolor', help='Requests to run in black and white', action='store_true', dest='monochrome')
	parser.add_argument('-t', '--tabsize', help='set tab size (default: %(default)d)', type=int, default=TAB_SIZE)
	parser.add_argument('-d', '--debug', help='activate debug mode', action='store_true')
	args = parser.parse_args()

	filename = Path(args.FILE)

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

