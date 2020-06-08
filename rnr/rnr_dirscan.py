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

import time

from .debug_print import (debug_print, debug_pprint)


def recursive_dirscan(dir_, file_list, error_list, skipped_list, info, last_write, fd, q, ev_interrupt, ev_abort, ev_skip):
	files = []
	errors = []
	old_files = info['files']
	old_bytes = info['bytes']

	for file in os.scandir(dir_):
		if ev_interrupt.is_set():
			return False

		if ev_abort.is_set():
			return False

		if ev_skip.is_set():
			ev_skip.clear()
			info['files'] = old_files
			info['bytes'] = old_bytes
			skipped_list.append({'file': dir_, 'message': ''})
			return False

		try:
			lstat = file.stat(follow_symlinks=False)
			info['current'] = dir_
			info['files'] += 1
			info['bytes'] += lstat.st_size
			if file.is_symlink():
				files.append({'file': file.path, 'is_dir': False, 'is_symlink': True, 'is_file': False, 'lstat': lstat, 'status': 'TO_DO', 'message': ''})
			elif file.is_dir():
				files.append({'file': file.path, 'is_dir': True, 'is_symlink': False, 'is_file': False, 'lstat': lstat, 'status': 'TO_DO', 'message': ''})
				if not recursive_dirscan(file.path, file_list, error_list, skipped_list, info, last_write, fd, q, ev_interrupt, ev_abort, ev_skip):
					files.pop()
					info['files'] -= 1
					info['bytes'] -= lstat.st_size

			else:
				files.append({'file': file.path, 'is_dir': False, 'is_symlink': False, 'is_file': file.is_file(), 'lstat': lstat, 'status': 'TO_DO', 'message': ''})

			now = time.monotonic()
			if (now - last_write[0]) > 0.05:
				last_write[0] = now
				q.put(info.copy())
				try:
					os.write(fd, b'\n')
				except OSError:
					pass
		except OSError as e:
			errors.append({'file': file.path, 'message': f'{e.strerror} ({e.errno})'})

	file_list.extend(files)
	error_list.extend(errors)

	return True

def rnr_dirscan(files, cwd, fd, q, ev_interrupt, ev_abort, ev_skip):
	file_list = []
	error_list = []
	skipped_list = []

	info = {
		'current': cwd,
		'files': 0,
		'bytes': 0,
	}

	last_write = [time.monotonic()]
	for file in files:
		if ev_interrupt.is_set():
			break

		if ev_abort.is_set():
			break

		if ev_skip.is_set():
			ev_skip.clear()
			del file_list[:]
			del error_list[:]
			del skipped_list[:]
			info['files'] = 0
			info['bytes'] = 0
			skipped_list.append({'file': cwd, 'message': ''})
			break

		try:
			lstat = file.lstat()
			info['current'] = cwd
			info['files'] += 1
			info['bytes'] += lstat.st_size
			if file.is_symlink():
				file_list.append({'file': str(file), 'is_dir': False, 'is_symlink': True, 'is_file': False, 'lstat': lstat, 'status': 'TO_DO', 'message': ''})
			elif file.is_dir():
				file_list.append({'file': str(file), 'is_dir': True, 'is_symlink': False, 'is_file': False, 'lstat': lstat, 'status': 'TO_DO', 'message': ''})
				if not recursive_dirscan(str(file), file_list, error_list, skipped_list, info, last_write, fd, q, ev_interrupt, ev_abort, ev_skip):
					file_list.pop()
					info['files'] -= 1
					info['bytes'] -= lstat.st_size
			else:
				file_list.append({'file': str(file), 'is_dir': False, 'is_symlink': False, 'is_file': file.is_file(), 'lstat': lstat, 'status': 'TO_DO', 'message': ''})

			now = time.monotonic()
			if (now - last_write[0]) > 0.05:
				last_write[0] = now
				q.put(info.copy())
				try:
					os.write(fd, b'\n')
				except OSError:
					pass
		except OSError as e:
			error_list.append({'file': str(file), 'message': f'{e.strerror} ({e.errno})'})

	old_file_list = file_list[:]
	if error_list:
		err = [x['file'] for x in error_list]
		file_list = [x for x in file_list if x['file'] not in err]

	q.put({'result': file_list, 'error': error_list, 'skipped': skipped_list})
	try:
		os.write(fd, b'\n')
	except OSError:
		pass
	os.close(fd)

