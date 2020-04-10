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

from pathlib import Path

from .debug_print import (debug_print, debug_pprint)


def rnr_copy(files, cwd, dest, fd, q, ev_skip, ev_suspend, ev_abort):
	file_list = sorted(files, key=lambda x: x['file'])
	error_list = []
	skipped_list = []
	completed_list = []

	dest = Path(dest)

	info = {
		'cur_source': '',
		'cur_target': '',
		'cur_size': 0,
		'cur_bytes': 0,
		'files': 0,
		'bytes': 0,
		'time': 0,
	}

	total_bytes = 0
	time_start = time.monotonic()
	last_write = time_start
	for file in file_list:
		time.sleep(0.5)

		t1 = time.monotonic()
		ev_suspend.wait()
		t2 = time.monotonic()
		time_start += round(t2 - t1)

		if ev_abort.is_set():
			break

		if ev_skip.is_set():
			ev_skip.clear()

			skipped_list.append(file['file'])

			total_bytes += file['size']
			info['bytes'] = total_bytes
			info['files'] += 1
			continue

		cur_file = Path(file['file'])
		rel_file = cur_file.relative_to(cwd)
		cur_target = dest / rel_file
		info['cur_source'] = rel_file
		info['cur_target'] = cur_target
		info['cur_bytes'] = 0

		now = time.monotonic()
		if (now - last_write) > 0.04:
			last_write = now
			info['time'] = int(round(now - time_start))
			q.put(info.copy())
			try:
				os.write(fd, b'\n')
			except OSError:
				pass

		if cur_file.parent.resolve() == cur_target.parent.resolve():
			skipped_list.append(file['file'])

			total_bytes += file['size']
			info['bytes'] = total_bytes
			info['files'] += 1
			continue

		try:
			parent_dir = cur_target.resolve().parent

			if file['is_symlink']:
				os.symlink(os.readlink(cur_file), cur_target)
			elif file['is_dir']:
				pass
			elif file['is_file']:
				pass
			else:
				pass

			parent_fd = os.open(parent_dir, 0)
			try:
				os.fsync(parent_fd)
			finally:
				os.close(parent_fd)

			completed_list.append(file['file'])
		except OSError as e:
			error_list.append({'file': file['file'], 'error': f'{e.strerror} ({e.errno})'})

		total_bytes += file['size']
		info['bytes'] = total_bytes
		info['files'] += 1

	q.put({'result': completed_list, 'error': error_list, 'skipped': skipped_list})
	try:
		os.write(fd, b'\n')
	except OSError:
		pass
	os.close(fd)

