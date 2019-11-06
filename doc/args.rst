Command line
------------

Main script of project `Universum` is ``universum.py``.
All command-line parameters, general and module-related, are passed to this main script.

.. note::
    Most of command-line parameters can be replaced by setting up corresponding environment
    variables (see 'env' comment in descriptions)

.. argparse::
    :module: universum
    :func: define_arguments
    :prog: universum
    :nosubcommands:

    --version : @replace
        Display product name & version instead of launching.

    {poll,submit,nonci} : @replace
        | :doc:`universum poll <args_poll>`
        | :doc:`universum submit <args_submit>`
        | :doc:`universum nonci <args_nonci>`
