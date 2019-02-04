Getting started
---------------

Before installing or launching the `Universum`, please make sure your system meets the following
:doc:`prerequisites`.

The main script (`universum.py`) is used for performing all CI-related actions.
If using raw sources, launch Universum via running this script with :doc:`parameters <args>`::

    $ ./universum.py --help


If using a module installed via PyPi, use created ``universum`` command from any suitable directory::

    $ universum --help


In order to use the CI system with a project, a special ``configs.py`` file must be created.
The contents of such file are described on :doc:`configuring` page.

We recommend to place configuration file somewhere inside the project tree.
Its location :doc:`may also be specified <args>` by the `CONFIG_PATH` environment variable.
