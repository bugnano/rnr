#! /usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (C) 2020-2022  Franco Bugnano
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

import datetime
import string
import shlex
import unicodedata
import re

from pathlib import Path

import urwid

from urwid.util import str_util

from .debug_print import (debug_print, debug_pprint)


ReNumbers = re.compile(r'(\d+)')


def human_readable_size(size):
	if size < 1024:
		return f'{size:d}B'

	for suffix in ['K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']:
		size /= 1024
		if size < 1024:
			break

	return f'{size:.{max(4 - len(str(int(size))), 1)}f}{suffix}'

def format_date(d):
	d = datetime.datetime.fromtimestamp(d)
	today = datetime.date.today()
	if d.date() == today:
		return d.strftime('%H:%M').center(7)
	elif d.year == today.year:
		return d.strftime('%b %d').center(7)
	else:
		return d.strftime('%Y-%m').center(7)

def format_seconds(t):
	days, remainder = divmod(t, 86400)
	hours, remainder = divmod(remainder, 3600)
	minutes, seconds = divmod(remainder, 60)

	if days:
		return f'{days}d{hours:02d}:{minutes:02d}:{seconds:02d}'
	else:
		return f'{hours:02d}:{minutes:02d}:{seconds:02d}'

def try_int(s):
	try:
		return ('0', int(s))
	except ValueError:
		return (s, 0)

def natsort_key(s):
	return [try_int(x) for x in ReNumbers.split(unicodedata.normalize('NFKD', s.casefold()))]

def tar_stem(file):
	p = Path(file)
	suffixes = p.suffixes
	if (len(suffixes) >= 2) and (suffixes[-2].lower() == '.tar'):
		return Path(p.stem).stem
	else:
		return p.stem

def tar_suffix(file):
	p = Path(file)
	suffixes = p.suffixes
	if (len(suffixes) >= 2) and (suffixes[-2].lower() == '.tar'):
		return ''.join(suffixes[-2:])
	else:
		return p.suffix


class TildeTextLayout(urwid.TextLayout):
	def layout(self, text, width, align, wrap):
		text = unicodedata.normalize('NFKC', text)
		in_error = True
		while in_error:
			try:
				utf8_text = text.encode('utf-8')
				in_error = False
			except UnicodeError as e:
				text = ''.join([text[:e.start], '\uFFFD' * (e.end - e.start), text[e.end:]])

		widths = [str_util.get_width(ord(x)) for x in text]
		text_width = sum(widths)
		if text_width <= width:
			return [[(text_width, 0, utf8_text)]]

		full_len = max(width - 1, 2)
		left = int(full_len / 2)
		right = full_len - left

		left_width = 0
		for i, e in enumerate(widths):
			left_width += e
			if left_width > left:
				i_left = i
				break

		right_width = 0
		for i, e in enumerate(reversed(widths)):
			right_width += e
			if right_width > right:
				i_right = len(text) - i
				break

		tilde_text = f'{text[:i_left]}~{text[i_right:]}'
		if len(tilde_text) <= 3:
			widths = [str_util.get_width(ord(x)) for x in tilde_text]
			text_width = sum(widths)
			while text_width > width:
				tilde_text = tilde_text[:-1]
				text_width -= widths.pop(-1)

		return [[(width, 0, tilde_text.encode('utf-8'))]]

	def pack(self, maxcol, layout):
		maxwidth = 0
		for l in layout:
			for line in l:
				maxwidth = max(line[0], maxwidth)

		return min(maxwidth, maxcol)

TildeLayout = TildeTextLayout()


class TLineWidget(urwid.WidgetWrap):
	def __init__(self, title, title_align='center', title_attr=None, lcorner='├', tline='─', rcorner='┤'):
		self.title_widget = title
		self.title_attr = urwid.AttrMap(self.title_widget, title_attr)
		tline_divider = urwid.Divider(tline)

		if title_align == 'left':
			tline_widgets = [('pack', self.title_attr), tline_divider]
		else:
			tline_widgets = [tline_divider, ('pack', self.title_attr)]
			if title_align == 'center':
				tline_widgets.append(tline_divider)

		self.tline_widget = urwid.Columns(tline_widgets)

		w = urwid.Columns([(1, urwid.Text(lcorner)), (1, urwid.Text(tline)), self.tline_widget, (1, urwid.Text(tline)), (1, urwid.Text(rcorner))])

		super().__init__(w)

	def set_title(self, text):
		self.title_widget.set_text(text)

	def set_title_attr(self, attr):
		self.title_attr.set_attr_map({None: attr})


class InterruptError(Exception):
	pass

class AbortedError(Exception):
	pass

class SkippedError(Exception):
	pass


class Template(string.Template):
	delimiter = '%'

def apply_template(text, screen, quote=True, unarchive_path=None):
	if quote:
		fn_quote = shlex.quote
	else:
		fn_quote = str

	if unarchive_path is None:
		unarchive_path = lambda x, include_self=True: (x, None, None)

	cwd = str(screen.center.focus.cwd)

	try:
		current_file = fn_quote(str(screen.center.focus.get_focus()['file'].relative_to(cwd)))
		current_name = fn_quote(tar_stem(screen.center.focus.get_focus()['file']))
		current_extension = fn_quote(tar_suffix(screen.center.focus.get_focus()['file']))
	except (TypeError, AttributeError):
		current_file = fn_quote('')
		current_name = fn_quote('')
		current_extension = fn_quote('')

	current_tagged = ' '.join([fn_quote(str(x.relative_to(cwd))) for x in screen.center.focus.get_tagged_files()])
	if not current_tagged:
		current_tagged = fn_quote('')

	if screen.center.focus == screen.left:
		other = screen.right
	else:
		other = screen.left

	try:
		other_file = fn_quote(str(unarchive_path(other.get_focus()['file'], include_self=False)[0]))
		other_name = fn_quote(tar_stem(other.get_focus()['file']))
		other_extension = fn_quote(tar_suffix(other.get_focus()['file']))
	except (TypeError, AttributeError):
		other_file = fn_quote('')
		other_name = fn_quote('')
		other_extension = fn_quote('')

	other_tagged = ' '.join([fn_quote(str(unarchive_path(x, include_self=False)[0])) for x in other.get_tagged_files()])
	if not current_tagged:
		other_tagged = fn_quote('')

	s = Template(text)
	d = {
		'f': current_file,
		'n': current_name,
		'e': current_extension,
		'd': fn_quote(str(unarchive_path(cwd)[0])),
		'b': fn_quote(Path(cwd).name),
		's': current_tagged,
		't': current_tagged,
		'F': other_file,
		'N': other_name,
		'E': other_extension,
		'D': fn_quote(str(unarchive_path(other.cwd)[0])),
		'B': fn_quote(Path(other.cwd).name),
		'S': other_tagged,
		'T': other_tagged,
	}

	return s.safe_substitute(d)

