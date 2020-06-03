Getting started
---------------

Before installing or launching the `Universum`, please make sure your system meets the following
:doc:`prerequisites`.

The main module (`universum`) is used for performing all CI-related actions.
If using raw sources, launch Universum from project root via running main module with :doc:`parameters <args>`::

    $ python3.7 -m universum --help

If using a module installed via PyPi, use the same command from any suitable directory.

In order to use the CI system with a project, a special ``configs.py`` file must be created.
The contents of such file are described on :doc:`configuring` page.

We recommend to place configuration file somewhere inside the project tree.
Its location `may also be specified <args.html#Configuration\ execution>`__ by the `CONFIG_PATH` environment variable.
