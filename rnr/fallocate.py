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

import errno
import ctypes

from ctypes.util import find_library


__all__ = ['fallocate', 'FALLOC_FL_KEEP_SIZE', 'FALLOC_FL_PUNCH_HOLE']


FALLOC_FL_KEEP_SIZE = 0x01
FALLOC_FL_PUNCH_HOLE = 0x02


libc = ctypes.CDLL(find_library('c'))
prototype = ctypes.CFUNCTYPE(ctypes.c_int, *[ctypes.c_int, ctypes.c_int, ctypes.c_int64, ctypes.c_int64], use_errno=True)

try:
	fallocate = prototype(('fallocate', libc))
	fallocate.get_errno = ctypes.get_errno
except AttributeError:
	def fallocate(*args):
		return -1

	fallocate.get_errno = lambda: errno.ENOTSUP

