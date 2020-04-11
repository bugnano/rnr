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

import urwid


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

class AbortedError(Exception):
	pass

class SkippedError(Exception):
	pass

