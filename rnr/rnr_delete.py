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
import errno

from pathlib import Path

from .database import DataBase
from .utils import (InterruptError, AbortedError, SkippedError)
from .debug_print import (debug_print, debug_pprint)


def rnr_delete(files, fd, q, ev_skip, ev_suspend, ev_interrupt, ev_abort, ev_nodb, dbfile, job_id):
	if dbfile:
		db = DataBase(dbfile)

	file_list = sorted(files, key=lambda x: x['file'].replace(os.sep, '\0'), reverse=True)
	error_list = [{'file': x['file'], 'message': x['message']} for x in file_list if x['status'] == 'ERROR']
	skipped_list = [{'file': x['file'], 'message': x['message']} for x in file_list if x['status'] == 'SKIPPED']
	completed_list = [{'file': x['file'], 'message': x['message']} for x in file_list if x['status'] == 'DONE']
	aborted_list = []

	info = {
		'current': '',
		'files': 0,
		'bytes': 0,
		'time': 0,
	}

	timers = {}

	timers['start'] = time.monotonic()
	timers['last_write'] = timers['start']
	for i_file, file in enumerate(file_list):
		try:
			if ev_interrupt.is_set():
				raise InterruptError()

			if dbfile and ev_nodb.is_set():
				db.delete_job(job_id)
				del db
				dbfile = None

			t1 = time.monotonic()
			ev_suspend.wait()
			t2 = time.monotonic()
			timers['start'] += round(t2 - t1)

			if ev_abort.is_set():
				raise AbortedError()

			if ev_skip.is_set():
				ev_skip.clear()
				raise SkippedError('ev_skip')

			if file['status'] in ('DONE', 'ERROR', 'SKIPPED'):
				raise SkippedError('no_log')

			info['current'] = file['file']

			now = time.monotonic()
			if (now - timers['last_write']) > 0.05:
				timers['last_write'] = now
				info['time'] = int(round(now - timers['start']))
				q.put(info.copy())
				try:
					os.write(fd, b'\n')
				except OSError:
					pass

			try:
				if dbfile:
					db.set_file_status(file, 'IN_PROGRESS')

				parent_dir = Path(file['file']).resolve().parent

				if file['is_dir']:
					os.rmdir(file['file'])
				else:
					os.remove(file['file'])

				parent_fd = os.open(parent_dir, 0)
				try:
					os.fsync(parent_fd)
				finally:
					os.close(parent_fd)

				completed_list.append({'file': file['file'], 'message': ''})
				if dbfile:
					db.set_file_status(file, 'DONE', '')
			except OSError as e:
				if e.errno == errno.ENOENT:
					completed_list.append({'file': file['file'], 'message': ''})
					if dbfile:
						db.set_file_status(file, 'DONE', '')
				else:
					message = f'{e.strerror} ({e.errno})'
					error_list.append({'file': file['file'], 'message': message})
					if dbfile:
						db.set_file_status(file, 'ERROR', message)

			if dbfile:
				db.set_job_status(job_id, 'DONE')
		except InterruptError as e:
			break
		except AbortedError as e:
			aborted_list.extend([{'file': x['file'], 'message': ''} for x in file_list[i_file:]])
			if dbfile:
				db.set_job_status(job_id, 'ABORTED')
			break
		except SkippedError as e:
			if str(e) == 'no_log':
				if file['status'] == 'ERROR':
					error_list.append({'file': file['file'], 'message': file['message']})
				elif file['status'] == 'SKIPPED':
					skipped_list.append({'file': file['file'], 'message': file['message']})
				else:
					completed_list.append({'file': file['file'], 'message': ''})
					if dbfile and file['status'] != 'DONE':
						db.set_file_status(file, 'DONE', '')
			else:
				message = str(e)
				if message == 'ev_skip':
					message = ''

				skipped_list.append({'file': file['file'], 'message': message})
				if dbfile:
					db.set_file_status(file, 'SKIPPED', message)

		info['bytes'] += file['lstat'].st_size
		info['files'] += 1

	q.put({'result': completed_list, 'error': error_list, 'skipped': skipped_list, 'aborted': aborted_list})
	try:
		os.write(fd, b'\n')
	except OSError:
		pass
	os.close(fd)

