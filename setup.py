import setuptools

from rnr import __version__

with open('README.md', 'r') as fh:
	long_description = fh.read()

with open('requirements.txt', 'r') as fh:
	requirements = [x.strip() for x in fh if x.strip()]

setuptools.setup(
	name='rnr',
	version=__version__,
	author='Franco Bugnano',
	author_email="franco@bugnano.it",
	description="The RNR File Manager (RNR's Not Ranger)",
	long_description=long_description,
	long_description_content_type='text/markdown',
	url='https://github.com/bugnano/rnr',
	packages=setuptools.find_packages(),
	data_files=[
		('share/rnr', [
			'rnr.fish',
			'rnr.sh',
		])
	],
	entry_points={
		'console_scripts': [
			'rnr=rnr:main',
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
	install_requires=requirements,
)

