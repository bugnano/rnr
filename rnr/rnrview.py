#! /usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

import re
import fnmatch
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
from .dlg_search import DlgSearch
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

	def get_focus_offset(self, offset):
		position = self.focus
		pos = position - (position % self.line_width)
		pos += offset * self.line_width
		if pos < 0:
			return 0

		if pos >= self.file_size:
			pos = self.file_size - 1

		return pos


class HexFileWalker(urwid.ListWalker):
	def __init__(self, fh, file_size, data=None):
		self.fh = fh
		self.file_size = file_size
		self.data = data
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

		if self.data:
			data = self.data[pos:pos+self.line_width]
		else:
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

		if self.data:
			data = self.data[pos:pos+self.line_width]
		else:
			self.fh.seek(pos)
			data = self.fh.read(self.line_width)

		h = hex_string(data)
		w = urwid.Columns([(self.len_address, urwid.Text(('Lineno', self.fmt_address % (pos)), align='right')), (self.hex_width, urwid.Text(('Text', h))), urwid.Text([('Operator', '|'), ('String', masked_string(data)), ('Operator', '|')], wrap='clip')], dividechars=1)

		return (w, pos)

	def get_prev(self, position):
		pos = (position - (position % self.line_width)) - self.line_width
		if pos < 0:
			return (None, None)

		if self.data:
			data = self.data[pos:pos+self.line_width]
		else:
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

	def get_focus_offset(self, offset):
		position = self.focus
		pos = position - (position % self.line_width)
		pos += offset * self.line_width
		if pos < 0:
			return 0

		if pos >= self.file_size:
			pos = self.file_size - 1

		return pos


