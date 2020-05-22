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

import sqlite3
import json

from pathlib import Path

from .debug_print import (debug_print, debug_pprint)


class DataBase(object):
	def __init__(self, file):
		self.conn = None

		try:
			self.conn = sqlite3.connect(file)
			self.conn.row_factory = sqlite3.Row

			with self.conn:
				self.conn.executescript('''
					PRAGMA foreign_keys = ON;

					CREATE TABLE IF NOT EXISTS jobs (
						id INTEGER NOT NULL PRIMARY KEY,
						operation TEXT NOT NULL,
						files TEXT NOT NULL,
						cwd TEXT NOT NULL,
						dest TEXT,
						on_conflict TEXT,
						scan_error TEXT,
						scan_skipped TEXT,
						dir_list TEXT,
						rename_dir_stack TEXT,
						skip_dir_stack TEXT,
						status TEXT NOT NULL
					);

					CREATE TABLE IF NOT EXISTS files (
						id INTEGER NOT NULL PRIMARY KEY,
						job_id INTEGER NOT NULL,
						file TEXT NOT NULL,
						status TEXT NOT NULL,
						message TEXT,
						FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
					);
				''')
		except sqlite3.OperationalError:
			pass

	def __del__(self):
		if self.conn is None:
			return

		try:
			self.conn.commit()
			self.conn.close()
		except sqlite3.OperationalError:
			pass

	def new_job(self, operation, file_list, error_list, skipped_list, files, cwd, dest=None, on_conflict=None):
		job_id = None

		if self.conn is None:
			return job_id

		try:
			with self.conn:
				c = self.conn.execute('''SELECT MAX(id) FROM jobs''')
				job_id = c.fetchone()[0] or 0
				job_id += 1
				c.close()
				self.conn.execute('''INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
					job_id,
					operation,
					json.dumps([str(x) for x in files]),
					cwd,
					dest,
					on_conflict,
					json.dumps(error_list),
					json.dumps(skipped_list),
					None,
					None,
					None,
					'IN_PROGRESS',
				))

				c = self.conn.execute('''SELECT MAX(id) FROM files''')
				file_id = c.fetchone()[0] or 0
				file_id += 1
				c.close()
				for file in file_list:
					self.conn.execute('''INSERT INTO files VALUES (?, ?, ?, ?, ?)''', (
						file_id,
						job_id,
						json.dumps(file),
						'TO_DO',
						None,
					))

					file['id'] = file_id
					file['status'] = 'TO_DO'

					file_id += 1
		except sqlite3.OperationalError:
			pass

		return job_id

	def set_file_status(self, file, status, message=None):
		if self.conn is None:
			return

		try:
			with self.conn:
				if message is not None:
					self.conn.execute('''UPDATE files SET status = ?, message = ? WHERE id = ?''', (
						status,
						message,
						file['id'],
					))
				else:
					self.conn.execute('''UPDATE files SET status = ? WHERE id = ?''', (
						status,
						file['id'],
					))

				file['status'] = status
		except sqlite3.OperationalError:
			pass

	def set_job_status(self, job_id, status):
		if self.conn is None:
			return

		try:
			with self.conn:
				self.conn.execute('''UPDATE jobs SET status = ? WHERE id = ?''', (
					status,
					job_id,
				))
		except sqlite3.OperationalError:
			pass

	def delete_job(self, job_id):
		if self.conn is None:
			return

		try:
			with self.conn:
				self.conn.execute('''DELETE FROM jobs WHERE id = ?''', (
					job_id,
				))
		except sqlite3.OperationalError:
			pass

	def set_dir_list(self, job_id, dir_list):
		if self.conn is None:
			return

		try:
			with self.conn:
				self.conn.execute('''UPDATE jobs SET dir_list = ? WHERE id = ?''', (
					json.dumps([{'file': x['file'], 'cur_file': str(x['cur_file']), 'cur_target': str(x['cur_target'])} for x in dir_list]),
					job_id,
				))
		except sqlite3.OperationalError:
			pass

	def get_dir_list(self, job_id):
		dir_list = []

		if self.conn is None:
			return dir_list

		try:
			with self.conn:
				c = self.conn.execute('''SELECT dir_list FROM jobs WHERE id = ?''', (job_id,))
				record = c.fetchone()[0]
				c.close()

				if record:
					for file in json.loads(record):
						file['cur_file'] = Path(file['cur_file'])
						file['cur_target'] = Path(file['cur_target'])
						file['file']['file'] = Path(file['file']['file'])
						file['file']['lstat'] = os.stat_result(file['file']['lstat'])
						dir_list.append(file)
		except sqlite3.OperationalError:
			pass

		return dir_list

	def set_rename_dir_stack(self, job_id, rename_dir_stack):
		if self.conn is None:
			return

		try:
			with self.conn:
				self.conn.execute('''UPDATE jobs SET rename_dir_stack = ? WHERE id = ?''', (
					json.dumps([list(map(str, x)) for x in rename_dir_stack]),
					job_id,
				))
		except sqlite3.OperationalError:
			pass

	def get_rename_dir_stack(self, job_id):
		rename_dir_stack = []

		if self.conn is None:
			return rename_dir_stack

		try:
			with self.conn:
				c = self.conn.execute('''SELECT rename_dir_stack FROM jobs WHERE id = ?''', (job_id,))
				record = c.fetchone()[0]
				c.close()

				if record:
					rename_dir_stack.extend(json.loads(record))
		except sqlite3.OperationalError:
			pass

		return rename_dir_stack

	def set_skip_dir_stack(self, job_id, skip_dir_stack):
		if self.conn is None:
			return

		try:
			with self.conn:
				self.conn.execute('''UPDATE jobs SET skip_dir_stack = ? WHERE id = ?''', (
					json.dumps([str(x) for x in skip_dir_stack]),
					job_id,
				))
		except sqlite3.OperationalError:
			pass

	def get_skip_dir_stack(self, job_id):
		skip_dir_stack = []

		if self.conn is None:
			return skip_dir_stack

		try:
			with self.conn:
				c = self.conn.execute('''SELECT skip_dir_stack FROM jobs WHERE id = ?''', (job_id,))
				record = c.fetchone()[0]
				c.close()

				if record:
					skip_dir_stack.extend(json.loads(record))
		except sqlite3.OperationalError:
			pass

		return skip_dir_stack

	def get_jobs(self):
		jobs = []

		if self.conn is None:
			return jobs

		try:
			with self.conn:
				c = self.conn.execute('''SELECT * FROM jobs''')
				jobs.extend(c.fetchall())
				c.close()
		except sqlite3.OperationalError:
			pass

		return jobs

	def get_file_list(self, job_id):
		file_list = []

		if self.conn is None:
			return file_list

		try:
			with self.conn:
				c = self.conn.execute('''SELECT * FROM files WHERE job_id = ?''', (job_id,))
				for row in c:
					file = json.loads(row['file'])
					file['id'] = row['id']
					file['status'] = row['status']
					file['lstat'] = os.stat_result(file['lstat'])

					file_list.append(file)

				c.close()
		except sqlite3.OperationalError:
			pass

		return file_list

