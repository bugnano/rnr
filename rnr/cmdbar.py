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

import subprocess
import signal

from pathlib import Path

import urwid

from .utils import (tar_stem, tar_suffix, apply_template)
from .debug_print import (debug_print, debug_pprint)



class CmdEdit(urwid.Edit):
	def keypress(self, size, key):
		if key in ('up', 'down'):
			pass
		elif key == 'backspace':
			if self.edit_pos:
				return super().keypress(size, key)
		else:
			return super().keypress(size, key)


class CmdBar(urwid.WidgetWrap):
	def __init__(self, controller, screen):
		self.controller = controller
		self.screen = screen

		self.action = None
		self.leader = ''
		self.file = None
		self.callback = None
		self.forced_focus = False

		self.edit = CmdEdit()

		w = urwid.AttrMap(self.edit, 'default')

		super().__init__(w)

		urwid.connect_signal(self.edit, 'change', self.on_change)

	def on_change(self, edit, new_edit_text):
		if self.action == 'filter':
			self.screen.center.focus.filter(new_edit_text)
			self.screen.center.focus.force_focus()

	def reset(self):
		self.edit.set_caption('')
		self.edit.set_edit_text('')
		self.screen.pile.focus_position = 0
		if self.forced_focus:
			self.screen.center.focus.remove_force_focus()

		self.action = None
		self.leader = ''
		self.file = None
		self.callback = None
		self.forced_focus = False

	def execute(self):
		if self.action == 'mkdir':
			self.do_mkdir()
		elif self.action == 'rename':
			self.do_rename()
		elif self.action == 'tag_glob':
			self.do_tag_glob()
		elif self.action == 'untag_glob':
			self.do_untag_glob()
		elif self.action == 'shell':
			self.do_shell()
		elif self.action == 'save':
			self.do_save()

		self.action = None
		self.leader = ''

		self.edit.set_caption('')
		self.edit.set_edit_text('')
		self.screen.pile.focus_position = 0
		if self.forced_focus:
			self.screen.center.focus.remove_force_focus()

		self.forced_focus = False

		if self.callback:
			file = self.file
			callback = self.callback
			self.file = None
			self.callback = None
			callback(file)


	def set_leader(self, leader):
		self.leader = leader
		self.edit.set_caption(self.leader)

	def prepare_action(self, action, caption, text, edit_pos=-1, forced_focus=True):
		self.action = action
		self.edit.set_caption(caption)
		self.edit.set_edit_text(text)
		if edit_pos < 0:
			self.edit.set_edit_pos(len(text))
		else:
			self.edit.set_edit_pos(edit_pos)
		self.screen.pile.focus_position = 1
		self.forced_focus = forced_focus
		if self.forced_focus:
			self.screen.center.focus.force_focus()

	def filter(self):
		self.prepare_action('filter', 'filter: ', self.screen.center.focus.file_filter)

	def mkdir(self, cwd):
		self.file = cwd
		self.prepare_action('mkdir', 'mkdir: ', '')

	def do_mkdir(self):
		new_dir = Path(apply_template(self.edit.get_edit_text(), self.screen, quote=False))
		try:
			new_dir = new_dir.expanduser()
		except RuntimeError:
			pass

		if new_dir.is_absolute():
			new_dir = Path(os.path.normpath(new_dir))
		else:
			new_dir = Path(os.path.normpath(self.file / new_dir))

		try:
			os.makedirs(new_dir, exist_ok=True)
			self.controller.reload(new_dir, only_focused=True)
		except (PermissionError, FileExistsError) as e:
			self.screen.error(f'{e.strerror} ({e.errno})')

	def rename(self, file, mode):
		self.file = file
		text = file.name.replace('%', '%%')
		if mode == 'replace':
			text = ''
			edit_pos = -1
		elif mode == 'insert':
			edit_pos = 0
		elif mode == 'append_before':
			edit_pos = len(tar_stem(file).replace('%', '%%'))
		elif mode == 'replace_before':
			text = tar_suffix(file).replace('%', '%%')
			edit_pos = 0
		else:
			edit_pos = -1

		self.prepare_action('rename', 'rename: ', text, edit_pos)

	def do_rename(self):
		new_name = Path(apply_template(self.edit.get_edit_text(), self.screen, quote=False))
		try:
			new_name = new_name.expanduser()
		except RuntimeError:
			pass

		if new_name.is_absolute():
			new_name = Path(os.path.normpath(new_name))
		else:
			new_name = Path(os.path.normpath(self.file.parent / new_name))

		try:
			if os.path.lexists(new_name):
				if new_name.is_dir():
					if new_name.resolve() == self.file.parent.resolve():
						return

					new_name = new_name / self.file.name
				else:
					if (new_name.parent.resolve() / new_name.name) == (self.file.parent.resolve() / self.file.name):
						return

					self.screen.error(f'File already exists')
					return

			self.file.rename(new_name)
			self.controller.reload(new_name, old_focus=self.file)
		except OSError as e:
			self.screen.error(f'{e.strerror} ({e.errno})')

	def tag_glob(self):
		self.prepare_action('tag_glob', 'tag: ', '*')

	def do_tag_glob(self):
		self.screen.center.focus.tag_glob(self.edit.get_edit_text())

	def untag_glob(self):
		self.prepare_action('untag_glob', 'untag: ', '*')

	def do_untag_glob(self):
		self.screen.center.focus.untag_glob(self.edit.get_edit_text())

	def shell(self):
		self.prepare_action('shell', 'shell: ', '')

	def do_shell(self):
		cwd = str(self.screen.center.focus.cwd)

		self.controller.loop.stop()
		prompt = ('$' if os.geteuid() else '#')
		cmd = apply_template(self.edit.get_edit_text(), self.screen)
		print(f'[{cwd}]{prompt} {cmd}')
		subprocess.run(cmd, shell=True, cwd=cwd)
		self.controller.loop.start()
		os.kill(os.getpid(), signal.SIGWINCH)
		self.controller.reload()

	def save(self, file, callback, forced_focus=True):
		self.file = file
		self.callback = callback
		text = str(file).replace('%', '%%')
		edit_pos = len(str(file.parent).replace('%', '%%'))
		self.prepare_action('save', 'save: ', text, edit_pos, forced_focus=forced_focus)

	def do_save(self):
		file = Path(apply_template(self.edit.get_edit_text(), self.screen, quote=False))
		try:
			file = file.expanduser()
		except RuntimeError:
			pass

		if file.is_absolute():
			file = Path(os.path.normpath(file))
		else:
			file = Path(os.path.normpath(self.file.parent / file))

		self.file = file

	def error(self, e):
		self.edit.set_caption(('default_error', f'ERROR: {e}'))
		self.edit.set_edit_text('')

