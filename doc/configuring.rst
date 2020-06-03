Configuring the project
=======================

.. currentmodule:: universum.configuration_support

In order to use the `Universum`, the project should provide a configuration file.
This file is a regular python script with specific interface, which is recognized
by the `Universum`.

The path to the configuration file is supplied to the main script via the `CONFIG_PATH`
environment variable or ``--config`` / ``-cfg`` `command-line parameter
<args.html#Configuration\ execution>`__.
Internally the config file is processed by the :mod:`universum.launcher` module. The path is passed
to this module in `config_path` member of its input settings.

.. note::

    Generally there should be no need to implement complex logic in the configuration file,
    however the `Universum` doesn't limit what project uses its configuration file for. Also,
    there are no restriction on using of external python modules, libraries or on the
    structure of the configuration file itself.

    The project is free to use whatever it needs in the configuration file; just remember,
    all the calculations are done on config processing, not step execution.


Project configuration
---------------------

Project configuration (also mentioned as `build configuration`) is a simple complete way
to test the project: e.g., build it for some specific platform, or run some specific test script.
Basically, `project configuration` is a single launch of some external application or script.

For example::

    $ ./build.sh -d --platform MSM8996
    $ make tests
    $ ./run_regression_tests.sh

— are three different possible project configurations.


Minimal project configuration file
----------------------------------

Below is an example of the configuration file in its most basic form:

.. testcode::

    from universum.configuration_support import Variations

    configs = Variations([dict(name="Build", command=["build.sh"])])

This configuration file uses a :class:`Variations` class
from the :mod:`universum.configuration_support`
module and defines one build configuration.

.. note::

    Creating a :class:`Variations` instance takes a list of dictionaries as an argument,
    where every new list member describes a new `project configuration`_.

* The :mod:`universum.configuration_support` module provides several functions to be used by project configuration files
* The `Universum` expects project configuration file to define global variable with
  name `configs`. This variable defines all project configurations to be used in a build.

The minimal project configuration file example defines just one project configuration with
the following parameters:

#. **name** is a string `"Build"`
#. **command** is a list with a string item `"build.sh"`

Both `name` and `command`, however, can be missing. A build configuration without a name will still have a step number;
a build configuration without issued command will do nothing, but will still appear in log and have a step number.

.. note::

    Command line is a list with (so far) one string item, not just a string.
    Command name and all the following arguments must be passed as a list of separate strings.
    See `List of configurations`_ for more details.


Execution directory
-------------------

Some scripts (using relative paths or filesystem communication commands like ``pwd``)
work differently when launching them via ``./scripts/run.sh`` and via ``cd scripts/ && ./run.sh``.

Also, some console applications, such as ``make`` and ``ant``, support setting working directory
using special argument. Some other applications lack this support.

That is why it is sometimes necessary, and sometimes just convenient to launch
the configuration `command` in a directory other then project root. This can be easily done
using `directory` keyword:

.. testcode::

    from universum.configuration_support import Variations

    configs = Variations([dict(name="Make Special Module", directory="specialModule", command=["make"])])

To use a `Makefile` located in `"specialModule"` directory without passing "-C specialModule/"
arguments to ``make`` command, the launch directory is specified.


.. _get_project_root:

:func:`get_project_root`
~~~~~~~~~~~~~~~~~~~~~~~~

By default for any launched external command `current directory` is the actual directory
containing project files. So any internal relative paths for the project should not cause any troubles.
But when, for any reason, there's a need to refer to project location absolute path, it is
recommended to use :func:`get_project_root` function from :mod:`universum.configuration_support` module.

.. note::

    The `Universum` launches in its own working directory that may be changed for every run
    and therefore cannot be hardcoded in `configs.py` file. Also, if not stated otherwise,
    project sources are copied to a temporary directory that will be deleted after a run.
    This directory may be created in different places depending on various `Universum` settings
    (not only the `working directory`, mentioned above), so the path to this directory
    can not be hardcoded too.

The :mod:`universum.configuration_support` module processes current `Universum` run settings and returns
actual project root to the config processing module.

See the following example configuration file:

.. testcode::

    from universum.configuration_support import Variations, get_project_root

    configs = Variations([dict(name="Run tests", directory="/home/scripts", command=["./run_tests.sh", "--directory", get_project_root()])])

