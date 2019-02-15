Other usage examples
====================

This page contains some examples of Python scripts using Universum.


Export Perforce repository to Git
---------------------------------

Here's an example script that ports certain directory with commit history
from Helix Perforce (P4) repository to Git. It sequentially reproduces directory state
for each submitted CL, and submits this repository state to Git using the same commit description.

.. note::
    To port the whole repository you just have to set Perforce source directory
    and Git destination directory to repository root


Command line description
~~~~~~~~~~~~~~~~~~~~~~~~

--p4-port           Source Perforce repository; format equals to Perforce `P4PORT`
                    environment variable and usually looks like ``example.com:1666``
--p4-user           Perforce account used to download (sync) files from Perforce server4
--p4-password       Corresponding password for ``--p4-user``
--p4-client         Name of a disposable client (workspace) to be created in process;
                    this client will be deleted after the script finishes its work
--p4-depot-path     Particular folder in source Perforce repository to be ported;
                    should be provided in Perforce-specific format, e.g. ``//depot/path/...``
--p4-client-root    Local folder, where the source commits will be downloaded to;
                    should be absolute path; should be anywhere inside destination Git repository
--git-repo          Destination Git repository; should be absolute path; repository should already exist
--git-user          Git account used to commit ported changes
--git-email         Mandatory Git parameter for committer; should correspond to ``--git-user``

.. note::
    ``--p4-client-root`` should not necessarily equal ``--git-repo``;
    it just has to be somewhere inside repository


Preconditions
~~~~~~~~~~~~~

* Git repository already exists (e.g. is cloned from remote or created via ``git init``)

* All required changes in Perforce are made in one source folder (``--depot-path``)

* Git account used for porting is authorized to commit

* Perforce account used for porting is authorized to download (sync) source folder

* Perforce client does not exist

* 'Client root' leads to the local folder inside Git repository


Script
~~~~~~

.. literalinclude:: ../examples/p4_to_git.py
    :language: python
    :linenos:


Possible script modifications
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In this example commit messages are preserved, but all changes are committed to Git from one user.
To port commit users as well use ``p4.run_describe(cl)[0]['user']`` to find P4 user
and replace incoming parameters ``--git-user``, ``--git-email`` with
mapping of P4 users into Git user parameters (``-gu``, ``-ge``) that are passed to submitter.

.. literalinclude:: ../examples/p4_to_git.py
    :language: python
    :lines: 44-56
    :emphasize-lines: 9-10
    :lineno-start: 44


Also this script only can process the contents of one P4 folder, creating a single mapping for it
in ``client["View"]``. To use multiple mappings, edit ``client["View"]`` accordingly
instead of parsing ``--depot-path`` parameter.

.. literalinclude:: ../examples/p4_to_git.py
    :language: python
    :lines: 33-37
    :emphasize-lines: 3
    :lineno-start: 33
