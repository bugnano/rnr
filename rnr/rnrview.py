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
from .palette import PALETTE
from .panel import (get_file_list, sort_by_name)
from .buttonbar import ButtonBar
from .dlg_goto import DlgGoto
from .dlg_error import DlgError
from .dlg_search import DlgSearch
from .utils import (TildeLayout, format_date)
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


Labels = [
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


def masked_string(b, attr_normal, attr_highlight):
	chars = []
	for highlight, data in b:
		tmp = []
		for x in data:
			if (x < 0x20) or (x >= 0x7F):
				tmp.append(NON_PRINTABLE_MASK)
			else:
				tmp.append(chr(x))

		if highlight:
			chars.append((attr_highlight, ''.join(tmp)))
		else:
			chars.append((attr_normal, ''.join(tmp)))

	return chars


def hex_string(b, attr_normal, attr_highlight):
	chars = []
	i = 0

	for highlight, data in b:
		if highlight:
			for e in data:
				if (i % 4) == 0:
					chars.append((attr_normal, ' '))

				chars.append((attr_highlight, '%02X' % e))
				chars.append((attr_normal, ' '))

				i += 1
		else:
			tmp = []
			for e in data:
				if (i % 4) == 0:
					fmt = ' %02X '
				else:
					fmt = '%02X '

				tmp.append(fmt % e)

				i += 1

			chars.append((attr_normal, ''.join(tmp)))

	return chars


class TopBar(urwid.WidgetWrap):
	def __init__(self, filename):
		w = urwid.Text(os.path.abspath(filename), layout=TildeLayout)
		w = urwid.AttrMap(w, 'selected')
		super().__init__(w)


class BinaryFileWalker(urwid.ListWalker):
	def __init__(self, fh, file_size, data=None):
		self.fh = fh
		self.file_size = file_size
		self.data = data
		self.focus = 0
		self.search_expression = None
		self.search_backwards = False
		self.highligh_buffer = None
		self.highligh_buffer_pos = None

		len_address = len(hex(file_size - 1).split('x')[1])
		len_address += len_address % 2
		self.len_address = max(len_address, 8)
		self.fmt_address = f'%0{self.len_address}X'

	def set_focus(self, position):
		self.focus = position
		self._modified()

	def positions(self, reverse=False):
		if reverse:
			return range(self.file_size - 1, -1, -1)
		else:
			return range(self.file_size)

	def get_focus_offset(self, offset):
		position = self.focus
		pos = position - (position % self.line_width)
		pos += offset * self.line_width
		if pos < 0:
			return 0

		if pos >= self.file_size:
			pos = self.file_size - 1

		return pos

	def start_search(self, expression, backwards):
		self.search_expression = expression
		self.search_backwards = backwards
		position = self.focus
		position = position - (position % self.line_width)
		pos = self.search_from_pos(position, backwards)

		if pos is None:
			self.search_expression = None

		self._modified()

		return pos

	def stop_search(self):
		self.search_expression = None
		self._modified()

	def search_next(self):
		if self.search_backwards:
			position = self.focus
			position = position - (position % self.line_width)
			pos = position - 1
			if pos < 0:
				pos = self.file_size - 1
		else:
			position = self.focus
			position = position - (position % self.line_width)
			pos = position + self.line_width
			if pos >= self.file_size:
				pos = 0

		pos = self.search_from_pos(pos, self.search_backwards)

		self._modified()

		return pos

	def search_prev(self):
		if self.search_backwards:
			position = self.focus
			position = position - (position % self.line_width)
			pos = position + self.line_width
			if pos >= self.file_size:
				pos = 0
		else:
			position = self.focus
			position = position - (position % self.line_width)
			pos = position - 1
			if pos < 0:
				pos = self.file_size - 1

		pos = self.search_from_pos(pos, not self.search_backwards)

		self._modified()

		return pos

	def search_from_pos(self, pos, backwards):
		starting_pos = pos
		new_pos = None

		block_size = 131072

		if new_pos is None:
			if backwards:
				if self.data:
					data = self.data[pos:pos+len(self.search_expression)]
				else:
					self.fh.seek(pos)
					data = self.fh.read(len(self.search_expression))

				while pos >= 0:
					old_data = data[:len(self.search_expression)]
					if self.data:
						data = self.data[max(0, pos - block_size):pos] + old_data
					else:
						self.fh.seek(max(0, pos - block_size))
						data = self.fh.read(min(pos, block_size)) + old_data

					i = data.rfind(self.search_expression)
					if i >= 0:
						new_pos = ((pos + len(old_data)) - len(data)) + i
						break

					pos -= block_size
			else:
				data = b''
				while pos < self.file_size:
					old_data = data[-len(self.search_expression):]
					if self.data:
						data = old_data + self.data[pos:pos+block_size]
					else:
						self.fh.seek(pos)
						data = old_data + self.fh.read(block_size)

					i = data.find(self.search_expression)
					if i >= 0:
						new_pos = (pos - len(old_data)) + i
						break

					pos += block_size

		if new_pos is None:
			data = b''
			if backwards:
				pos = self.file_size - 1
				while pos >= starting_pos:
					old_data = data[:len(self.search_expression)]
					if self.data:
						data = self.data[max(0, pos - block_size):pos] + old_data
					else:
						self.fh.seek(max(0, pos - block_size))
						data = self.fh.read(min(pos, block_size)) + old_data

					i = data.rfind(self.search_expression)
					if i >= 0:
						new_pos = ((pos + len(old_data)) - len(data)) + i
						break

					pos -= block_size

			else:
				pos = 0
				while pos < starting_pos:
					old_data = data[-len(self.search_expression):]
					if self.data:
						data = old_data + self.data[pos:pos+block_size]
					else:
						self.fh.seek(pos)
						data = old_data + self.fh.read(block_size)

					i = data.find(self.search_expression)
					if i >= 0:
						new_pos = (pos - len(old_data)) + i
						break

					pos += block_size

		return new_pos

	def highlight_line(self, pos):
		if self.search_expression:
			len_expression = len(self.search_expression)
		else:
			len_expression = 0

		starting_pos = max(pos - len_expression, 0)
		end_pos = min(pos + self.line_width, self.file_size)
		block_size = 131072

		if (self.highligh_buffer_pos is None) or (self.highligh_buffer_pos > starting_pos) or ((len(self.highligh_buffer) - (pos - self.highligh_buffer_pos)) < max(self.line_width, len_expression)):
			if self.data:
				self.highligh_buffer = self.data[starting_pos:starting_pos+block_size]
			else:
				self.fh.seek(starting_pos)
				self.highligh_buffer = self.fh.read(block_size)

			self.highligh_buffer_pos = starting_pos

		ranges_to_highlight = []

		if self.search_expression:
			search_pos = starting_pos
			while search_pos < end_pos:
				i = self.highligh_buffer.find(self.search_expression, search_pos - self.highligh_buffer_pos)
				if (i >= 0) and (i < (end_pos - self.highligh_buffer_pos)):
					ranges_to_highlight.append([max(self.highligh_buffer_pos + i, pos), min(self.highligh_buffer_pos + i + len_expression, end_pos)])
				else:
					break

				search_pos = self.highligh_buffer_pos + i + len_expression

		line = []
		if ranges_to_highlight:
			for i, e in enumerate(ranges_to_highlight):
				if i == 0:
					line.append([False, self.highligh_buffer[pos-self.highligh_buffer_pos:e[0]-self.highligh_buffer_pos]])
				else:
					line.append([False, self.highligh_buffer[ranges_to_highlight[i-1][1]-self.highligh_buffer_pos:e[0]-self.highligh_buffer_pos]])

				line.append([True, self.highligh_buffer[e[0]-self.highligh_buffer_pos:e[1]-self.highligh_buffer_pos]])

			chunk_pos = ranges_to_highlight[-1][1] - self.highligh_buffer_pos
			used_line = sum([len(x[1]) for x in line])
			line.append([False, self.highligh_buffer[chunk_pos:chunk_pos+(self.line_width-used_line)]])
		else:
			chunk_pos = pos-self.highligh_buffer_pos
			line.append([False, self.highligh_buffer[chunk_pos:chunk_pos+self.line_width]])

		return [x for x in line if x[1]]


class DumpFileWalker(BinaryFileWalker):
	def __init__(self, fh, file_size, data=None):
		self.line_width = 64
		super().__init__(fh, file_size, data)

	def get_focus(self):
		position = self.focus
		pos = position - (position % self.line_width)
		if (pos < 0) or (pos >= self.file_size):
			return (None, None)

		line = self.highlight_line(pos)
		w = urwid.Columns([(self.len_address, urwid.Text(('Lineno', self.fmt_address % (pos)), align='right')), urwid.Text(masked_string(line, 'Text', 'markselect'), wrap='clip')], dividechars=1)

		return (w, pos)

	def get_next(self, position):
		pos = (position - (position % self.line_width)) + self.line_width
		if pos >= self.file_size:
			return (None, None)

		line = self.highlight_line(pos)
		w = urwid.Columns([(self.len_address, urwid.Text(('Lineno', self.fmt_address % (pos)), align='right')), urwid.Text(masked_string(line, 'Text', 'selected'), wrap='clip')], dividechars=1)

		return (w, pos)

	def get_prev(self, position):
		pos = (position - (position % self.line_width)) - self.line_width
		if pos < 0:
			return (None, None)

		line = self.highlight_line(pos)
		w = urwid.Columns([(self.len_address, urwid.Text(('Lineno', self.fmt_address % (pos)), align='right')), urwid.Text(masked_string(line, 'Text', 'selected'), wrap='clip')], dividechars=1)

		return (w, pos)

	def change_size(self, size):
		width = size[0]
		old_width = self.line_width

		width -= self.len_address + 1
		line_width = max(width, 16)
		self.line_width = line_width - (line_width % 16)

		if self.line_width != old_width:
			self._modified()


class HexFileWalker(BinaryFileWalker):
	def __init__(self, fh, file_size, data=None):
		self.line_width = 16
		self.hex_width = int(self.line_width / 4) * 13
		super().__init__(fh, file_size, data)

	def get_focus(self):
		position = self.focus
		pos = position - (position % self.line_width)
		if (pos < 0) or (pos >= self.file_size):
			return (None, None)

		line = self.highlight_line(pos)
		h = hex_string(line, 'Text', 'markselect')
		w = urwid.Columns([(self.len_address, urwid.Text(('Lineno', self.fmt_address % (pos)), align='right')), (self.hex_width, urwid.Text(h)), urwid.Text([('Operator', '|'), *masked_string(line, 'String', 'markselect'), ('Operator', '|')], wrap='clip')], dividechars=1)

		return (w, pos)

	def get_next(self, position):
		pos = (position - (position % self.line_width)) + self.line_width
		if pos >= self.file_size:
			return (None, None)

		line = self.highlight_line(pos)
		h = hex_string(line, 'Text', 'selected')
		w = urwid.Columns([(self.len_address, urwid.Text(('Lineno', self.fmt_address % (pos)), align='right')), (self.hex_width, urwid.Text(h)), urwid.Text([('Operator', '|'), *masked_string(line, 'String', 'selected'), ('Operator', '|')], wrap='clip')], dividechars=1)

		return (w, pos)

	def get_prev(self, position):
		pos = (position - (position % self.line_width)) - self.line_width
		if pos < 0:
			return (None, None)

		line = self.highlight_line(pos)
		h = hex_string(line, 'Text', 'selected')
		w = urwid.Columns([(self.len_address, urwid.Text(('Lineno', self.fmt_address % (pos)), align='right')), (self.hex_width, urwid.Text(h)), urwid.Text([('Operator', '|'), *masked_string(line, 'String', 'selected'), ('Operator', '|')], wrap='clip')], dividechars=1)

		return (w, pos)

	def change_size(self, size):
		width = size[0]
		old_width = self.line_width

		width -= self.len_address + 4
		num_dwords = max(int(width / 17), 1)
		self.line_width = num_dwords * 4
		self.hex_width = int(self.line_width / 4) * 13

		if self.line_width != old_width:
			self._modified()


class BaseTextFileWalker(urwid.ListWalker):
	def set_focus(self, position):
		self.focus = position
		self._modified()

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
		pos = self.search_from_pos(self.focus, backwards)

		if pos is None:
			self.search_expression = None

		self._modified()

		return pos

	def stop_search(self):
		self.search_expression = None
		self._modified()

	def search_next(self):
		if self.search_backwards:
			pos = self.focus - 1
			if pos < 0:
				pos = self.len_lines - 1
		else:
			pos = self.focus + 1
			if pos >= self.len_lines:
				pos = 0

		pos = self.search_from_pos(pos, self.search_backwards)

		self._modified()

		return pos

	def search_prev(self):
		if self.search_backwards:
			pos = self.focus + 1
			if pos >= self.len_lines:
				pos = 0
		else:
			pos = self.focus - 1
			if pos < 0:
				pos = self.len_lines - 1

		pos = self.search_from_pos(pos, not self.search_backwards)

		self._modified()

		return pos

	def search_from_pos(self, pos, backwards):
		new_pos = None

		if new_pos is None:
			if backwards:
				slice = self.code[pos::-1]
			else:
				slice = self.code[pos:]

			for i, line in enumerate(slice):
				if self.search_expression.search(line):
					if backwards:
						new_pos = pos - i
					else:
						new_pos = pos + i

					break

		if new_pos is None:
			if backwards:
				slice = self.code[:pos:-1]
			else:
				slice = self.code[:pos]

			for i, line in enumerate(slice):
				if self.search_expression.search(line):
					if backwards:
						new_pos = (self.len_lines - 1) - i
					else:
						new_pos = i

					break

		return new_pos

	def highlight_line(self, line, attr):
		if not self.search_expression:
			return line

		len_part = 0
		part_offset = []
		for text_attr, text in line:
			len_part += len(text)
			part_offset.append(len_part)

		part_offset.append(0)

		raw_line = ''.join([x[1] for x in line])
		new_line = []
		start = 0
		m = self.search_expression.search(raw_line, start)
		while m:
			match_start = m.start()
			match_end = m.end()
			for i, (text_attr, text) in enumerate(line):
				if part_offset[i] <= start:
					continue

				if part_offset[i] < match_start:
					new_text = text[-(part_offset[i] - start):]
					if new_text:
						new_line.append((text_attr, new_text))
				else:
					new_text = text[max(start - part_offset[i-1], 0):match_start-part_offset[i-1]]
					if new_text:
						new_line.append((text_attr, new_text))

					break

			new_line.append((attr, raw_line[match_start:match_end]))

			start = match_end
			m = self.search_expression.search(raw_line, start)

		for i, (text_attr, text) in enumerate(line):
			if part_offset[i] <= start:
				continue

			new_text = text[-(part_offset[i] - start):]
			if new_text:
				new_line.append((text_attr, new_text))

		if not new_line:
			new_line.append(('Text', ''))

		return new_line

class TextFileWalker(BaseTextFileWalker):
	def __init__(self, fh, file_size, code, filename, tabsize, use_line_highlight):
		self.fh = fh
		self.file_size = file_size
		self.code = code.splitlines(keepends=True)
		self.filename = filename
		self.tabsize = tabsize
		self.use_line_highlight = use_line_highlight
		self.focus = 0
		self.search_expression = None
		self.search_backwards = False

		try:
			name = self.filename.name
			if name == name.upper():
				filename = self.filename.parent / self.filename.name.lower()
			else:
				filename = self.filename

			self.lexer = pygments.lexers.get_lexer_for_filename(filename, stripnl=False, tabsize=self.tabsize)
		except pygments.util.ClassNotFound:
			try:
				self.lexer = pygments.lexers.guess_lexer(code, stripnl=False, tabsize=self.tabsize)
			except pygments.util.ClassNotFound:
				self.lexer = pygments.lexers.special.TextLexer(stripnl=False, tabsize=self.tabsize)

		if self.use_line_highlight:
			self.lines = self.code
		else:
			self.lines = []
			line = []
			result = pygments.lex(code, self.lexer)
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


		line = self.highlight_line(self.lines[pos], 'markselect')
		w = urwid.Columns([(self.digits, urwid.Text(('Lineno', f'{pos+1}'), align='right')), urwid.Text(line, wrap='clip')], dividechars=1)

		return (w, pos)

	def get_next(self, position):
		pos = position + 1
		if pos >= self.len_lines:
			return (None, None)

		line = self.highlight_line(self.lines[pos], 'selected')
		w = urwid.Columns([(self.digits, urwid.Text(('Lineno', f'{pos+1}'), align='right')), urwid.Text(line, wrap='clip')], dividechars=1)

		return (w, pos)

	def get_prev(self, position):
		pos = position - 1
		if pos < 0:
			return (None, None)

		line = self.highlight_line(self.lines[pos], 'selected')
		w = urwid.Columns([(self.digits, urwid.Text(('Lineno', f'{pos+1}'), align='right')), urwid.Text(line, wrap='clip')], dividechars=1)

		return (w, pos)

	def highlight_line(self, code, attr):
		if self.use_line_highlight:
			line = []
			result = pygments.lex(code, self.lexer)
			for tokentype, value in result:
				for k, v in StyleFromToken.items():
					if tokentype in k:
						style = v
						break
				else:
					style = 'Text'

				if ReNewLine.search(value):
					line.append((style, ReNewLine.sub('', value)))
				else:
					line.append((style, value))
		else:
			line = code

		return super().highlight_line(line, attr)


class TextDirectoryWalker(BaseTextFileWalker):
	def __init__(self, files, filename):
		files.sort(key=functools.cmp_to_key(sort_by_name))

		self.fh = None
		self.file_size = 0
		self.code = [f'{x["label"]}\n' for x in files]
		self.files = files
		self.filename = filename
		self.lines = [[(x['palette'], x['label'])] for x in files]
		self.focus = 0
		self.search_expression = None
		self.search_backwards = False

		self.len_lines = len(self.lines)
		self.digits = len(str(self.len_lines))

	def get_focus(self):
		pos = self.focus
		if (pos < 0) or (pos >= self.len_lines):
			return (None, None)


		file = self.files[pos]
		line = self.highlight_line(self.lines[pos], 'markselect')
		w = urwid.Columns([urwid.Text(line, wrap='clip'), ('pack', urwid.Text((file['palette'], file['size']))), ('pack', urwid.Text((file['palette'], format_date(file['lstat'].st_mtime))))], dividechars=1)

		return (w, pos)

	def get_next(self, position):
		pos = position + 1
		if pos >= self.len_lines:
			return (None, None)

		file = self.files[pos]
		line = self.highlight_line(self.lines[pos], 'selected')
		w = urwid.Columns([urwid.Text(line, wrap='clip'), ('pack', urwid.Text((file['palette'], file['size']))), ('pack', urwid.Text((file['palette'], format_date(file['lstat'].st_mtime))))], dividechars=1)

		return (w, pos)

	def get_prev(self, position):
		pos = position - 1
		if pos < 0:
			return (None, None)

		file = self.files[pos]
		line = self.highlight_line(self.lines[pos], 'selected')
		w = urwid.Columns([urwid.Text(line, wrap='clip'), ('pack', urwid.Text((file['palette'], file['size']))), ('pack', urwid.Text((file['palette'], format_date(file['lstat'].st_mtime))))], dividechars=1)

		return (w, pos)


class FileViewListBox(urwid.ListBox):
	def __init__(self, controller, tabsize, use_line_highlight):
		self.controller = controller
		self.tabsize = tabsize
		self.use_line_highlight = use_line_highlight
		self.clear_walker = urwid.SimpleFocusListWalker([])
		self.walker = self.clear_walker
		self.hex_walker = None

		self.old_size = None

		super().__init__(self.walker)

	def clear(self):
		self.walker = self.clear_walker
		self.body = self.walker

	def read_file(self, filename, file_size):
		self.filename = filename
		self.file_size = file_size

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
			self.walker = DumpFileWalker(fh, self.file_size)
			self.hex_walker = HexFileWalker(fh, self.file_size)

		self.old_size = None

		self.body = self.walker

	def read_text_file(self, fh, encoding):
		fh.seek(0)
		data = fh.read(MAX_TEXT_FILE_SIZE)

		self.hex_walker = HexFileWalker(fh, len(data), data)

		try:
			code = data.decode(encoding)
		except UnicodeDecodeError:
			if encoding == 'windows-1252':
				return DumpFileWalker(fh, self.file_size)
			else:
				try:
					encoding = 'windows-1252'
					code = data.decode(encoding)
				except UnicodeDecodeError:
					self.text_file = False
					return DumpFileWalker(fh, self.file_size)

		self.file_size = len(data)

		lines_data = data.splitlines(keepends=True)
		len_line = 0
		self.line_offset = [len_line]
		for line in lines_data:
			len_line += len(line)
			self.line_offset.append(len_line)

		del self.line_offset[-1]

		w = TextFileWalker(fh, self.file_size, code, self.filename, self.tabsize, self.use_line_highlight)
		self.lines = w.lines
		self.len_lines = w.len_lines

		return w

	def read_directory(self, filename):
		self.text_file = True

		files = get_file_list(filename)
		w = TextDirectoryWalker(files, filename)
		self.lines = w.lines
		self.len_lines = w.len_lines
		self.file_size = self.len_lines

		len_line = 0
		self.line_offset = [len_line]
		for line in w.code:
			len_line += len(line)
			self.line_offset.append(len_line)

		del self.line_offset[-1]

		data = (''.join(w.code)).encode('utf-8')
		self.walker = w
		self.hex_walker = HexFileWalker(None, len(data), data)

		self.old_size = None

		self.body = self.walker

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

	def on_goto(self, pos):
		self.controller.screen.close_dialog()

		try:
			if self.use_hex_offset():
				pos = int(pos, 16)
			else:
				pos = int(pos, 10) - 1
		except ValueError:
			self.controller.screen.error(f'Invalid number: {pos}')
			return

		if self.use_hex_offset():
			if pos >= self.file_size:
				pos = self.file_size - 1
		else:
			if pos >= self.len_lines:
				pos = self.len_lines - 1

		if pos < 0:
			pos = 0

		try:
			self.set_focus(pos)
			self.set_focus_valign('top')
		except IndexError:
			pass

	def on_search(self, text, mode, flags):
		self.controller.screen.close_dialog()

		if not text:
			self.body.stop_search()
			self._invalidate()
			return

		if self.use_hex_offset():
			if flags.hex:
				parts = []
				use_hex_value = True
				for part in text.split('"'):
					if use_hex_value:
						for hex_part in part.split():
							hex_value = hex_part
							if hex_value.startswith('0x') or hex_value.startswith('0X'):
								hex_value = hex_value[2:]

							if len(hex_value) % 2:
								hex_value = f'0{hex_value}'

							try:
								parts.append(bytes.fromhex(hex_value))
							except ValueError:
								self.controller.screen.error(f'Hex pattern error: {hex_part}', title='Search', error=False)
								return
					else:
						parts.append(part.encode(sys.getdefaultencoding()))

					use_hex_value = not use_hex_value

				expression = b''.join(parts)
			else:
				expression = text.encode(sys.getdefaultencoding())
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

		self.controller.screen.error('Searching...', title='Search', error=False)
		self.controller.loop.draw_screen()

		pos = self.body.start_search(expression, flags.backwards)

		self.controller.screen.close_dialog()
		self.controller.loop.draw_screen()

		if pos is not None:
			try:
				self.set_focus(pos)
				self.set_focus_valign('top')
				self._invalidate()
			except IndexError:
				pass
		else:
			self.controller.screen.error('Search string not found', title='Search', error=False)

	def search_next(self):
		if self.body.search_expression is None:
			return

		self.controller.screen.error('Searching...', title='Search', error=False)
		self.controller.loop.draw_screen()

		pos = self.body.search_next()

		self.controller.screen.close_dialog()
		self.controller.loop.draw_screen()

		if pos is not None:
			try:
				self.set_focus(pos)
				self.set_focus_valign('top')
				self._invalidate()
			except IndexError:
				pass
		else:
			self.controller.screen.error('Search string not found', title='Search', error=False)

	def search_prev(self):
		if self.body.search_expression is None:
			return

		self.controller.screen.error('Searching...', title='Search', error=False)
		self.controller.loop.draw_screen()

		pos = self.body.search_prev()

		self.controller.screen.close_dialog()
		self.controller.loop.draw_screen()

		if pos is not None:
			try:
				self.set_focus(pos)
				self.set_focus_valign('top')
				self._invalidate()
			except IndexError:
				pass
		else:
			self.controller.screen.error('Search string not found', title='Search', error=False)

	def render(self, size, *args, **kwargs):
		if size != self.old_size:
			self.old_size = size
			try:
				self.body.change_size(size)
			except AttributeError:
				pass

		return super().render(size, *args, **kwargs)

	def keypress(self, size, key):
		if key in ('h', 'f4'):
			try:
				prev_focus = self.focus_position
			except IndexError:
				prev_focus = 0

			if self.body == self.walker:
				self.body = self.hex_walker
				try:
					if self.text_file:
						self.set_focus(self.line_offset[prev_focus])
					else:
						self.set_focus(prev_focus)
				except IndexError:
					pass
			else:
				self.body = self.walker
				try:
					if self.text_file:
						self.set_focus(self.line_from_offset(prev_focus))
					else:
						self.set_focus(prev_focus)
				except IndexError:
					pass

			if 'bottom' in self.ends_visible(size):
				try:
					self.set_focus(self.body.get_focus_offset(self.file_size))
					self.set_focus(self.body.get_focus_offset(min(-(size[1] - 1), -1)))
				except IndexError:
					pass

			try:
				self.set_focus_valign('top')
			except IndexError:
				pass

			self.body.change_size(size)

			self._invalidate()
		elif key in ('j', 'down'):
			try:
				self.set_focus(self.body.get_focus_offset(1))
				if 'bottom' in self.ends_visible(size):
					self.set_focus(self.body.get_focus_offset(self.file_size))
					self.set_focus(self.body.get_focus_offset(min(-(size[1] - 1), -1)))

				self.set_focus_valign('top')

				self._invalidate()
			except IndexError:
				pass
		elif key in ('k', 'up'):
			try:
				if 'bottom' in self.ends_visible(size):
					self.set_focus(self.body.get_focus_offset(self.file_size))
					self.set_focus(self.body.get_focus_offset(min(-(size[1] - 1), -1)))

				self.set_focus(self.body.get_focus_offset(-1))
				self.set_focus_valign('top')

				self._invalidate()
			except IndexError:
				pass
		elif key in ('g', 'home'):
			try:
				self.set_focus(0)
				self.set_focus_valign('top')

				self._invalidate()
			except IndexError:
				pass
		elif key in ('G', 'end'):
			try:
				self.set_focus(self.body.get_focus_offset(self.file_size))
				self.set_focus(self.body.get_focus_offset(min(-(size[1] - 1), -1)))
				self.set_focus_valign('top')

				self._invalidate()
			except IndexError:
				pass
		elif key in ('ctrl b', 'page up'):
			try:
				if 'bottom' in self.ends_visible(size):
					self.set_focus(self.body.get_focus_offset(self.file_size))
					self.set_focus(self.body.get_focus_offset(min(-(size[1] - 1), -1)))

				self.set_focus(self.body.get_focus_offset(min(-(size[1] - 1), -1)))
				self.set_focus_valign('top')

				self._invalidate()
			except IndexError:
				pass
		elif key in ('ctrl f', 'page down'):
			try:
				self.set_focus(self.body.get_focus_offset(max(size[1] - 1, 1)))
				if 'bottom' in self.ends_visible(size):
					self.set_focus(self.body.get_focus_offset(self.file_size))
					self.set_focus(self.body.get_focus_offset(min(-(size[1] - 1), -1)))

				self.set_focus_valign('top')

				self._invalidate()
			except IndexError:
				pass
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

		self.list_box = FileViewListBox(controller, tabsize, use_line_highlight=False)

		try:
			self.list_box.read_file(filename, file_size)
			self.center = urwid.AttrMap(self.list_box, 'Text')
		except IsADirectoryError:
			self.list_box.read_directory(filename)
			self.center = urwid.AttrMap(self.list_box, 'panel')

		pile_widgets = [(1, urwid.Filler(top)), self.center]

		self.bottom = ButtonBar(Labels)
		w = urwid.Filler(self.bottom)
		if SHOW_BUTTONBAR:
			pile_widgets.append((1, w))

		self.pile = urwid.Pile(pile_widgets)
		self.main_area = 1

		super().__init__(self.pile)

	def close_dialog(self):
		self.pile.contents[self.main_area] = (self.center, self.pile.options())

		self.in_error = False

	def error(self, e, title='Error', error=True):
		self.pile.contents[self.main_area] = (urwid.Overlay(DlgError(self, e, title, error), self.center,
			'center', len(e) + 6,
			'middle', 'pack',
		), self.pile.options())

		self.in_error = True


class App(object):
	def __init__(self, filename, file_size, monochrome, tabsize):
		self.filename = filename
		self.monochrome = monochrome
		self.tabsize = tabsize

		self.focused_quickviewer = False

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

	if key == 'esc':
		controller.screen.list_box.body.stop_search()
		controller.screen.list_box._invalidate()
	elif key in ('q', 'Q', 'v', 'f3', 'f10'):
		try:
			controller.close_viewer(key)
		except AttributeError:
			raise urwid.ExitMainLoop()
	elif key in (':', 'f5'):
		if controller.screen.list_box.file_size == 0:
			return

		if controller.screen.list_box.use_hex_offset():
			label = 'Hex offset: '
		else:
			label = 'Line number: '

		controller.screen.pile.contents[controller.screen.main_area] = (urwid.Overlay(DlgGoto(controller.screen, controller.screen.list_box.on_goto, lambda x: controller.screen.close_dialog(), label=label), controller.screen.center,
			'center', 30,
			'middle', 'pack',
		), controller.screen.pile.options())
	elif key in ('/', '?', 'f', 'f7'):
		if controller.screen.list_box.file_size == 0:
			return

		backwards = (key == '?')

		controller.screen.pile.contents[controller.screen.main_area] = (urwid.Overlay(DlgSearch(controller.screen, controller.screen.list_box.on_search, lambda x: controller.screen.close_dialog(), text_file=not controller.screen.list_box.use_hex_offset(), backwards=backwards), controller.screen.center,
			'center', 58,
			'middle', 'pack',
		), controller.screen.pile.options())
	elif key == 'n':
		controller.screen.list_box.search_next()
	elif key == 'N':
		controller.screen.list_box.search_prev()
	elif key in ('tab', 'shift tab', 'ctrl u', 'ctrl q'):
		if controller.focused_quickviewer:
			controller.set_input_rnr()
			controller.keypress(key)


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('FILE', help='the file to view')
	parser.add_argument('-V', '--version', action='version', version=f'%(prog)s {__version__}')
	parser.add_argument('-b', '--nocolor', help='Requests to run in black and white', action='store_true', dest='monochrome')
	parser.add_argument('-t', '--tabsize', help='set tab size (default: %(default)d)', type=int, default=TAB_SIZE)
	parser.add_argument('-d', '--debug', help='activate debug mode', action='store_true')
	args = parser.parse_args()

	filename = Path(args.FILE)

	if args.debug:
		set_debug_fh(open(Path.home() / 'rnr.log', 'w', buffering=1))

	try:
		file_size = os.stat(filename).st_size
		app = App(filename, file_size, args.monochrome, args.tabsize)
	except OSError as e:
		print(e, file=sys.stderr)
		return 1

	app.run()


if __name__ == '__main__':
	sys.exit(main())

