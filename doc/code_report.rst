Code report
===========

The following analysing modules (analysers) are installed by default: ``universum_pylint``, ``universum_svace``,
``universum_uncrustify``. Analysers are separate scripts, fully compatible with Universum.
It is possible to use them independently from command line.

All analysers must have an argument for JSON file with analysis results. If you run code report independently,
the name must conform to file name standards. If argument is not provided, output will be written to console.

Running analysers from Universum, you need to add ``code_report=True`` and result file argument mandatory must be
set to ``"${CODE_REPORT_FILE}"``. ``"${CODE_REPORT_FILE}"`` is a pseudo-variable that will be replaced with
the file name during execution. Also, you are able not to add ``code_report=True`` option and name file as you wish,
in this case result file won't be processed according to the rules defined for analysers and step will be marked as
``Failed`` if there are analysis issues found.

.. note::
    When using Universum, if file with analysis results is not added to artifacts, it will be deleted
    along with other build sources and results.

When using via Universum ``code_report=True`` step, use ``--report-to-review``
functionality to comment on any found issues to code review system.


.. _code_report#pylint:

Pylint
------

.. argparse::
    :ref: analyzers.pylint.form_arguments_for_documentation
    :prog: universum_pylint

Config example for ``universum_pylint``:

.. testcode::

    from _universum.configuration_support import Variations

    configs = Variations([dict(name="pylint", code_report=True, command=["universum_pylint",
                               "--python-version", "3", "--result-file", "${CODE_REPORT_FILE}",
                               "--files", "*.py", "examples/"])
                          ])

    if __name__ == '__main__':
        print configs.dump()

This file will get us the following list of configurations:

.. testcode::
    :hide:

    print "$ ./configs.py"
    print configs.dump()

.. testoutput::

    $ ./configs.py
    [{'command': 'universum_pylint --python-version 3 --result-file ${CODE_REPORT_FILE} --files *.py examples/', 'name': 'pylint', 'code_report': True}]


.. _code_report#svace:

Svace
-----

.. argparse::
    :ref: analyzers.svace.form_arguments_for_documentation
    :prog: universum_svace

Config example for ``universum_svace``:

.. testcode::

    from _universum.configuration_support import Variations

    configs = Variations([dict(name="svace", code_report=True, command=["universum_svace",
                               "--build-cmd", "make", "--lang", "CXX",
                               "--result-file", "${CODE_REPORT_FILE}"])
                          ])

    if __name__ == '__main__':
        print configs.dump()

will produce this list of configurations:

.. testcode::
    :hide:

    print "$ ./configs.py"
    print configs.dump()

.. testoutput::

    $ ./configs.py
    [{'command': 'universum_svace --build-cmd make --lang CXX --result-file ${CODE_REPORT_FILE}', 'name': 'svace', 'code_report': True}]


.. _code_report#uncrustify:

Uncrustify
----------

.. argparse::
    :ref: analyzers.uncrustify.form_arguments_for_documentation
    :prog: universum_uncrustify

Config example for ``universum_uncrustify``:

.. testcode::

    from _universum.configuration_support import Variations

    configs = Variations([dict(name="svace", code_report=True, command=["universum_uncrustify",
                               "--file-names", "*.c", "--cfg-file", "file_name.cfg",
                               "--result-file", "${CODE_REPORT_FILE}"])
                          ])

    if __name__ == '__main__':
        print configs.dump()

will produce this list of configurations:

.. testcode::
    :hide:

    print "$ ./configs.py"
    print configs.dump()

.. testoutput::

    $ ./configs.py
    [{'command': 'universum_uncrustify --file-names *.c --cfg-file file_name.cfg --result-file ${CODE_REPORT_FILE}', 'name': 'svace', 'code_report': True}]