class TextFileWalker(urwid.ListWalker):
	def __init__(self, fh, file_size, data, code, filename, tabsize):
		self.fh = fh
		self.file_size = file_size
		self.data = data
		self.code = code.splitlines(keepends=True)
		self.filename = filename
		self.tabsize = tabsize
		self.lines = []
		self.focus = 0
		self.search_expression = None
		self.search_backwards = False

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


		line = self.highlight_line(pos, 'markselect')
		w = urwid.Columns([(self.digits, urwid.Text(('Lineno', f'{pos+1}'), align='right')), urwid.Text(line, wrap='clip')], dividechars=1)

		return (w, pos)

	def set_focus(self, position):
		self.focus = position
		self._modified()

	def get_next(self, position):
		pos = position + 1
		if pos >= self.len_lines:
			return (None, None)

		line = self.highlight_line(pos, 'selected')
		w = urwid.Columns([(self.digits, urwid.Text(('Lineno', f'{pos+1}'), align='right')), urwid.Text(line, wrap='clip')], dividechars=1)

		return (w, pos)

	def get_prev(self, position):
		pos = position - 1
		if pos < 0:
			return (None, None)

		line = self.highlight_line(pos, 'selected')
		w = urwid.Columns([(self.digits, urwid.Text(('Lineno', f'{pos+1}'), align='right')), urwid.Text(line, wrap='clip')], dividechars=1)

		return (w, pos)

	def positions(self, reverse=False):
		if reverse:
			return range(self.len_lines - 1, -1, -1)
		else:
			return range(self.len_lines)

	def change_size(self, size):
		pass

	def get_focus_offset(self, offset):
		pos = self.focus
		pos += offset
		if pos < 0:
			return 0

		if pos >= self.len_lines:
			pos = self.len_lines - 1

		return pos

	def start_search(self, expression, backwards):
		self.search_expression = expression
		self.search_backwards = backwards
		pos = None

		if pos is None:
			if backwards:
				slice = self.code[self.focus::-1]
			else:
				slice = self.code[self.focus:]

			for i, line in enumerate(slice):
				if self.search_expression.search(line):
					if backwards:
						pos = self.focus - i
					else:
						pos = self.focus + i

					break

		if pos is None:
			if backwards:
				slice = self.code[:self.focus:-1]
			else:
				slice = self.code[:self.focus]

			for i, line in enumerate(slice):
				if self.search_expression.search(line):
					if backwards:
						pos = (len(self.code) - 1) - i
					else:
						pos = i

					break

		if pos is None:
			self.search_expression = None

		return pos

	def highlight_line(self, pos, attr):
		if not self.search_expression:
			return self.lines[pos]

		line = self.lines[pos]

		len_part = 0
		part_offset = []
		for text_attr, text in line:
			len_part += len(text)
			part_offset.append(len_part)

		raw_line = ''.join([x[1] for x in line])
		new_line = []
		start = 0
		m = self.search_expression.search(raw_line, start)
		while m:
			match_start = m.start()
			prev_offset = 0
			for i, (text_attr, text) in enumerate(line):
				if part_offset[i] <= start:
					prev_offset = part_offset[i]
					continue

				if part_offset[i] < match_start:
					new_line.append((text_attr, text[-(part_offset[i] - start):]))
				else:
					new_line.append((text_attr, text[max(0, start - prev_offset):match_start-prev_offset]))
					break

				prev_offset = part_offset[i]

			new_line.append((attr, raw_line[match_start:m.end()]))

			start = m.end()
			m = self.search_expression.search(raw_line, start)

		prev_offset = 0
		for i, (text_attr, text) in enumerate(line):
			if part_offset[i] <= start:
				prev_offset = part_offset[i]
				continue

			new_line.append((text_attr, text[-(part_offset[i] - start):]))

			prev_offset = part_offset[i]

		new_line.append(('Text', ''))

		return new_line


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

		self.hex_walker = HexFileWalker(fh, len(data), data)

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

		self.file_size = len(data)

		lines_data = data.splitlines(keepends=True)
		len_line = 0
		self.line_offset = [len_line]
		for line in lines_data:
			len_line += len(line)
			self.line_offset.append(len_line)

		del self.line_offset[-1]

		w = TextFileWalker(fh, self.file_size, data, code, self.filename, self.tabsize)
		self.lines = w.lines
		self.len_lines = w.len_lines

		return w

	def use_hex_offset(self):
		if self.text_file:
			return self.body == self.hex_walker
		else:
			return True

	def line_from_offset(self, offset):
		low = 0;
		high = len(self.line_offset) - 1
		while low <= high:
			mid = (low + high) // 2

			if self.line_offset[mid] > offset:
				high = mid - 1
			elif self.line_offset[mid] < offset:
				low = mid + 1
			else:
				return mid

		return mid

	def render(self, size, *args, **kwargs):
		if size != self.old_size:
			self.old_size = size
			self.body.change_size(size)

		return super().render(size, *args, **kwargs)

	def keypress(self, size, key):
		if key in ('h', 'f4'):
			prev_focus = self.focus_position

			if self.body == self.walker:
				self.body = self.hex_walker
				if self.text_file:
					self.set_focus(self.line_offset[prev_focus])
				else:
					self.set_focus(prev_focus)
			else:
				self.body = self.walker
				if self.text_file:
					self.set_focus(self.line_from_offset(prev_focus))
				else:
					self.set_focus(prev_focus)

			if 'bottom'in self.ends_visible(size):
				self.set_focus(self.body.get_focus_offset(self.file_size))
				self.set_focus(self.body.get_focus_offset(min(-(size[1] - 1), -1)))

			self.set_focus_valign('top')

			self.body.change_size(size)

			self._invalidate()
		elif key in ('j', 'down'):
			self.set_focus(self.body.get_focus_offset(1))
			if 'bottom'in self.ends_visible(size):
				self.set_focus(self.body.get_focus_offset(self.file_size))
				self.set_focus(self.body.get_focus_offset(min(-(size[1] - 1), -1)))

			self.set_focus_valign('top')

			self._invalidate()
		elif key in ('k', 'up'):
			self.set_focus(self.body.get_focus_offset(-1))
			self.set_focus_valign('top')

			self._invalidate()
		elif key in ('g', 'home'):
			self.set_focus(0)
			self.set_focus_valign('top')

			self._invalidate()
		elif key in ('G', 'end'):
			self.set_focus(self.body.get_focus_offset(self.file_size))
			self.set_focus(self.body.get_focus_offset(min(-(size[1] - 1), -1)))
			self.set_focus_valign('top')

			self._invalidate()
		elif key in ('ctrl b', 'page up'):
			self.set_focus(self.body.get_focus_offset(min(-(size[1] - 1), -1)))
			self.set_focus_valign('top')

			self._invalidate()
		elif key in ('ctrl f', 'page down'):
			self.set_focus(self.body.get_focus_offset(max(size[1] - 1, 1)))
			if 'bottom'in self.ends_visible(size):
				self.set_focus(self.body.get_focus_offset(self.file_size))
				self.set_focus(self.body.get_focus_offset(min(-(size[1] - 1), -1)))

			self.set_focus_valign('top')

			self._invalidate()
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

	def on_search(self, text, mode, flags):
		self.close_dialog()

		if not text:
			return

		if self.list_box.use_hex_offset():
			expression = text
			pass
		else:
			if mode == 'wildcard':
				expression = fnmatch.translate(text)[:-2]
			elif mode == 'normal':
				expression = re.escape(text)
			else:
				expression = text

			if flags.words:
				expression = fr'\b{expression}\b'

			if flags.case:
				re_flags = 0
			else:
				re_flags = re.IGNORECASE

			expression = re.compile(expression, re_flags)

		pos = self.list_box.body.start_search(expression, flags.backwards)
		if pos is not None:
			self.list_box.set_focus(pos)
			self.list_box.set_focus_valign('top')
		else:
			self.error('Search string not found', title='Search', error=False)

	def close_dialog(self):
		self.pile.contents[1] = (self.center, self.pile.options())

		self.in_error = False

	def error(self, e, title='Error', error=True):
		self.pile.contents[1] = (urwid.Overlay(DlgError(self, e, title, error), self.center,
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
	elif key in ('f7', '/', '?'):
		if controller.screen.list_box.file_size == 0:
			return

		backwards = (key == '?')

		controller.screen.pile.contents[1] = (urwid.Overlay(DlgSearch(controller.screen, controller.screen.on_search, lambda x: controller.screen.close_dialog(), text_file=not controller.screen.list_box.use_hex_offset(), backwards=backwards), controller.screen.center,
			'center', 58,
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

