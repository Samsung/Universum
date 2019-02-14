Other usage examples
====================

Here are some examples of Python scripts using Universum.


Export Perforce repository to Git
---------------------------------

Here's an example script that ports all commits from certain directory in Perforce repository
to certain directory in Git directory. (Note that to port whole repository you just have to pass
root directories in both cases)

In this example commit messages are preserved, but all changes are committed to Git from one user.

Preconditions:
 * Git repository is created and cloned (``--git-repo`` is an absolute local path)

 * Git user (``--git-user``, ``--git-email``) is authorized to commit

   * To port commit users as well use ``p4.run_describe(cl)[0]['user']``

 * All required changes in Perforce are made in one folder (``--depot-path``)

   * To use multiple mappings, edit ``client["View"]`` accordingly

 * Perforce disposable client root (``--client-root``) leads to git folder to be committed

   * ``--client-root`` should not necessarily equal ``--git-repo``;
     it just has to be somewhere inside repository


.. literalinclude:: ../examples/p4_to_git.py
    :language: python
