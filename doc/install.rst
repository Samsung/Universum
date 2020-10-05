Installation
============

Currently `Universum` requires the following prerequisites:

* OS Linux
* Python version 3.7 or greater
* Pip version 9.0 or greater

Use ``{pip} install -U universum`` to install latest default `Universum` to the system.
This will also install following modules:

* :mod:`glob2`
* :mod:`requests`
* :mod:`sh`
* :mod:`lxml`
* :mod:`typing-extensions`


VCS-related extras
------------------

Perforce
~~~~~~~~

Before installing `Universum` for Perforce, make sure to install `P4 CLI` (see `official installation manual
<https://www.perforce.com/manuals/p4sag/Content/P4SAG/install.linux.packages.install.html>`__ for details)

To install `Universum` for Perfoce, use ``{pip} install -U universum[p4]``. This will update :mod:`pip` to latest
version, as installing :mod:`p4python` requires :mod:`pip` version not lower then 19.0.


Git
~~~

Before installing `Universum` for Git, make sure to install `Git` client (use ``sudo apt-get install git``).
Then use ``{pip} install -U universum[git]``, that will also install :mod:`gitpython` module for Python.


GitHub
~~~~~~

For :doc:`GitHub Handler <github_handler>`, use ``{pip} install -U universum[github]``, that will install
:mod:`pygithub` and :mod:`cryptography` modules for Python (as :mod:`cryptography` is used for GitHub App token
calculation).

Using `Universum` with ``github`` VCS type also requires `Git` client (use ``sudo apt-get install git``).


Developer extras
----------------

.. note::

    These extras are used for `Universum` development purposes. *Using* `Universum` does not require any of these.

Although it is possible to install these extras from PyPI, it might be more convenient to checkout the `Universum`
branch you are currently working in, change working directory to project root and run a ``{pip} install -U .`` from
there for more flexibility.


Documentation
~~~~~~~~~~~~~

To be able to generate documentation locally (via ``make doc_clean && make doc`` command),
use ``{pip} install -U .[docs]``. This will install the following Python modules:

* :mod:`sphinx` module for Python
* :mod:`sphinx-argparse` extension for `Sphinx`
* :mod:`sphinx_rtd_theme` extension for `Sphinx`


Testing
~~~~~~~

Testing `Universum` locally requires manual installation of Docker (see `official installation manual
<https://docs.docker.com/engine/installation/linux/ubuntu/#install-using-the-repository>`__ for details), and then
building docker images, used in tests (can be done via ``make images`` command, or ``make rebuild`` if images
must be updated skipping tests).

Running ``{pip} install -U .[test]`` will not only add all modules for generating documentation, but will also add
follosing Python modules:

* :mod:`pytest`
* :mod:`pylint`
* :mod:`docker`
* :mod:`httpretty`
* :mod:`mock`

This will allow to run `Universum` tests using ``pytest`` (via ``pytest`` command with any parameters required).
Commnd ``make test`` will run all the tests and collect coverage; it will also rebuild the documentation and run
all doctests.
