import setuptools

from rrr import __version__

with open('README.md', 'r') as fh:
	long_description = fh.read()

setuptools.setup(
	name='rrr',
	version=__version__,
	author='Franco Bugnano',
	description='The rrr file manager',
	long_description=long_description,
	long_description_content_type='text/markdown',
	url='https://github.com/bugnano/rrr',
	packages=setuptools.find_packages(),
	entry_points={
		'console_scripts': [
			'rrr=rrr:main',
		],
	},
	classifiers=[
		'Development Status :: 2 - Pre-Alpha',
		'Environment :: Console :: Curses',
		'Intended Audience :: End Users/Desktop',
		'Intended Audience :: System Administrators',
		'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
		'Natural Language :: English',
		'Operating System :: POSIX :: Linux',
		'Programming Language :: Python :: 3',
		'Topic :: Desktop Environment :: File Managers',
		'Topic :: System',
		'Topic :: System :: Systems Administration',
		'Topic :: Utilities',
	],
	python_requires='>=3.6',
	install_requires=[
		'urwid',
		'fuzzyfinder',
	],
)

