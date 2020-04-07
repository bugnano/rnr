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


def delete(files, fd, q, ev_skip, ev_suspend, ev_abort):
	file_list = sorted(files, key=lambda x: x['file'], reverse=True)
	error_list = []
	skipped_list = []

	info = {
		'current': '',
		'files': 0,
		'bytes': 0,
		'time': 0,
	}

	time_start = time.monotonic()
	for file in file_list:
		t1 = time.monotonic()
		ev_suspend.wait()
		t2 = time.monotonic()
		time_start += t2 - t1

		if ev_abort.is_set():
			break

		if ev_skip.is_set():
			ev_skip.clear()
			skipped_list.append(file['file'])
			continue

		info['current'] = file['file']
		info['files'] += 1
		info['bytes'] += file['size']
		info['time'] = int(round(time.monotonic() - time_start))

		q.put(info.copy())
		try:
			os.write(fd, b'\n')
		except OSError:
			pass

		try:
			if file['is_dir']:
				#os.rmdir(file['file'])
				pass
			else:
                #os.remove(file['file'])
				pass
		except OSError as e:
			error_list.append({'file': file['file'], 'error': f'{e.strerror} ({e.errno})'})

	q.put({'result': file_list, 'error': error_list, 'skipped': skipped_list})
	try:
		os.write(fd, b'\n')
	except OSError:
		pass
	os.close(fd)

