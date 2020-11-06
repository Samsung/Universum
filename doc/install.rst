Installation
============

Currently `Universum` requires the following prerequisites:

* OS Linux
* Python version 3.7 or greater
* Pip version 9.0 or greater

Use ``{pip} install -U universum`` to install latest default `Universum` to the system.
This will also install the following modules:

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
version, as we recommend :mod:`pip` version not lower than 19.0 for installing the :mod:`p4python`. Pip older than
version 19.0 uses FTP to install :mod:`p4python`, while the latter versions use HTTP.


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