In this configuration a hypothetical external script `"run_tests.sh"` requires absolute path
to project sources as an argument. The :func:`get_project_root` will pass the actual project root,
no matter where the sources are located on this run.


List of configurations
----------------------

The `Universum` gets the list of project configurations from the `configs` global variable.
In the basic form this variable contains a flat list of items, and each item represents one
`project configuration`_.

Below is an example of the configuration file with three different configurations:

.. testcode::

    from universum.configuration_support import Variations, get_project_root
    import os.path

    test_path = os.path.join(get_project_root(), "out/tests")
    configs = Variations([
        dict(name="Make Special Module", command=["make", "-C", "SpecialModule/"], artifacts="out"),
        dict(name="Run internal tests", command=["scripts/run_tests.sh"]),
        dict(name="Run external tests", directory="/home/scripts", command=["run_tests.sh", "-d", test_path])
    ])

The example configuration file declares the following `Universum` run steps:

1. `Make` a module, located in `"specialModule"` directory
2. Run a `"run_tests.sh"` script, located in `"scripts"` directory
3. Run a `"run_tests.sh"` script, located in external directory `"/home/scripts"`
   and pass an absolute path to a directory `"out/tests"` inside project location
4. Copy resulting directory `"out"` to the artifact directory

.. note::

    Concatenating :func:`get_project_root` results with any other paths is recommended using
    :func:`os.path.join` function to avoid any possible errors on path joining.


Common `Variations` keys
------------------------

Each configuration description is a python dictionary with the following possible keys:

..

name
    Specifies the name of the configuration. The name is used as the title of the build log
    block corresponding to the build of this configuration. It is also used to generate
    name of the log file if the option for storing to log files is selected.
    A project configuration can have no name, but it is not recommended for aesthetic reasons.
    If several project configurations have the same names, and logs are stored to files
    (see ``--out`` / ``-o``  `command-line parameter <args.html#Output>`__ for details),
    all logs for such configurations will be stored to one file in order of their appearances.

..

command
    The list with command line for the configuration launch. For every project configuration
    first list item should be a console command (e.g. script name, or any other command like ``ls``),
    and other list items should be the arguments, added to the command (e.g. ``--debug`` or ``-la``).
    Every command line element, separated with space character, should be passed as a separate
    string argument. Lists like ``["ls -a"]`` will not be processed correctly and thus
    should be splat into ``["ls", "-a"]``. Lists like ``["build.sh", "--platform A"]``
    will not be processed correctly and thus should be plat into ``["build.sh", "--platform", "A"]``.
    A project configuration can have an empty list as a command. Such configuration
    won't do anything except informing user about missing it.

.. note::

    Some common actions, such as ``echo`` or ``cp``, are bash features and not actual programs to run. These
    features should be called as ``["bash", "-C", "echo -e 'Some line goes here'"]``. Note that in this case
    the string to be passed to bash is one argument containing white spaces and therefore not splat by commas.

.. _build_environment:

environment
    Python dictionary of required environment variables, e.g. ``environment={"VAR1": "String", "VAR2": "123"}``
    Can be set at any step level, but re-declaring variables is not supported, so please make sure
    to mention every variable only one time at most.

.. _build_artifacts:

artifacts
    Path to the file or directory to be copied to the working directory as an execution result.
    Can contain shell-style pattern matching (e.g. `"out/*.html"`), including recursive wildcards
    (e.g. `"out/**/index.html"`).
    If not stated otherwise (see ``--no-archive`` `command-line parameter <args.html#Artifact\ collection>`__
    for details), artifact directories are copied as archives.
    If :ref:`'artifact_prebuild_clean' key <clean_artifacts>` is either absent or set to `False` and
    stated artifacts are present in downloaded sources, it is considered a failure and configuration
    execution will not proceed.
    If no required artifacts were found in the end of the `Universum` run, it is also considered a failure.
    In case of shell-style patterns build is failed if no files or directories matching pattern are found.
    Any project configuration may or may not have any artifacts.

.. _report_artifacts:

