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

