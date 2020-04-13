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
import errno
import shutil

from pathlib import Path

from .utils import (AbortedError, SkippedError)
from .debug_print import (debug_print, debug_pprint)


def rnr_copyfile(cur_file, cur_target, file_size, block_size, info, timers, fd, q, ev_skip, ev_suspend, ev_abort):
	with open(cur_file, 'rb') as fh:
		target_fd = os.open(cur_target, os.O_CREAT | os.O_WRONLY | os.O_TRUNC | os.O_EXCL | os.O_DSYNC, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
		try:
			if file_size > 0:
				os.posix_fallocate(target_fd, 0, file_size)

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

def rnr_copy(files, cwd, dest, on_conflict, fd, q, ev_skip, ev_suspend, ev_abort):
	file_list = sorted(files, key=lambda x: x['file'])
	error_list = []
	skipped_list = []
	completed_list = []
	dir_list = []

	dest = Path(dest)

	try:
		block_size = max(dest.lstat().st_blksize, 131072)
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

	dir_stack = []

	if not (dest.exists() and stat.S_ISDIR(dest.lstat().st_mode)):
		cur_file = Path(file_list[0]['file'])
		rel_file = cur_file.relative_to(cwd)
		cur_target = dest / rel_file

		dir_stack.append((cur_target, dest))

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

			while dir_stack:
				(old_target, new_target) = dir_stack[-1]
				if cur_target == old_target:
					cur_target = new_target
					debug_print(f'cur_target (1): {cur_target}')
					break
				elif old_target in cur_target.parents:
					cur_target = Path(str(cur_target).replace(str(old_target), str(new_target)))
					debug_print(f'cur_target (2): {cur_target}')
					break
				else:
					dir_stack.pop()
					debug_print(f'pop')

			info['cur_source'] = str(rel_file)
			info['cur_target'] = str(cur_target)
			info['cur_size'] = file['lstat'].st_size
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

			try:
				parent_dir = cur_target.resolve().parent

				warning = ''
				if cur_target.exists():
					target_is_dir = stat.S_ISDIR(cur_target.lstat().st_mode)
					if on_conflict == 'overwrite':
						if not (file['is_dir'] and target_is_dir):
							if cur_file.resolve() == cur_target.resolve():
								raise SkippedError('Same file')

							if target_is_dir:
								os.rmdir(cur_target)
								warning = f'Overwrite'
							else:
								os.remove(cur_target)
								warning = f'Overwrite'
					elif on_conflict == 'rename_existing':
						if not (file['is_dir'] and target_is_dir):
							i = 0
							name = cur_target.name
							existing_target = cur_target
							while existing_target.exists():
								new_name = f'{name}.rnrsave{i}'
								existing_target = existing_target.parent / new_name
								i += 1

							os.rename(cur_target, existing_target)
							warning = f'Renamed to {existing_target.name}'
					elif on_conflict == 'rename_copy':
						if not (file['is_dir'] and target_is_dir):
							i = 0
							name = cur_target.name
							existing_target = cur_target
							while cur_target.exists():
								new_name = f'{name}.rnrnew{i}'
								cur_target = cur_target.parent / new_name
								i += 1

							warning = f'Renamed to {cur_target.name}'
							if file['is_dir']:
								dir_stack.append((existing_target, cur_target))
					else:
						if not (file['is_dir'] and target_is_dir):
							if cur_file.resolve() == cur_target.resolve():
								raise SkippedError('Same file')

							raise SkippedError('Target exists')

				in_error = False
				if file['is_symlink']:
					os.symlink(os.readlink(cur_file), cur_target)
				elif file['is_dir']:
					os.makedirs(cur_target, exist_ok=True)
					dir_list.append({'file': file, 'target': cur_target})
				elif file['is_file']:
					rnr_copyfile(cur_file, cur_target, file['lstat'].st_size, block_size, info, timers, fd, q, ev_skip, ev_suspend, ev_abort)
				else:
					in_error = True
					error_list.append({'file': file['file'], 'error': f'Special file'})

				if not in_error:
					if not file['is_dir']:
						try:
							os.lchown(cur_target, file['lstat'].st_uid, file['lstat'].st_gid)
						except OSError as e:
							if e.errno == errno.EPERM:
								try:
									os.lchown(cur_target, -1, file['lstat'].st_gid)
								except OSError as e:
									if e.errno == errno.EPERM:
										pass
									else:
										raise
							else:
								raise

						shutil.copystat(cur_file, cur_target, follow_symlinks=False)

					parent_fd = os.open(parent_dir, 0)
					try:
						os.fsync(parent_fd)
					finally:
						os.close(parent_fd)

					completed_list.append({'file': file['file'], 'warning': warning})
			except OSError as e:
				error_list.append({'file': file['file'], 'error': f'{e.strerror} ({e.errno})'})
		except AbortedError as e:
			break
		except SkippedError as e:
			skipped_list.append({'file': file['file'], 'why': str(e)})

		total_bytes += file['lstat'].st_size
		info['bytes'] = total_bytes
		info['files'] += 1

	for entry in reversed(dir_list):
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

			file = entry['file']
			cur_target = entry['target']
			cur_file = Path(file['file'])
			rel_file = cur_file.relative_to(cwd)
			info['cur_source'] = str(rel_file)
			info['cur_target'] = str(cur_target)
			info['cur_size'] = file['lstat'].st_size
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

			try:
				parent_dir = cur_target.resolve().parent

				try:
					os.lchown(cur_target, file['lstat'].st_uid, file['lstat'].st_gid)
				except OSError as e:
					if e.errno == errno.EPERM:
						try:
							os.lchown(cur_target, -1, file['lstat'].st_gid)
						except OSError as e:
							if e.errno == errno.EPERM:
								pass
							else:
								raise
					else:
						raise

				shutil.copystat(cur_file, cur_target, follow_symlinks=False)

				parent_fd = os.open(parent_dir, 0)
				try:
					os.fsync(parent_fd)
				finally:
					os.close(parent_fd)
			except OSError as e:
				error_list.append({'file': file['file'], 'error': f'{e.strerror} ({e.errno})'})
		except AbortedError as e:
			break
		except SkippedError as e:
			skipped_list.append({'file': file['file'], 'why': str(e)})

	q.put({'result': completed_list, 'error': error_list, 'skipped': skipped_list})
	try:
		os.write(fd, b'\n')
	except OSError:
		pass
	os.close(fd)

