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

import datetime
import string
import shlex

from pathlib import Path

import urwid

from .debug_print import (debug_print, debug_pprint)


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
		if len(text) <= width:
			return [[(len(text), 0, text.encode('utf-8'))]]

		full_len = max(width - 1, 2)
		half = int(full_len / 2)
		left = half
		right = full_len - left

		return [[(width, 0, f'{text[:left]}~{text[-right:]}'[:width].encode('utf-8'))]]

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

def apply_template(text, screen, quote=True):
	if quote:
		fn_quote = shlex.quote
	else:
		fn_quote = str

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

	other_cwd = str(other.cwd)

	try:
		other_file = fn_quote(str(other.get_focus()['file']))
		other_name = fn_quote(tar_stem(other.get_focus()['file']))
		other_extension = fn_quote(tar_suffix(other.get_focus()['file']))
	except (TypeError, AttributeError):
		other_file = fn_quote('')
		other_name = fn_quote('')
		other_extension = fn_quote('')

	other_tagged = ' '.join([fn_quote(str(x)) for x in other.get_tagged_files()])
	if not current_tagged:
		other_tagged = fn_quote('')

	s = Template(text)
	d = {
		'f': current_file,
		'n': current_name,
		'e': current_extension,
		'd': fn_quote(cwd),
		'b': fn_quote(Path(cwd).name),
		's': current_tagged,
		't': current_tagged,
		'F': other_file,
		'N': other_name,
		'E': other_extension,
		'D': fn_quote(other_cwd),
		'B': fn_quote(Path(other_cwd).name),
		'S': other_tagged,
		'T': other_tagged,
	}

	return s.safe_substitute(d)

