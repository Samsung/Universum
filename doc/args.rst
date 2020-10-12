Command line and parameters
===========================

`Univesrum` can be executed via ``{python} -m universum`` with various parameters. These parameters can be
passed via command line; most of them can also be passed via environment variables.

Apart from default mode, actually used for CI, `Universum` also has several other
:doc:`helpful modes <additional_commands>` and a bunch of :doc:`analyzers <code_report>` that are used to
add comments on found issues right to the selected code review system.

.. argparse::
    :module: universum.__main__
    :func: define_arguments
    :prog: {python} -m universum
    :nosubcommands:

    --version : @replace
        Display product name & version instead of launching.

    --filter -f : @replace
        | Allows to filter which steps to execute during launch.
         String value representing single filter or a set of filters separated by '**:**'.
         To define exclude pattern use '**!**' symbol at the beginning of the pattern.
        |
        | A Universum step match specified pattern when 'filter' is a substring of step 'name'.
         This functionality is similar to 'boosttest' and 'gtest' filtering, except special characters
         (like '*', '?', etc.) are ignored.
        |
        | Examples:
        | * -f='run test'               - run only steps that contain 'run test' substring in their names
        | * -f='!run test'              - run all steps except those containing 'run test' substring in their
         names
        | * -f='test 1:test 2'          - run all steps with 'test 1' OR 'test 2' substring in their names
        | * -f='test 1:!unit test 1'    - run all steps with 'test 1' substring in their names except those
         containing 'unit test 1'

    {init,run,poll,submit,github-handler} : @replace
        | See detailed description of additional commands :doc:`here <additional_commands>`.
