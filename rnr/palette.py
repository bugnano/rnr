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

from .import_config import *


PALETTE = [
	('default', 'default', 'default'),
	('default_error', 'light red', 'default', 'default,bold'),

	('panel', PANEL_FG, PANEL_BG),
	('reverse', REVERSE_FG, REVERSE_BG, 'standout'),
	('selected', SELECTED_FG, SELECTED_BG, 'standout'),
	('marked', MARKED_FG, PANEL_BG, 'default,bold'),
	('markselect', MARKSELECT_FG, SELECTED_BG, 'standout,bold'),

	('directory', DIRECTORY_FG, PANEL_BG),
	('dir_symlink', DIR_SYMLINK_FG, PANEL_BG),
	('executable', EXECUTABLE_FG, PANEL_BG),
	('symlink', SYMLINK_FG, PANEL_BG),
	('stalelink', STALELINK_FG, PANEL_BG),
	('device', DEVICE_FG, PANEL_BG),
	('special', SPECIAL_FG, PANEL_BG),
	('archive', ARCHIVE_FG, PANEL_BG),

	('hotkey', HOTKEY_FG, HOTKEY_BG),

	('error', ERROR_FG, ERROR_BG, 'standout'),
	('error_title', ERROR_TITLE_FG, ERROR_BG, 'standout'),
	('error_focus', ERROR_FOCUS_FG, ERROR_FOCUS_BG, 'standout'),

	('dialog', DIALOG_FG, DIALOG_BG, 'standout'),
	('dialog_title', DIALOG_TITLE_FG, DIALOG_BG, 'standout'),
	('dialog_focus', DIALOG_FOCUS_FG, DIALOG_FOCUS_BG, 'standout'),
	('progress', DIALOG_BG, DIALOG_FG),
	('input', INPUT_FG, INPUT_BG),

	('Text', TEXT_FG, TEXT_BG),
	('Namespace', NAMESPACE_FG, TEXT_BG),
	('Keyword', KEYWORD_FG, TEXT_BG),
	('Class', CLASS_FG, TEXT_BG),
	('Operator', OPERATOR_FG, TEXT_BG),
	('String', STRING_FG, TEXT_BG),
	('Literal', LITERAL_FG, TEXT_BG),
	('Comment', COMMENT_FG, TEXT_BG),
	('Lineno', LINENO_FG, TEXT_BG, 'default,bold'),
]

