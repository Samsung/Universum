#!/usr/bin/env python2
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
    packages=find_packages(exclude=['tests', 'tests.*']),
    py_modules=['universum', 'analyzers.pylint', 'analyzers.svace', 'analyzers.uncrustify'],
    entry_points={'console_scripts': [
        'universum = universum:main',
        'universum_pylint = analyzers.pylint:main',
        'universum_svace = analyzers.svace:main',
        'universum_uncrustify = analyzers.uncrustify:main'
    ]},
    python_requires='>=2.7.6, <3',
    setup_requires=['setuptools'],
    install_requires=[
        'glob2',
        'requests',
        'sh',
        'lxml'
    ],
    extras_require={
        'docs': [
            'sphinx',
            'sphinx-argparse',
            'sphinx_rtd_theme'
        ],
        'development': [
            'gitpython',
            'P4',
            'sphinx',
            'sphinx-argparse',
            'sphinx_rtd_theme'
        ],
        'test': [
            'docker',
            'gitpython',
            'httpretty<=0.8',
            'mock',
            'P4',
            'pytest<3.7',
            'pylint<2',
            'pytest-pylint',
            'sphinx',
            'sphinx-argparse',
            'sphinx_rtd_theme',
            'teamcity-messages',
            'pytest-cov',
            'coverage'
        ]
    }
)


if __name__ == "__main__":
    print "Please use 'sudo pip install .' instead of launching this script"
