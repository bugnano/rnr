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

from .debug_print import (debug_print, debug_pprint)


def recursive_dirscan(dir_, error_list, err, info, fd, q):
	file_list = []

	for file in os.scandir(dir_):
		try:
			lstat = file.stat(follow_symlinks=False)
			info['bytes'] += lstat.st_size
			info['files'] += 1
			if file.is_symlink():
				file_list.append({'file': file.path, 'is_dir': False, 'size': lstat.st_size})
			elif file.is_dir():
				file_list.append({'file': file.path, 'is_dir': True, 'size': lstat.st_size})
				info['current'] = file.path
				try:
					file_list.extend(recursive_dirscan(file, error_list, err, info, fd, q))
				except OSError as e:
					error_list.append({'file': file.path, 'error': f'{e.strerror} ({e.errno})'})
					err.append(file.path)
			else:
				file_list.append({'file': file.path, 'is_dir': False, 'size': lstat.st_size})

			q.put(info.copy())
			os.write(fd, b'x')
		except OSError as e:
			error_list.append({'file': file.path, 'error': f'{e.strerror} ({e.errno})'})
			err.append(file.path)

	return file_list

def dirscan(files, cwd, fd, q):
	file_list = []
	error_list = []
	err = []

	info = {
		'current': cwd,
		'files': 0,
		'bytes': 0,
	}

	for file in files:
		try:
			lstat = file.lstat()
			info['bytes'] += lstat.st_size
			info['files'] += 1
			if file.is_symlink():
				file_list.append({'file': str(file), 'is_dir': False, 'size': lstat.st_size})
			elif file.is_dir():
				file_list.append({'file': str(file), 'is_dir': True, 'size': lstat.st_size})
				info['current'] = str(file)
				try:
					file_list.extend(recursive_dirscan(file, error_list, err, info, fd, q))
				except OSError as e:
					error_list.append({'file': str(file), 'error': f'{e.strerror} ({e.errno})'})
					err.append(str(file))
			else:
				file_list.append({'file': str(file), 'is_dir': False, 'size': lstat.st_size})

			q.put(info.copy())
			os.write(fd, b'x')
		except OSError as e:
			error_list.append({'file': str(file), 'error': f'{e.strerror} ({e.errno})'})
			err.append(str(file))

	if err:
		file_list = [x for x in file_list if x['file'] not in err]

	q.put({'result': (file_list, error_list)})
	os.write(fd, b'x')
	os.close(fd)

