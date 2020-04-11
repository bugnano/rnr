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
import stat

from pathlib import Path

from .utils import (AbortedError, SkippedError)
from .debug_print import (debug_print, debug_pprint)


def rnr_copyfile(cur_file, cur_target, block_size, info, timers, fd, q, ev_skip, ev_suspend, ev_abort):
	with open(cur_file, 'rb') as fh:
		target_fd = os.open(cur_target, os.O_CREAT | os.O_WRONLY | os.O_TRUNC | os.O_EXCL | os.O_DSYNC, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
		try:
			while True:
				t1 = time.monotonic()
				ev_suspend.wait()
				t2 = time.monotonic()
				dt = round(t2 - t1)
				timers['cur_start'] += dt
				timers['start'] += dt

				if ev_abort.is_set():
					raise AbortedError()

				if ev_skip.is_set():
					ev_skip.clear()
					raise SkippedError()

				buf = fh.read(block_size)
				if not buf:
					break

				buffer_length = len(buf)
				bytes_written = 0
				while bytes_written < buffer_length:
					bytes_written += os.write(target_fd, buf[bytes_written:])

				info['cur_bytes'] += bytes_written
				info['bytes'] += bytes_written
				now = time.monotonic()
				if (now - timers['last_write']) > 0.04:
					timers['last_write'] = now
					info['cur_time'] = int(round(now - timers['cur_start']))
					info['time'] = int(round(now - timers['start']))
					q.put(info.copy())
					try:
						os.write(fd, b'\n')
					except OSError:
						pass
		finally:
			os.close(target_fd)

def rnr_copy(files, cwd, dest, fd, q, ev_skip, ev_suspend, ev_abort):
	file_list = sorted(files, key=lambda x: x['file'])
	error_list = []
	skipped_list = []
	completed_list = []

	dest = Path(dest)

	try:
		block_size = max(dest.stat().st_blksize, 131072)
	except (OSError, AttributeError):
		block_size = 131072

	info = {
		'cur_source': '',
		'cur_target': '',
		'cur_size': 0,
		'cur_bytes': 0,
		'cur_time': 0,
		'files': 0,
		'bytes': 0,
		'time': 0,
	}

	timers = {}

	total_bytes = 0
	timers['start'] = time.monotonic()
	timers['last_write'] = timers['start']
	for file in file_list:
		try:
			timers['cur_start'] = time.monotonic()

			t1 = time.monotonic()
			ev_suspend.wait()
			t2 = time.monotonic()
			dt = round(t2 - t1)
			timers['cur_start'] += dt
			timers['start'] += dt

			if ev_abort.is_set():
				raise AbortedError()

			if ev_skip.is_set():
				ev_skip.clear()
				raise SkippedError()

			cur_file = Path(file['file'])
			rel_file = cur_file.relative_to(cwd)
			cur_target = dest / rel_file
			info['cur_source'] = str(rel_file)
			info['cur_target'] = str(cur_target)
			info['cur_size'] = file['size']
			info['cur_bytes'] = 0

			now = time.monotonic()
			if (now - timers['last_write']) > 0.04:
				timers['last_write'] = now
				info['cur_time'] = int(round(now - timers['cur_start']))
				info['time'] = int(round(now - timers['start']))
				q.put(info.copy())
				try:
					os.write(fd, b'\n')
				except OSError:
					pass

			if cur_file.parent.resolve() == cur_target.parent.resolve():
				raise SkippedError()

			try:
				parent_dir = cur_target.resolve().parent

				in_error = False
				if file['is_symlink']:
					os.symlink(os.readlink(cur_file), cur_target)
				elif file['is_dir']:
					os.makedirs(cur_target)
				elif file['is_file']:
					rnr_copyfile(cur_file, cur_target, block_size, info, timers, fd, q, ev_skip, ev_suspend, ev_abort)
				else:
					in_error = True
					error_list.append({'file': file['file'], 'error': f'{cur_file.name} is a special file'})

				if not in_error:
					parent_fd = os.open(parent_dir, 0)
					try:
						os.fsync(parent_fd)
					finally:
						os.close(parent_fd)

					completed_list.append(file['file'])
			except OSError as e:
				error_list.append({'file': file['file'], 'error': f'{e.strerror} ({e.errno})'})
		except AbortedError as e:
			break
		except SkippedError as e:
			skipped_list.append(file['file'])

		total_bytes += file['size']
		info['bytes'] = total_bytes
		info['files'] += 1

	q.put({'result': completed_list, 'error': error_list, 'skipped': skipped_list})
	try:
		os.write(fd, b'\n')
	except OSError:
		pass
	os.close(fd)

