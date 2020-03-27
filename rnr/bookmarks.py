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

import string
import collections

from atomicwrites import atomic_write


BOOKMARK_KEYS = tuple(string.ascii_letters + string.digits)


class Bookmarks(collections.UserDict):
	def __init__(self, file):
		super().__init__()

		self.file = str(file)

		try:
			with open(self.file, 'r') as fh:
				for line in fh:
					line = line.rstrip('\r\n')
					if (len(line) < 3) or (line[1] != ':') or (line[0] not in BOOKMARK_KEYS):
						continue

					self.data[line[0]] = line[2:]
		except (FileNotFoundError, PermissionError, IsADirectoryError):
			pass

	def __setitem__(self, key, item):
		key = str(key)
		item = str(item)

		if (len(key) != 1) or (key not in BOOKMARK_KEYS):
			return

		if (key not in self.data) or (self.data[key] != item):
			self.data[key] = item

			try:
				with atomic_write(self.file, overwrite=True) as f:
					for k, v in sorted(self.data.items()):
						f.write(f'{k}:{v}\n')
			except (FileNotFoundError, PermissionError, IsADirectoryError):
				pass

