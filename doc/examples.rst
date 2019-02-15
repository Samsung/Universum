Other usage examples
====================

This page contains some examples of Python scripts using Universum.


Export Perforce repository to Git
---------------------------------

Here's an example script that ports all commits from certain directory in Perforce repository
to certain directory in Git repository.

.. note::
    To port whole repository you just have to pass root directories in both cases

In this example commit messages are preserved, but all changes are committed to Git from one user.
To port commit users as well use ``p4.run_describe(cl)[0]['user']`` to find P4 user
and replace incoming parameters ``--git-user``, ``--git-email`` with
mapping of P4 users into Git user parameters (``-gu``, ``-ge``) that are passed to submitter.

Also this script is porting contents of one P4 folder, that is mapped into cloned Git repository.
To use multiple mappings, edit ``client["View"]`` accordingly instead of parsing ``--depot-path``
parameter

Preconditions for this particular script:
 * Git repository is created and cloned

   * ``--git-repo`` is an absolute local path

 * All required changes in Perforce are made in one folder (``--depot-path``)

   * ``--depot-path`` is in P4 format starting with "//"

 * Git user (``--git-user``, ``--git-email``) is authorized to commit

 * Perforce user (``--p4-user``, ``--p4-password``) is authorized to sync ``--depot-path`` folder

 * Perforce disposable client (``--p4-client``) does not exist

 * Perforce disposable client root (``--client-root``) leads to the local folder inside
   Git repository to be committed

   * ``--client-root`` should not necessarily equal ``--git-repo``;
     it just has to be somewhere inside repository


.. literalinclude:: ../examples/p4_to_git.py
    :language: python
