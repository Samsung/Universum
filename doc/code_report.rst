Code report
===========

The following analysing modules (analysers) are currently added to Universum:

   * `pylint`_
   * `mypy`_
   * `svace`_
   * `uncrustify`_

Analysers are separate scripts, fully compatible with Universum. It is possible to use them
as independent Python modules.

All analysers must have an argument for JSON file with analysis results. If you run code report independently,
the name must conform to file name standards. If argument is not provided, output will be written to console.

Running analysers from Universum config, you need to add ``code_report=True`` and result file argument
mandatory must be set to ``"${CODE_REPORT_FILE}"``.
``"${CODE_REPORT_FILE}"`` is a pseudo-variable that will be replaced with the file name during execution.
Also, without ``code_report=True`` and result file may be called any name, as it won't be processed according
to the rules defined for analysers. Such step will be marked as ``Failed`` if any analysis issues are found.

.. note::
    When using Universum, if a file with analysis results is not added to artifacts, it will be deleted
    along with other build sources and results.

When using via Universum ``code_report=True`` step, use ``--report-to-review``
functionality to comment on any found issues to code review system.


.. _code_report#pylint:

Pylint
------

.. argparse::
    :ref: universum.analyzers.pylint.form_arguments_for_documentation
    :prog: {python} -m universum.analyzers.pylint

Config example for ``universum.analyzers.pylint``:

.. testcode::

    from universum.configuration_support import Configuration, Step

    configs = Configuration([Step(name="pylint", code_report=True, command=[
        "{python}", "-m", "universum.analyzers.pylint", "--python-version", "2.7",
        "--result-file", "${CODE_REPORT_FILE}", "--files", "*.py", "examples/"
    ])])

    if __name__ == '__main__':
        print(configs.dump())

This file will get us the following list of configurations:

.. testcode::
    :hide:

    print("$ ./.universum.py")
    print(configs.dump())

.. testoutput::

    $ ./.universum.py
    [{'name': 'pylint', 'code_report': True, 'command': '{python} -m universum.analyzers.pylint --python-version 2.7 --result-file ${CODE_REPORT_FILE} --files *.py examples/'}]


.. _code_report#mypy:

Mypy
----

.. argparse::
    :ref: universum.analyzers.mypy.form_arguments_for_documentation
    :prog: {python} -m universum.analyzers.mypy

Config example for ``universum.analyzers.mypy``:

.. testcode::

    from universum.configuration_support import Configuration, Step

    configs = Configuration([Step(name="mypy", code_report=True, command=[
        "{python}", "-m", "universum.analyzers.mypy", "--python-version", "3",
        "--result-file", "${CODE_REPORT_FILE}", "--files", "*.py", "examples/"
    ])])

    if __name__ == '__main__':
        print(configs.dump())

This file will get us the following list of configurations:

.. testcode::
    :hide:

    print("$ ./.universum.py")
    print(configs.dump())

.. testoutput::

    $ ./.universum.py
    [{'name': 'mypy', 'code_report': True, 'command': '{python} -m universum.analyzers.mypy --python-version 3 --result-file ${CODE_REPORT_FILE} --files *.py examples/'}]


.. _code_report#svace:

Svace
-----

.. argparse::
    :ref: universum.analyzers.svace.form_arguments_for_documentation
    :prog: {python} -m universum.analyzers.svace

Config example for ``universum.analyzers.svace``:

.. testcode::

    from universum.configuration_support import Configuration, Step

    configs = Configuration([Step(name="svace", code_report=True, command=[
        "{python}", "-m", "universum.analyzers.svace", "--build-cmd", "make", "--lang", "CXX",
        "--result-file", "${CODE_REPORT_FILE}"
    ])])

    if __name__ == '__main__':
        print(configs.dump())

will produce this list of configurations:

.. testcode::
    :hide:

    print("$ ./.universum.py")
    print(configs.dump())

.. testoutput::

    $ ./.universum.py
    [{'name': 'svace', 'code_report': True, 'command': '{python} -m universum.analyzers.svace --build-cmd make --lang CXX --result-file ${CODE_REPORT_FILE}'}]


.. _code_report#uncrustify:

Uncrustify
----------

.. argparse::
    :ref: universum.analyzers.uncrustify.form_arguments_for_documentation
    :prog: {python} -m universum.analyzers.uncrustify
    :nodefault:

Config example for ``universum.analyzers.uncrustify``:

.. testcode::

    from universum.configuration_support import Configuration, Step

    configs = Configuration([Step(name="uncrustify", code_report=True, command=[
        "{python}", "-m", "universum.analyzers.uncrustify",  "--files", "project_root_directory",
        "--cfg-file", "file_name.cfg", "--filter-regex", ".*//.(?:c|cpp)",
        "--result-file", "${CODE_REPORT_FILE}", "--output-directory", "uncrustify"
    ])])

    if __name__ == '__main__':
        print(configs.dump())

will produce this list of configurations:

.. testcode::
    :hide:

    print("$ ./.universum.py")
    print(configs.dump())

.. testoutput::

    $ ./.universum.py
    [{'name': 'uncrustify', 'code_report': True, 'command': '{python} -m universum.analyzers.uncrustify --files project_root_directory --cfg-file file_name.cfg --filter-regex .*//.(?:c|cpp) --result-file ${CODE_REPORT_FILE} --output-directory uncrustify'}]
