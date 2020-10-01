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

import argparse
import shutil
import stat
import signal
import functools

from pathlib import Path
from queue import Queue
from threading import (Thread, Event)

import urwid

import xdg.BaseDirectory

from . import __version__
from . import rnrview

from .import_config import *
from .palette import PALETTE
from .panel import Panel
from .preview_panel import PreviewPanel
from .cmdbar import CmdBar
from .buttonbar import ButtonBar
from .bookmarks import (Bookmarks, BOOKMARK_KEYS)
from .dlg_error import DlgError
from .dlg_question import DlgQuestion
from .dlg_dirscan import DlgDirscan
from .rnr_dirscan import rnr_dirscan
from .dlg_delete_progress import DlgDeleteProgress
from .rnr_delete import rnr_delete
from .dlg_report import DlgReport
from .dlg_cpmv import DlgCpMv
from .dlg_cpmv_progress import DlgCpMvProgress
from .rnr_cpmv import rnr_cpmv
from .database import DataBase
from .dlg_pending_job import DlgPendingJob
from .debug_print import (debug_print, debug_pprint, set_debug_fh)


DATA_DIR = Path(xdg.BaseDirectory.save_data_path('rnr'))


Labels = [
	' ', #'Help',
	' ', #'Menu',
	'View',
	'Edit',
	'Copy',
	'Move',
	'Mkdir',
	'Delete',
	' ', #'PullDn',
	'Quit',
]


class Screen(urwid.WidgetWrap):
	def __init__(self, controller):
		self.left = Panel(controller)
		self.right = Panel(controller)
		self.preview_panel = PreviewPanel(controller)
		#self.center = urwid.Columns([self.left, self.preview_panel, self.right])
		self.center = urwid.Columns([self.left, self.right])
		self.command_bar = CmdBar(controller, self)
		w = urwid.Filler(self.command_bar)
		pile_widgets = [self.center, (1, w)]

		self.bottom = ButtonBar(Labels)
		w = urwid.Filler(self.bottom)
		if SHOW_BUTTONBAR:
			pile_widgets.append((1, w))

		self.pile = urwid.Pile(pile_widgets)
		self.pile.focus_position = 0
		self.main_area = 0

		self.list_box = self.preview_panel.listbox

		self.show_preview = False
		self.in_error = False

		super().__init__(self.pile)

	def update_focus(self):
		for i, e in enumerate(self.center.contents):
			if i == self.center.focus_position:
				e[0].set_title_attr('reverse')
				e[0].focused = True
				try:
					e[0].show_preview(e[0].get_focus())
				except AttributeError:
					pass
			else:
				e[0].set_title_attr('panel')
				e[0].focused = False

	def close_dialog(self):
		self.pile.contents[self.main_area] = (self.center, self.pile.options())

		try:
			self.center.focus.remove_force_focus()
		except AttributeError:
			pass

		self.in_error = False

	def error(self, e, title='Error', error=True):
		try:
			self.center.focus.force_focus()
		except AttributeError:
			pass

		self.pile.contents[self.main_area] = (urwid.Overlay(DlgError(self, e, title, error), self.center,
			'center', len(e) + 6,
			'middle', 'pack',
		), self.pile.options())

		self.in_error = True


