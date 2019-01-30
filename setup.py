#!/usr/bin/env python
try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

import ast
import os
import re

os.chdir(os.path.dirname(os.path.abspath(__file__)))

with open('src/xymon_client/__init__.py') as fobj:
	version = ast.literal_eval(
		re.compile(r'__version__\s*=\s*(.*)')
		.search(fobj.read()).group(1)
	)





setup(
	name='xymon_client',
	version=version,
	description='a minimalist Xymon client library in Python',
	author='Romain Dartigues',
	license='BSD 3-Clause License',
	keywords=('bb', 'BigBrother', 'xymon'),
	url='https://github.com/romain-dartigues/python-xymon-client',
	classifiers=(
		'Development Status :: 4 - Beta',
		'Environment :: Plugins',
		'Intended Audience :: Developers',
		'License :: OSI Approved :: BSD License',
		'Natural Language :: English',
		'Operating System :: OS Independent',
		'Programming Language :: Python :: 2.7',
		'Programming Language :: Python :: 3',
		'Topic :: Software Development :: Libraries :: Python Modules',
		'Topic :: System :: Monitoring',
	),
	package_dir={'': 'src'},
	packages=(
		'xymon_client',
	),
	entry_points={
		'console_scripts': [
			'xymon-client = xymon_client.__main__:main',
		],
	},
)
