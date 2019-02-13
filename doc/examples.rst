Other usage examples
====================

Here are some examples of Python scripts using Universum.


Export Perforce repository to Git saving commit messages
--------------------------------------------------------

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
