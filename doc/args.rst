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
        .. include:: filter_description.rst

    --html-log -hl : @after
        To make sure all the interactive features of such a page work right in Jenkins artifacts,
        please refer to the following :doc:`guide <jenkins>`

    {init,run,poll,submit,github-handler} : @replace
        | See detailed description of additional commands :doc:`here <additional_commands>`.
