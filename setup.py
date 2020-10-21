from setuptools import setup, find_packages

import universum


def readme():
    with open('README.md') as f:
        return f.read()


p4 = ('pip>=19', 'p4python>=2019.1')

git = 'gitpython>=3.0.5'

github = (git, 'cryptography', 'pygithub')

vcs = p4 + github

docs = ('sphinx', 'sphinx-argparse', 'sphinx_rtd_theme')  # This extra is required for RTD to generate documentation

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
    install_requires=[
        'glob2',
        'requests',
        'sh',
        'lxml',
        'typing-extensions'
    ],
    extras_require={
        'p4': [p4],
        'git': [git],
        'github': [github],
        'docs': [docs],
        'test': [
            vcs,
            docs,
            'docker',
            'httpretty',
            'mock',
            'pytest',
            'pylint',
            'pytest-pylint',
            'teamcity-messages',
            'pytest-cov',
            'coverage',
            'mypy'
        ]
    }
)


if __name__ == "__main__":
    print("Please use 'sudo pip install .' instead of launching this script")