report_artifacts
    Special artifacts for reporting (e.g. to Swarm). A separate link to each of such artifacts
    will be added to the report. Unlike :ref:`artifacts <build_artifacts>`,
    `report_artifacts` are not obligatory and their absence is not considered a build failure.
    A directory cannot be stored as a separate artifact, so when using ``--no-archive`` option,
    do not claim directories as `report_artifacts`.
    Please note that any file can be claimed as `artifact`, `report_artifact`, or both.
    A file, claimed both in `artifacts` and `report_artifacts`, will be mentioned in a report
    and will cause build failure when missing.

.. _clean_artifacts:

artifact_prebuild_clean
    Basic usage is adding ``artifact_prebuild_clean=True`` to configuration description.
    By default artifacts are not stored in VCS, and artifact presence before build most likely
    means that working directory is not cleaned after previous build and therefore might influence
    build results. But sometimes deliverables have to be stored in VCS, and in this case
    instead of stopping the build they should be simply cleaned before it. This is where
    ``artifact_prebuild_clean=True`` key is supposed to be used. If set without any :ref:`artifacts <build_artifacts>`
    or `report_artifacts`_, this key will be ignored.

..

directory
    Path to a current working directory for launched process.
    Please see the `Execution directory`_ section for details. No `directory` is equal to
    empty string passed as `directory` and means the `command` will be launched
    from project root directory.

.. _critical_step:

critical
    Basic usage is adding ``critical=True`` to configuration description.
    This parameter is used in case of a linear step execution, when the result of some step is
    critical for the subsequent step execution. If some configuration has `critical` key set to `True`
    and executing this step fails, no more configurations will be executed during this run.
    However, all already started :ref:`background <background_step>` steps will be finished
    regardless critical step results.

.. _background_step:

background
    Basic usage is adding ``background=True`` to configuration description.
    This parameter means that configuration should be executed independently in parallel with
    all other steps. All logs from such steps are written to file, and the results of execution
    are collected in the end of `Universum` run. Next step execution begins immediately after
    starting a background step, not waiting for it to be completed. Several background steps
    can be executed simultaneously.

.. _finish_background:

finish_background
    Basic usage is adding ``finish_background=True`` to configuration description.
    This parameter means that before executing this particular step all ongoing background steps
    (if any) should be finished first.

..

code_report
    Basic usage is adding ``code_report=True`` to configuration description and ``--result-file="${CODE_REPORT_FILE}"``
    to 'command' arguments.
    Specifies step that performs static or syntax analysis of code.
    Analyzers currently provided by Universum are: ``pylint``, ``svace`` and ``uncrustify``
    (see `code_report parameters <code_report.html>`__ for details).

.. _tc_tags:

pass_tag, fail_tag
    Basic usage is adding ``pass_tag="PASS", fail_tag="FAIL"`` to the configuration description.
    These keys are currently implemented only for TeamCity build. You can specify one, both or neither of them
    per step. Defining ``pass_tag="PASS"`` means that current build on TeamCity will be tagged with label ``PASS``
    if this particular step succeeds. Defining ``fail_tag="FAIL"`` means that current build on TeamCity will be
    tagged with label ``FAIL`` if this particular step fails. Key values can be set to any strings acceptable by
    TeamCity as tags. It is not recommended to separate words in the tag with spaces, since you cannot create
    a tag with spaces in TeamCity's web-interface. Every tag is added (if matching condition) after executing
    build step it is set in, not in the end of all run.
    ``pass_tag`` and ``fail_tag`` can also be used when `multiplying build configurations`_, like this:

    .. testsetup::

        #!/usr/bin/env python3.7

        from universum.configuration_support import Variations

    .. testcode::

        make = Variations([dict(name="Make ", command=["make"], pass_tag="pass_")])

        target = Variations([
            dict(name="Linux", command=["--platform", "Linux"], pass_tag="Linux"),
            dict(name="Windows", command=["--platform", "Windows"], pass_tag="Windows")
        ])

        configs = make * target

    This code will produce this list of configurations:

    .. testcode::
        :hide:

        print("$ ./configs.py")
        print(configs.dump())

    .. testoutput::

        $ ./configs.py
        [{'name': 'Make Linux', 'command': 'make --platform Linux', 'pass_tag': 'pass_Linux'},
        {'name': 'Make Windows', 'command': 'make --platform Windows', 'pass_tag': 'pass_Windows'}]

    This means that tags "pass_Linux" and "pass_Windows" will be sent to TeamCity's build.


