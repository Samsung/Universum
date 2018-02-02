Project 'Universum'
===================


.. Please see the full HTML version of documentation here: doc/_build/html/index.html


Project `Universum` is a continuous integration framework, containing
a collection of functions that simplify implementation of the
automatic build, testing, static analysis and other steps.
The goal of this project is to provide unified approach for adding continuous integration
to any project. It currently supports Perforce, Swarm and TeamCity.

Sometimes `Universum` system can be referred to as the framework or just CI.


Usage
-----

Before launching the `Universum`, please make sure your system meets the following
:doc:`prerequisites`.

The main script ``universum.py`` is used for performing all CI-related
actions. Launch it with ``--help`` parameter to obtain information on
:doc:`all supported options <args>`::

    $ ./universum.py --help

In order to use the CI system with a project, a special ``configs.py`` file
must be created. We recommend to place it somewhere inside the project 
tree. Its location is specified by the `CONFIG_PATH` environment variable.

.. note::

    Currently the CI system is maintained in two separate branches: `DEV` and `MAIN`.
    We recommend to use `MAIN` branch in production.


Examples
--------

The sample project can be found in the `examples` directory.
This sample project consists of the following files:

#. `basic_build_script.sh` - sort of build script, which simulates
   success and failure builds. This shell script is referred by 
   the configuration files
#. `basic_config.py` - sample configuration file for the project,
   displaying most crucial :doc:`configuring features <configuring>`
#. `if_env_set_config.py` - another configuration file, demonstrating
   configuration filtering

The example of using `Universum` system can be launched by ``run_basic_example.sh``
shell script, like follows::

    $ ./run_basic_example.sh

    Run using 'basic_config.py'

    1. Preparing repository
    |   1.1. Copying sources to working directory
    |      └ [Success]
    ... lots of output ...

    Run using 'if_env_set_config.py'

    1. Preparing repository
    |   1.1. Copying sources to working directory
    |      └ [Success]
    ... lots of output ...

You can inspect this basic sample to understand the using of the CI system.

The detailed description of project configuration can be found on a :doc:`configuring` section.
