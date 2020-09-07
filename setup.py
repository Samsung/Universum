from setuptools import setup, find_packages

import universum


def readme():
    with open('README.md') as f:
        return f.read()


docs = (
    'sphinx',
    'sphinx-argparse',
    'sphinx_rtd_theme'
)

vcs = (
    'gitpython>=3.0.5',
    'p4python>=2019.1',
    'pygithub',
    'cryptography'
)

setup(
    name=universum.__title__,
    version=universum.__version__,
    description='Unifier of Continuous Integration',
    long_description=readme(),
    long_description_content_type='text/markdown',
    author='Ivan Keliukh <i.keliukh@samsung.com>, Kateryna Dovgan <k.dovgan@samsung.com>',
    license='BSD',
    packages=find_packages(exclude=['tests', 'tests.*']),
    py_modules=['universum'],
    python_requires='>=3.7',
    setup_requires=['setuptools'],
    install_requires=[
        'glob2',
        'requests',
        'sh',
        'lxml',
        'six',
        'typing-extensions'
    ],
    extras_require={
        'docs': [docs],
        'development': [docs, vcs],
        'test': [
            docs,
            vcs,
            'docker',
            'httpretty',
            'mock',
            'pytest',
            'pylint',
            'pytest-pylint',
            'teamcity-messages',
            'pytest-cov',
            'coverage'
        ]
    }
)


if __name__ == "__main__":
    print("Please use 'sudo pip install .' instead of launching this script")
