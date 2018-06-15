#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from setuptools import setup, find_packages

import _universum


def readme():
    with open('README.rst') as f:
        return f.read()

setup(
    name=_universum.__title__,
    version=_universum.__version__,
    description='Continuous Integration Framework',
    long_description=readme(),
    author='Ivan Keliukh, Kateryna Dovgan',
    author_email='k.dovgan@samsung.com',
    license='BSD',
    packages=find_packages(exclude='tests'),
    py_modules=['universum', 'submit', 'poll', 'code_report'],
    entry_points={'console_scripts': [
        'universum = universum:main',
        'universum_submit = submit:main',
        'universum_poll = poll:main',
        'universum_static = code_report:main'
    ]},
    setup_requires=['setuptools'],
    install_requires=[
        'gitpython',
        'mechanize',
        'requests',
        'sh',
        'P4'
    ],
    extras_require={
        'development': [
            'sphinx',
            'sphinx-argparse'
        ],
        'test': [
            'docker',
            'httpretty<=0.8',
            'mock',
            'pytest',
            'pylint',
            'pytest-pylint',
            'sphinx',
            'sphinx-argparse',
            'teamcity-messages',
            'pytest-cov',
            'coverage'
        ]
    }
)