class App(object):
	def __init__(self, printwd, dbfile, monochrome, tabsize):
		self.printwd = printwd

		if not dbfile:
			self.dbfile = None
		elif dbfile == ':memory:':
			self.dbfile = dbfile
		else:
			self.dbfile = str(Path(dbfile).resolve())

		self.monochrome = monochrome
		self.tabsize = tabsize

		if self.dbfile:
			db = DataBase(self.dbfile)
			del db

		self.opener = OPENER
		self.pager = PAGER
		self.editor = EDITOR
		self.use_internal_viewer = USE_INTERNAL_VIEWER

		self.old_screen = None
		self.loop = None
		self.screen = Screen(self)
		self.screen.update_focus()
		self.leader = ''
		self.ev_interrupt = Event()
		self.suspend = set()
		self.pending_jobs = []
		self.focused_quickviewer = False

		self.bookmarks = Bookmarks(CONFIG_DIR / 'bookmarks')
		if 'h' not in self.bookmarks:
			self.bookmarks['h'] = Path.home()

		self.check_pending_jobs()

	def run(self):
		self.loop = urwid.MainLoop(self.screen, PALETTE, unhandled_input=self.keypress)

		if self.monochrome:
			self.loop.screen.set_terminal_properties(colors=1)

		signal.signal(signal.SIGINT, self.signal_handler)
		signal.signal(signal.SIGTERM, self.signal_handler)

		self.loop.run()

	def signal_handler(self, signum, frame):
		try:
			self.loop.stop()
		except AttributeError:
			pass

		if signum == signal.SIGINT:
			print('Ctrl+C')
		elif signum == signal.SIGTERM:
			print('Kill')

		self.ev_interrupt.set()

		for ev in self.suspend:
			ev.set()

		sys.exit(1)

	def keypress(self, key):
		if key == 'esc':
			self.screen.command_bar.reset()
			self.leader = ''
		elif self.leader == 's':
			if key == 'n':
				self.screen.left.sort('sort_by_name')
				self.screen.right.sort('sort_by_name')
			elif key == 'N':
				self.screen.left.sort('sort_by_name', reverse=True)
				self.screen.right.sort('sort_by_name', reverse=True)
			elif key == 'e':
				self.screen.left.sort('sort_by_extension')
				self.screen.right.sort('sort_by_extension')
			elif key == 'E':
				self.screen.left.sort('sort_by_extension', reverse=True)
				self.screen.right.sort('sort_by_extension', reverse=True)
			elif key == 'd':
				self.screen.left.sort('sort_by_date')
				self.screen.right.sort('sort_by_date')
			elif key == 'D':
				self.screen.left.sort('sort_by_date', reverse=True)
				self.screen.right.sort('sort_by_date', reverse=True)
			elif key == 's':
				self.screen.left.sort('sort_by_size')
				self.screen.right.sort('sort_by_size')
			elif key == 'S':
				self.screen.left.sort('sort_by_size', reverse=True)
				self.screen.right.sort('sort_by_size', reverse=True)

			self.screen.command_bar.reset()
			self.leader = ''
		elif self.leader == 'm':
			if key in BOOKMARK_KEYS:
				self.bookmarks[key] = self.screen.center.focus.cwd

			self.screen.command_bar.reset()
			self.leader = ''
		elif self.leader in ('`', "'"):
			if key in ('`', "'"):
				if self.screen.center.focus.old_cwd != self.screen.center.focus.cwd:
					self.screen.center.focus.chdir(self.screen.center.focus.old_cwd)
			elif key in BOOKMARK_KEYS:
				try:
					if self.bookmarks[key] != str(self.screen.center.focus.cwd):
						self.screen.center.focus.chdir(Path(self.bookmarks[key]))
				except KeyError:
					pass

			self.screen.command_bar.reset()
			self.leader = ''
		elif self.leader == 'u':
			if key == 'v':
				self.screen.center.focus.untag_all()
			elif key in ('f', '/'):
				self.screen.center.focus.filter('')

			self.screen.command_bar.reset()
			self.leader = ''
		elif self.leader == 'c':
			self.screen.command_bar.reset()
			self.leader = ''
			if key in ('c', 'w'):
				obj = self.screen.center.focus.get_focus()
				try:
					self.screen.command_bar.rename(obj['file'], mode='replace')
				except TypeError as e:
					pass
			elif key == 'e':
				obj = self.screen.center.focus.get_focus()
				try:
					self.screen.command_bar.rename(obj['file'], mode='replace_before')
				except TypeError:
					pass
		else:
			if key in ('q', 'Q', 'f10'):
				self.quit()
			elif key == 'tab':
				if self.screen.pile.focus_position == 0:
					self.screen.center.focus_position = (self.screen.center.focus_position + 1) % len(self.screen.center.contents)
					self.screen.update_focus()
					if self.screen.center.focus == self.screen.preview_panel:
						self.focused_quickviewer = True
						self.set_input_rnrview()
					else:
						self.focused_quickviewer = False
			elif key == 'shift tab':
				if self.screen.pile.focus_position == 0:
					self.screen.center.focus_position = (self.screen.center.focus_position - 1) % len(self.screen.center.contents)
					self.screen.update_focus()
					if self.screen.center.focus == self.screen.preview_panel:
						self.focused_quickviewer = True
						self.set_input_rnrview()
					else:
						self.focused_quickviewer = False
			elif key in ('f', '/'):
				self.screen.command_bar.filter()
			elif key == 'enter':
				self.screen.command_bar.execute()
			elif key == 'backspace':
				self.screen.left.toggle_hidden()
				self.screen.right.toggle_hidden()
			elif key == 's':
				self.leader = key
				self.screen.command_bar.set_leader(self.leader)
			elif key == 'm':
				self.leader = key
				self.screen.command_bar.set_leader(self.leader)
			elif key in ('`', "'"):
				self.leader = key
				self.screen.command_bar.set_leader(self.leader)
			elif key == 'u':
				self.leader = key
				self.screen.command_bar.set_leader(self.leader)
			elif key == 'meta i':
				cwd = self.screen.center.focus.cwd

				if (self.screen.left is not self.screen.center.focus) and (self.screen.left.cwd != cwd):
					self.screen.left.chdir(cwd)

				if (self.screen.right is not self.screen.center.focus) and (self.screen.right.cwd != cwd):
					self.screen.right.chdir(cwd)
			elif key == 'meta o':
				cwd = self.screen.center.focus.cwd.parent
				obj = self.screen.center.focus.get_focus()
				try:
					if stat.S_ISDIR(obj['stat'].st_mode):
						cwd = obj['file']
				except TypeError:
					pass

				if (self.screen.left is not self.screen.center.focus) and (self.screen.left.cwd != cwd):
					self.screen.left.chdir(cwd)

				if (self.screen.right is not self.screen.center.focus) and (self.screen.right.cwd != cwd):
					self.screen.right.chdir(cwd)
			elif key == 'ctrl r':
				self.reload()
			elif key == 'ctrl u':
				(self.screen.center.contents[0], self.screen.center.contents[1]) = (self.screen.center.contents[1], self.screen.center.contents[0])
				self.screen.center.focus_position ^= 1
				self.screen.update_focus()
			elif key == 'ctrl o':
				self.loop.stop()
				input('Press ENTER to continue...')
				self.loop.start()
				os.kill(os.getpid(), signal.SIGWINCH)
				self.reload()
			elif key == 'ctrl q':
				pos = self.screen.center.focus_position ^ 1
				if self.screen.left is self.screen.center.focus:
					if self.screen.show_preview:
						self.screen.show_preview = False
						self.screen.center.contents[pos] = (self.screen.right, self.screen.center.options())
					else:
						self.screen.show_preview = True
						self.screen.center.contents[pos] = (self.screen.preview_panel, self.screen.center.options())
				elif self.screen.right is self.screen.center.focus:
					if self.screen.show_preview:
						self.screen.show_preview = False
						self.screen.center.contents[pos] = (self.screen.left, self.screen.center.options())
					else:
						self.screen.show_preview = True
						self.screen.center.contents[pos] = (self.screen.preview_panel, self.screen.center.options())
				else:
					if self.screen.center.contents[pos][0] == self.screen.left:
						self.screen.show_preview = False
						self.screen.center.contents[self.screen.center.focus_position] = (self.screen.right, self.screen.center.options())
					else:
						self.screen.show_preview = False
						self.screen.center.contents[self.screen.center.focus_position] = (self.screen.left, self.screen.center.options())


				self.screen.update_focus()
				self.reload()
			elif key == 'f7':
				self.screen.command_bar.mkdir(self.screen.center.focus.cwd)
			elif key == 'c':
				self.leader = key
				self.screen.command_bar.set_leader(self.leader)
			elif key == 'r':
				obj = self.screen.center.focus.get_focus()
				try:
					self.screen.command_bar.rename(obj['file'], mode='replace')
				except TypeError:
					pass
			elif key in ('i', 'I'):
				obj = self.screen.center.focus.get_focus()
				try:
					self.screen.command_bar.rename(obj['file'], mode='insert')
				except TypeError:
					pass
			elif key == 'a':
				obj = self.screen.center.focus.get_focus()
				try:
					self.screen.command_bar.rename(obj['file'], mode='append_before')
				except TypeError:
					pass
			elif key == 'A':
				obj = self.screen.center.focus.get_focus()
				try:
					self.screen.command_bar.rename(obj['file'], mode='append_after')
				except TypeError:
					pass
			elif key == '+':
				self.screen.command_bar.tag_glob()
			elif key in ('-', '\\'):
				self.screen.command_bar.untag_glob()
			elif key in (':', '!'):
				self.screen.command_bar.shell()
			elif key == 'f8':
				tagged_files = self.screen.center.focus.get_tagged_files()
				if tagged_files:
					if len(tagged_files) == 1:
						question = f'Delete {tagged_files[0].name}?'
					else:
						question = f'Delete {len(tagged_files)} files/directories?'

					self.screen.center.focus.force_focus()
					self.screen.pile.contents[self.screen.main_area] = (urwid.Overlay(DlgQuestion(self, title='Delete', question=question,
						on_yes=lambda x: self.on_delete(tagged_files, str(self.screen.center.focus.cwd)), on_no=lambda x: self.screen.close_dialog()), self.screen.center,
						'center', max(len(question) + 6, 21),
						'middle', 'pack',
					), self.screen.pile.options())
			elif key == 'f5':
				tagged_files = self.screen.center.focus.get_tagged_files()
				if tagged_files:
					if len(tagged_files) == 1:
						question = f'Copy {tagged_files[0].name} to:'
					else:
						question = f'Copy {len(tagged_files)} files/directories to:'

					if self.screen.center.focus == self.screen.left:
						dest_dir = self.screen.right.cwd
					else:
						dest_dir = self.screen.left.cwd

					self.screen.center.focus.force_focus()
					self.screen.pile.contents[self.screen.main_area] = (urwid.Overlay(DlgCpMv(self, title='Copy', question=question, dest_dir=str(dest_dir),
						on_ok=functools.partial(self.on_copy, tagged_files, str(self.screen.center.focus.cwd)), on_cancel=lambda x: self.screen.close_dialog()), self.screen.center,
						'center', ('relative', 85),
						'middle', 'pack',
					), self.screen.pile.options())
			elif key == 'f6':
				tagged_files = self.screen.center.focus.get_tagged_files()
				if tagged_files:
					if len(tagged_files) == 1:
						question = f'Move {tagged_files[0].name} to:'
					else:
						question = f'Move {len(tagged_files)} files/directories to:'

					if self.screen.center.focus == self.screen.left:
						dest_dir = self.screen.right.cwd
					else:
						dest_dir = self.screen.left.cwd

					self.screen.center.focus.force_focus()
					self.screen.pile.contents[self.screen.main_area] = (urwid.Overlay(DlgCpMv(self, title='Move', question=question, dest_dir=str(dest_dir),
						on_ok=functools.partial(self.on_move, tagged_files, str(self.screen.center.focus.cwd)), on_cancel=lambda x: self.screen.close_dialog()), self.screen.center,
						'center', ('relative', 85),
						'middle', 'pack',
					), self.screen.pile.options())

	def reload(self, focus_path=None, old_focus=None, only_focused=False):
		if old_focus is None:
			if (not only_focused) or (self.screen.center.focus == self.screen.left):
				left_path = focus_path
			else:
				left_path = None

			if (not only_focused) or (self.screen.center.focus == self.screen.right):
				right_path = focus_path
			else:
				right_path = None
		else:
			obj = self.screen.left.get_focus()
			left_path = None
			try:
				if obj['file'] == old_focus:
					left_path = focus_path
			except TypeError:
				pass

			obj = self.screen.right.get_focus()
			right_path = None
			try:
				if obj['file'] == old_focus:
					right_path = focus_path
			except TypeError:
				pass

		self.screen.left.reload(left_path)
		self.screen.right.reload(right_path)

	def do_dirscan(self, files, cwd, on_complete):
		self.screen.center.focus.force_focus()

		q = Queue()
		ev_abort = Event()
		ev_skip = Event()
		dlg = DlgDirscan(self, cwd, q, ev_abort, ev_skip, on_complete)
		self.screen.pile.contents[self.screen.main_area] = (urwid.Overlay(dlg, self.screen.center,
			'center', ('relative', 50),
			'middle', 'pack',
		), self.screen.pile.options())

		fd = self.loop.watch_pipe(dlg.on_pipe_data)
		dlg.fd = fd

		Thread(target=rnr_dirscan, args=(files, cwd, fd, q, self.ev_interrupt, ev_abort, ev_skip)).start()

	def on_finish(self, completed_list, error_list, skipped_list, aborted_list, operation, files, cwd, dest, scan_error, scan_skipped, job_id):
		warnings = [x for x in completed_list if x['message']]
		if scan_error or error_list or scan_skipped or skipped_list or aborted_list or warnings:
			self.screen.center.focus.force_focus()

			dlg = DlgReport(self, completed_list, error_list, skipped_list, aborted_list, operation, files, cwd, dest, scan_error, scan_skipped, job_id)
			self.screen.pile.contents[self.screen.main_area] = (urwid.Overlay(dlg, self.screen.center,
				'center', ('relative', 75),
				'middle', ('relative', 75),
			), self.screen.pile.options())
		else:
			if self.dbfile:
				db = DataBase(self.dbfile)
				db.delete_job(job_id)
				del db

			self.reload()

	def on_delete(self, files, cwd):
		self.screen.close_dialog()
		self.do_dirscan(files, cwd, functools.partial(self.do_delete, files=files, cwd=cwd, job_id=None))

	def do_delete(self, file_list, scan_error, scan_skipped, files, cwd, job_id):
		self.screen.center.focus.force_focus()

		if self.dbfile and (job_id is None):
			db = DataBase(self.dbfile)
			job_id = db.new_job('Delete', file_list, scan_error, scan_skipped, files, cwd)
			del db

		q = Queue()
		ev_skip = Event()
		ev_suspend = Event()
		ev_suspend.set()
		self.suspend.add(ev_suspend)
		ev_abort = Event()
		ev_nodb = Event()
		dlg = DlgDeleteProgress(self, len(file_list), sum((x['lstat'].st_size for x in file_list)), q, ev_skip, ev_suspend, ev_abort, ev_nodb, functools.partial(self.on_finish, operation='Delete', files=files, cwd=cwd, dest=None, scan_error=scan_error, scan_skipped=scan_skipped, job_id=job_id))
		self.screen.pile.contents[self.screen.main_area] = (urwid.Overlay(dlg, self.screen.center,
			'center', ('relative', 75),
			'middle', 'pack',
		), self.screen.pile.options())

		fd = self.loop.watch_pipe(dlg.on_pipe_data)
		dlg.fd = fd

		Thread(target=rnr_delete, args=(file_list, fd, q, ev_skip, ev_suspend, self.ev_interrupt, ev_abort, ev_nodb, self.dbfile, job_id)).start()

	def on_copy(self, files, cwd, dest, on_conflict):
		self.screen.close_dialog()

		path_cwd = Path(cwd)
		path_dest = Path(dest)
		try:
			path_dest = path_dest.expanduser()
		except RuntimeError:
			pass

		if not path_dest.is_absolute():
			path_dest = Path(os.path.normpath(path_cwd / path_dest))

		try:
			if len(files) == 1:
				if path_dest.is_dir():
					if (path_cwd.resolve() == path_dest.resolve()) and (on_conflict in ('overwrite', 'skip')):
						pass
					else:
						self.do_dirscan(files, cwd, functools.partial(self.do_copy, files=files, cwd=cwd, dest=str(path_dest), on_conflict=on_conflict, job_id=None))
				else:
					dest_parent = path_dest.parent
					if not dest_parent.is_dir():
						self.screen.error(f'{str(Path(dest).parent)} is not a directory')
					elif (path_cwd.resolve() == path_dest.resolve()) and (on_conflict in ('overwrite', 'skip')):
						pass
					else:
						self.do_dirscan(files, cwd, functools.partial(self.do_copy, files=files, cwd=cwd, dest=str(path_dest), on_conflict=on_conflict, job_id=None))
			else:
				if not path_dest.is_dir():
					self.screen.error(f'{dest} is not a directory')
				elif (path_cwd.resolve() == path_dest.resolve()) and (on_conflict in ('overwrite', 'skip')):
					pass
				else:
					self.do_dirscan(files, cwd, functools.partial(self.do_copy, cwd=cwd, files=files, dest=str(path_dest), on_conflict=on_conflict, job_id=None))
		except (FileNotFoundError, PermissionError) as e:
			self.screen.error(f'{e.strerror} ({e.errno})')

	def do_copy(self, file_list, scan_error, scan_skipped, files, cwd, dest, on_conflict, job_id):
		self.screen.center.focus.force_focus()

		if self.dbfile and (job_id is None):
			db = DataBase(self.dbfile)
			job_id = db.new_job('Copy', file_list, scan_error, scan_skipped, files, cwd, dest, on_conflict)
			del db

		q = Queue()
		ev_skip = Event()
		ev_suspend = Event()
		ev_suspend.set()
		self.suspend.add(ev_suspend)
		ev_abort = Event()
		ev_nodb = Event()
		dlg = DlgCpMvProgress(self, 'Copy', len(file_list), sum((x['lstat'].st_size for x in file_list)), q, ev_skip, ev_suspend, ev_abort, ev_nodb, functools.partial(self.on_finish, operation='Copy', files=files, cwd=cwd, dest=dest, scan_error=scan_error, scan_skipped=scan_skipped, job_id=job_id))
		self.screen.pile.contents[self.screen.main_area] = (urwid.Overlay(dlg, self.screen.center,
			'center', ('relative', 75),
			'middle', 'pack',
		), self.screen.pile.options())

		fd = self.loop.watch_pipe(dlg.on_pipe_data)
		dlg.fd = fd

		Thread(target=rnr_cpmv, args=('cp', file_list, cwd, dest, on_conflict, fd, q, ev_skip, ev_suspend, self.ev_interrupt, ev_abort, ev_nodb, self.dbfile, job_id)).start()

	def on_move(self, files, cwd, dest, on_conflict):
		self.screen.close_dialog()

		path_cwd = Path(cwd)
		path_dest = Path(dest)
		try:
			path_dest = path_dest.expanduser()
		except RuntimeError:
			pass

		if not path_dest.is_absolute():
			path_dest = Path(os.path.normpath(path_cwd / path_dest))

		try:
			if len(files) == 1:
				if path_dest.is_dir():
					if path_cwd.resolve() == path_dest.resolve():
						pass
					else:
						self.do_dirscan(files, cwd, functools.partial(self.do_move, files=files, cwd=cwd, dest=str(path_dest), on_conflict=on_conflict, job_id=None))
				else:
					dest_parent = path_dest.parent
					if not dest_parent.is_dir():
						self.screen.error(f'{str(Path(dest).parent)} is not a directory')
					elif path_cwd.resolve() == path_dest.resolve():
						pass
					else:
						self.do_dirscan(files, cwd, functools.partial(self.do_move, files=files, cwd=cwd, dest=str(path_dest), on_conflict=on_conflict, job_id=None))
			else:
				if not path_dest.is_dir():
					self.screen.error(f'{dest} is not a directory')
				elif path_cwd.resolve() == path_dest.resolve():
					pass
				else:
					self.do_dirscan(files, cwd, functools.partial(self.do_move, files=files, cwd=cwd, dest=str(path_dest), on_conflict=on_conflict, job_id=None))
		except (FileNotFoundError, PermissionError) as e:
			self.screen.error(f'{e.strerror} ({e.errno})')

	def do_move(self, file_list, scan_error, scan_skipped, files, cwd, dest, on_conflict, job_id):
		self.screen.center.focus.force_focus()

		if self.dbfile and (job_id is None):
			db = DataBase(self.dbfile)
			job_id = db.new_job('Move', file_list, scan_error, scan_skipped, files, cwd, dest, on_conflict)
			del db

		q = Queue()
		ev_skip = Event()
		ev_suspend = Event()
		ev_suspend.set()
		self.suspend.add(ev_suspend)
		ev_abort = Event()
		ev_nodb = Event()
		dlg = DlgCpMvProgress(self, 'Move', len(file_list), sum((x['lstat'].st_size for x in file_list)), q, ev_skip, ev_suspend, ev_abort, ev_nodb, functools.partial(self.on_finish, operation='Move', files=files, cwd=cwd, dest=dest, scan_error=scan_error, scan_skipped=scan_skipped, job_id=job_id))
		self.screen.pile.contents[self.screen.main_area] = (urwid.Overlay(dlg, self.screen.center,
			'center', ('relative', 75),
			'middle', 'pack',
		), self.screen.pile.options())

		fd = self.loop.watch_pipe(dlg.on_pipe_data)
		dlg.fd = fd

		Thread(target=rnr_cpmv, args=('mv', file_list, cwd, dest, on_conflict, fd, q, ev_skip, ev_suspend, self.ev_interrupt, ev_abort, ev_nodb, self.dbfile, job_id)).start()

	def check_pending_jobs(self):
		if not self.dbfile:
			return

		db = DataBase(self.dbfile)
		self.pending_jobs.extend(db.get_jobs())
		del db

		if self.pending_jobs:
			self.show_next_pending_job()

	def show_next_pending_job(self):
		self.screen.center.focus.force_focus()

		pending_job = self.pending_jobs.pop(0)
		dlg = DlgPendingJob(self, pending_job)
		self.screen.pile.contents[self.screen.main_area] = (urwid.Overlay(dlg, self.screen.center,
			'center', ('relative', 75),
			'middle', ('relative', 75),
		), self.screen.pile.options())

	def view(self, filename):
		try:
			file_size = os.stat(filename).st_size
			screen = rnrview.Screen(self, filename, file_size, self.tabsize)
		except OSError:
			return

		self.old_screen = self.screen
		self.screen = screen
		self.loop.widget = self.screen
		self.set_input_rnrview()

	def close_viewer(self, key):
		if self.old_screen:
			self.screen = self.old_screen
			self.old_screen = None
			self.loop.widget = self.screen
			self.set_input_rnr()
			self.reload()
		elif key in ('q', 'Q', 'f10'):
			self.quit()

	def set_input_rnrview(self):
		self.screen.bottom.set_labels(rnrview.Labels)
		self.loop._unhandled_input = functools.partial(rnrview.keypress, self)

	def set_input_rnr(self):
		self.screen.bottom.set_labels(Labels)
		self.loop._unhandled_input = self.keypress

	def quit(self):
		if self.printwd:
			try:
				with open(self.printwd, 'w') as fh:
					fh.write(str(self.screen.center.focus.cwd))
			except (FileNotFoundError, PermissionError):
				pass

		raise urwid.ExitMainLoop()


def main():
	parser = argparse.ArgumentParser()
	parser.add_argument('-V', '--version', action='version', version=f'%(prog)s {__version__}')
	parser.add_argument('-P', '--printwd', help='Print last working directory to specified file', metavar='<file>')
	parser.add_argument('-D', '--database', help='Specify database file to use (default: %(default)s)', metavar='<file>', default=str(DATA_DIR / 'rnr.db'), dest='dbfile')
	parser.add_argument('-n', '--nodb', help='Do not use database', action='store_false', dest='use_db')
	parser.add_argument('-b', '--nocolor', help='Requests to run in black and white', action='store_true', dest='monochrome')
	parser.add_argument('-t', '--tabsize', help='set tab size for viewer (default: %(default)d)', type=int, default=TAB_SIZE)
	parser.add_argument('-d', '--debug', help='activate debug mode', action='store_true')
	args = parser.parse_args()

	if args.debug:
		set_debug_fh(open(Path.home() / 'rnr.log', 'w', buffering=1))

	if args.use_db:
		dbfile = args.dbfile
	else:
		dbfile = None

	app = App(args.printwd, dbfile, args.monochrome, args.tabsize)
	app.run()


if __name__ == '__main__':
	sys.exit(main())

