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

    --steps-filter -f : @replace
        | Allows to filter which steps to execute during launch.
         String value representing single filter or a set of filters separated by '**:**'.
         To define exclude pattern use '**!**' symbol at the beginning of pattern.
        |
        | A universum step match specified pattern when 'filter' is a substring of step 'name'.
         This functionality is similar to 'boosttest' and 'gtest' filtering.
         Except using of special characters like '*', '?', etc. which are ignored.
        |
        | Examples:
        | * -f='run test'               - run only steps which contain 'run test' string in name
        | * -f='!run test'              - run all steps except those which contain 'run test' string in name
        | * -f='test 1:test 2'          - run all steps with 'test 1' OR 'test 2' in name
        | * -f='test 1:!unit test 1'    - run all steps with 'test 1' in name except those which contain 'unit test 1'

    {poll,submit,nonci} : @replace
        | :doc:`universum poll <args_poll>`
        | :doc:`universum submit <args_submit>`
        | :doc:`universum nonci <args_nonci>`
