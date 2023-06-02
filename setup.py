from setuptools import setup, find_packages

import universum


def readme():
    with open('README.md', encoding="utf-8") as f:
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
    python_requires='>=3.6',
    install_requires=[
        'glob2',
        'requests',
        'sh',
        'lxml',
        'typing-extensions',
        'ansi2html',
        'pyyaml==6.0'
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
            'mypy',
            'types-requests',
            'selenium==3.141',
            'urllib3==1.26.15',  # This is required for selenium-3.141 to work correctly
            'types-PyYAML==6.0'
        ]
    },
    package_data={'': ['*.css', '*.js']}
)


if __name__ == "__main__":
    print("Please use 'sudo pip install .' instead of launching this script")
