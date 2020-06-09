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

from pathlib import Path

import xdg.BaseDirectory

CONFIG_DIR = Path(xdg.BaseDirectory.save_config_path('rnr'))

sys.path.insert(0, str(CONFIG_DIR))
_dont_write_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True

from .config import *

try:
	from config import *
except ModuleNotFoundError:
	try:
		shutil.copy(Path(__file__).parent / 'config.py', CONFIG_DIR)
		from config import *
	except (ModuleNotFoundError, FileNotFoundError, PermissionError, IsADirectoryError):
		pass

sys.dont_write_bytecode = _dont_write_bytecode
del _dont_write_bytecode
sys.path.pop(0)