.. note::

    All the paths, specified in `command`, `artifacts` and `directory` parameters, can be
    absolute or relative. All relative paths start from the project root (see :ref:`get_project_root`).


Dump configurations list
------------------------

Class :class:`Variations` have a build-in function :meth:`~Variations.dump`, that processes the passed dictionaries
and returns the list of all included configurations.

Below is an example of the configuration file that uses :meth:`~Variations.dump` function for debugging:

.. testsetup::

    def mock_project_root():
        return "/home/Project"

    import universum.configuration_support
    universum.configuration_support.get_project_root = mock_project_root

.. testcode::

    #!/usr/bin/env python3.7

    from universum.configuration_support import Variations, get_project_root
    import os.path

    test_path = os.path.join(get_project_root(), "out/tests")
    configs = Variations([
        dict(name="Make Special Module", command=["make", "-C", "SpecialModule/"], artifacts="out"),
        dict(name="Run internal tests", command=["scripts/run_tests.sh"]),
        dict(name="Run external tests", directory="/home/scripts", command=["run_tests.sh", "-d", test_path])
    ])

    if __name__ == '__main__':
        print(configs.dump())

The combination of ``#!/usr/bin/env python3.7`` and ``if __name__ == '__main__':`` allows launching
the `configs.py` script from shell.

For ``from universum.configuration_support import`` to work correctly, `configs.py` should be copied to
`Universum` root directory and launched there.

When launched from shell instead of being used by `Universum` system, :ref:`get_project_root` function
returns current directory instead of actual project root.

The only thing this script will do is create `configs` variable and print all project configurations
it includes. For example, running the script, given above, will result in the following:

.. testcode::
    :hide:

    print("$ ./configs.py")
    print(configs.dump())

.. testoutput::

    $ ./configs.py
    [{'name': 'Make Special Module', 'command': 'make -C SpecialModule/', 'artifacts': 'out'},
    {'name': 'Run internal tests', 'command': 'scripts/run_tests.sh'},
    {'name': 'Run external tests', 'directory': '/home/scripts', 'command': 'run_tests.sh -d /home/Project/out/tests'}]

As second and third build configurations have the same names, if log files are created,
only two logs will be created: one for the first build step, another for both second and third,
where the third will follow the second.


Combining configurations
------------------------

The Variations class provides a way to generate a full testing scenario by simulating the
combination of configurations.

For this class :class:`Variations` has built-in ``+`` and ``*`` operators that allow creating
configuration sets out of several :class:`Variations` instances.


Adding build configurations
~~~~~~~~~~~~~~~~~~~~~~~~~~~

See the following example:

.. testcode::

    #!/usr/bin/env python3.7

    from universum.configuration_support import Variations

    one = Variations([dict(name="Make project", command=["make"])])
    two = Variations([dict(name="Run tests", command=["run_tests.sh"])])

    configs = one + two

    if __name__ == '__main__':
        print(configs.dump())

The addition operator will just concatenate two lists into one, so
the `result <Dump configurations list_>`_ of such configuration file will be
the following list of configurations:

.. testcode::
    :hide:

    print("$ ./configs.py")
    print(configs.dump())

.. testoutput::

    $ ./configs.py
    [{'name': 'Make project', 'command': 'make'},
    {'name': 'Run tests', 'command': 'run_tests.sh'}]


Multiplying build configurations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Multiplication operator can be used in configuration file two ways:

1. multiplying configuration by a constant
2. multiplying configuration by another configuration

Multiplying configuration by a constant is just an equivalent of multiple additions:

.. doctest::

    >>> run = Variations([dict(name="Run tests", command=["run_tests.sh"])])
    >>> print (run * 2 == run + run)
    True

Though the application area of multiplication by a constant is unclear at the moment.

Multiplying configuration by a configuration combines their properties.
For example, this configuration file:

.. testcode::

    #!/usr/bin/env python3.7

    from universum.configuration_support import Variations

    make = Variations([dict(name="Make ", command=["make"], artifacts="out")])

    target = Variations([dict(name="Platform A", command=["--platform", "A"]),
                         dict(name="Platform B", command=["--platform", "B"])])

    configs = make * target

    if __name__ == '__main__':
        print(configs.dump())

will `produce <Dump configurations list_>`_ this list of configurations:

.. testcode::
    :hide:

    print("$ ./configs.py")
    print(configs.dump())

.. testoutput::

    $ ./configs.py
    [{'name': 'Make Platform A', 'command': 'make --platform A', 'artifacts': 'out'},
    {'name': 'Make Platform B', 'command': 'make --platform B', 'artifacts': 'out'}]

* `command` and `name` values are produced of `command` and `name` values of each of two configurations
* `artifacts` value, united with no corresponding value in second configuration, remains unchanged

.. note::

    Note the extra space character at the end of the configuration name `"Make "`.
    As multiplying process uses simple adding of all corresponding configuration settings,
    string variables are just concatenated, so without extra spaces resulting name
    would look like "MakePlatform A". If we add space character, the resulting name
    becomes "Make Platform A".


Combination of addition and multiplication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When creating a project configuration file, the two available operators, ``+`` and ``*``,
can be combined in any required way. For example:

.. testcode::

    #!/usr/bin/env python3.7

    from universum.configuration_support import Variations

    make = Variations([dict(name="Make ", command=["make"], artifacts="out")])
    test = Variations([dict(name="Run tests for ", directory="/home/scripts", command=["run_tests.sh", "--all"])])

    debug = Variations([dict(name=" - Release"),
                        dict(name=" - Debug", command=["-d"])])

    target = Variations([dict(name="Platform A", command=["--platform", "A"]),
                         dict(name="Platform B", command=["--platform", "B"])])

    configs = make * target + test * target * debug

    if __name__ == '__main__':
        print(configs.dump())

This file `will get us <Dump configurations list_>`_ the following list of configurations:

.. testcode::
    :hide:

    print("$ ./configs.py")
    print(configs.dump())

.. testoutput::

    $ ./configs.py
    [{'name': 'Make Platform A', 'command': 'make --platform A', 'artifacts': 'out'},
    {'name': 'Make Platform B', 'command': 'make --platform B', 'artifacts': 'out'},
    {'name': 'Run tests for Platform A - Release', 'directory': '/home/scripts', 'command': 'run_tests.sh --all --platform A'},
    {'name': 'Run tests for Platform A - Debug', 'directory': '/home/scripts', 'command': 'run_tests.sh --all --platform A -d'},
    {'name': 'Run tests for Platform B - Release', 'directory': '/home/scripts', 'command': 'run_tests.sh --all --platform B'},
    {'name': 'Run tests for Platform B - Debug', 'directory': '/home/scripts', 'command': 'run_tests.sh --all --platform B -d'}]

As in common arithmetic, multiplication is done before addition. To change the operations
order, use parentheses:

.. doctest::

    >>> configs = (make + test * debug) * target


.. _filtering:

Excluding configurations
------------------------

At the moment there is no support for ``-`` operator.
There is no easy way to exclude one of configurations, generated by adding/multiplying.
But there is a conditional including implemented. To include/exclude configuration depending on
environment variable, use `if_env_set` key. When script comes to executing a configuration with
such key, if there's no environment variable with stated name set to either "true", "yes" or "y",
configuration is not executed. If any other value should be set, use
``if_env_set="VARIABLE_NAME == variable_value"`` comparison. Please pay special attention on
the absence of any quotation marks around `variable_value`: if added, `$VARIABLE_NAME` will be
compared with `"variable_value"` string and thus fail. Also, please note, that all spaces before and after
`variable_value` will be automatically removed, so ``if_env_set="VARIABLE_NAME == variable_value "`` will
be equal to ``os.environ["VARIABLE_NAME"] = "variable_value"`` but not
``os.environ["VARIABLE_NAME"] = "variable_value "``.

`$VARIABLE_NAME` consist solely of letters, digits, and the '_' (underscore) and not begin with a digit.

If such environment variable should not be set to specific value, please use
``if_env_set="VARIABLE_NAME != variable_value"`` (especially ``!= True`` for variables
to not be set at all).

If executing the configuration depends on more than one environment variable,
use ``&&`` inside `if_env_set` value. For example,
``if_env_set="SPECIAL_TOOL_PATH && ADDITIONAL_SOURCES_ROOT"`` configuration will be executed only
in case of both `$SPECIAL_TOOL_PATH` and `$ADDITIONAL_SOURCES_ROOT` environment variables set
to some values. If any of them is missing or not set in current environment,
the configuration will be excluded from current run.
