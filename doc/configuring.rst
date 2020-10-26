Project configuration
=====================

.. currentmodule:: universum.configuration_support

In order to use the `Universum`, the project should provide a configuration file.
This file is a regular python script with specific interface, which is recognized by the `Universum`.

By default, configuration file is called ``.universum.py`` and is located in the project root directory.
To create one automatically, execute ``{python} -m universum init`` in the project root directory. To use another
file name or file path, use ``--config`` / ``-cfg`` `command-line parameter <args.html#Configuration\ execution>`__
or `CONFIG_PATH` environment variable.

Internally the config file is processed by the :mod:`universum.launcher` module. The path is passed
to this module in `config_path` member of its input settings.

.. note::

    Generally there should be no need to implement complex logic in the configuration file,
    however the `Universum` doesn't limit what project uses its configuration file for. Also,
    there are no restriction on using of the external python modules, libraries or on the
    structure of the configuration file itself.

    The project is free to use whatever it needs in the configuration file; just remember that
    all the calculations are done on config processing, not step execution.


Build step
----------

Project configuration is a list of actions to be performed to test a project: e.g., prepare environment,
build project for some specific platform or run a specific test script. These actions are mostly referred as
"build steps". A project configuration, being a list of build steps, is sometimes referred as a build configuration.

Here's an example of such actions::

    $ ./build.sh -d --platform linux_amd64
    $ cp -r ./build/results/ ./tests
    $ make tests
    $ ./run_regression_tests.sh

Each build step is defined by two main parameters:

* a `name` to refer to
* a `command` to execute

Both `name` and `command`, however, can be undefined. A build step without a name will still be issued a number;
a build step without a command will do nothing, but will still appear in log (and have a step number).

For storing such parameters :mod:`universum.configuration_support` provides a class :class:`Step`, that has
:ref:`a list of various step parameters <keys>`. Build steps can be :ref:`added, multiplied <combining>` and
:ref:`excluded <filtering>`.


Minimal project configuration file
----------------------------------

Below is an example of the configuration file in its most basic form:

.. testcode::

    from universum.configuration_support import Configuration, Step

    configs = Configuration([Step(name="Build", command=["build.sh"])])

This configuration file uses a :class:`Configuration` class from the :mod:`universum.configuration_support`
module and describes exactly one `build step`_.

.. note::

    Creating a :class:`Configuration` instance takes a list of dictionaries as an argument,
    where every new list member describes a new `build step`_.

* The :mod:`universum.configuration_support` module provides several helpful functions to be used
  by project configuration files.
* The `Universum` expects project configuration file to define global variable with name `configs`.
  This variable defines all build steps to be performed during a single `Universum` run.

This exact configuration file defines a project configuration that consists of one step with the following parameters:

#. **name** is a string `"Build"`
#. **command** is a list with a string item `"build.sh"`

.. note::

    Command line is a list with (so far) one string item, not just a string.
    Command name and all the following arguments must be passed as a list of separate strings.
    See `command` key :ref:`detailed description <keys>` for more details.


Execution directory
-------------------

Some scripts (using relative paths or filesystem communication commands like ``pwd``)
work differently when launching them via ``./scripts/run.sh`` and via ``cd scripts/ && ./run.sh``.

Also, some console applications, such as ``make`` and ``ant``, support setting working directory
using special argument. Some other applications lack this support.

That is why it is sometimes necessary, and sometimes just convenient to launch the stated `command`
in a directory other then project root. This can be easily done using `directory` keyword:

.. testcode::

    from universum.configuration_support import Configuration, Step

    configs = Configuration([Step(name="Make Special Module", directory="specialModule", command=["make"])])

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

    The `Universum` launches build steps in its own working directory that may be changed for every run
    and therefore cannot be hardcoded in Universum configuration file. Also, if not stated otherwise,
    project sources are copied to a temporary directory that will be deleted after a run.
    This directory may be created in different places depending on various `Universum` settings
    (not only the `working directory`, mentioned above), so the path to this directory
    can not be hardcoded too.

The :mod:`universum.configuration_support` module processes current `Universum` run settings and returns
actual project root to the config processing module.

See the following example configuration file:

.. testcode::

    from universum.configuration_support import Configuration, Step, get_project_root

    configs = Configuration([Step(name="Run tests", directory="/home/scripts",
                                  command=["./run_tests.sh", "--directory", get_project_root()])])

In this configuration a hypothetical external script `"run_tests.sh"` requires absolute path
to project sources as an argument. The :func:`get_project_root` will pass the actual project root,
no matter where the sources are located on this run.

.. note::

    Concatenating :func:`get_project_root` results with any other paths is recommended using
    :func:`os.path.join` function to avoid any possible errors on path joining.


Configuration with several steps
--------------------------------

The `Universum` gets the list of build steps from the `configs` global variable.
In the basic form this variable contains a flat list of items, and each item represents one `build step`_.

Below is an example of the configuration file with three different steps:

.. testcode::

    from universum.configuration_support import Configuration, Step, get_project_root
    import os.path

    test_path = os.path.join(get_project_root(), "out/tests")
    configs = Configuration([
        Step(name="Make Special Module", command=["make", "-C", "SpecialModule/"], artifacts="out"),
        Step(name="Run internal tests", command=["scripts/run_tests.sh"]),
        Step(name="Run external tests", directory="/home/scripts", command=["run_tests.sh", "-d", test_path])
    ])

The example configuration file declares the following `Universum` steps:

1. `Make` a module, located in `"specialModule"` directory
2. Run a `"run_tests.sh"` script, located in `"scripts"` directory
3. Run a `"run_tests.sh"` script, located in external directory `"/home/scripts"`
   and pass an absolute path to a directory `"out/tests"` inside project location
4. Copy resulting directory `"out"` to the artifact directory


.. _dump:

Dump a list of build steps
--------------------------

Class :class:`Configuration` has a build-in function :meth:`~Configuration.dump`, that processes the passed
dictionaries and returns the list of all included build steps.

Below is an example of the configuration file that uses :meth:`~Configuration.dump` function for debugging:

.. testsetup::

    def mock_project_root():
        return "/home/Project"

    import universum.configuration_support
    universum.configuration_support.get_project_root = mock_project_root

.. testcode::

    #!/usr/bin/env {python}

    from universum.configuration_support import Configuration, Step, get_project_root
    import os.path

    test_path = os.path.join(get_project_root(), "out/tests")
    configs = Configuration([
        Step(name="Make Special Module", command=["make", "-C", "SpecialModule/"], artifacts="out"),
        Step(name="Run internal tests", command=["scripts/run_tests.sh"]),
        Step(name="Run external tests", directory="/home/scripts", command=["run_tests.sh", "-d", test_path])
    ])

    if __name__ == '__main__':
        print(configs.dump())

The combination of ``#!/usr/bin/env {python}`` and ``if __name__ == '__main__':`` allows launching
the `Universum` configuration files as a script from shell.

If `Universum` is not installed locally, for ``from universum.configuration_support import`` to work correctly
the configuration file should be copied to local `Universum` root directory and launched there.

When launched from shell instead of being used by `Universum` system, :ref:`get_project_root` function
returns current directory instead of actual project root.

The only thing this script will do is create `configs` variable and print all build steps it includes.
For example, running the script, given above, will result in the following:

.. testcode::
    :hide:

    print("$ ./.univesrum.py")
    print(configs.dump())

.. testoutput::

    $ ./.univesrum.py
    [{'name': 'Make Special Module', 'command': 'make -C SpecialModule/', 'artifacts': 'out'},
    {'name': 'Run internal tests', 'command': 'scripts/run_tests.sh'},
    {'name': 'Run external tests', 'directory': '/home/scripts', 'command': 'run_tests.sh -d /home/Project/out/tests'}]

As second and third steps have the same names, if log files are created, only two logs will be created:
one for the first build step, another for both second and third, where the third will follow the second.


.. _combining:

Combining configurations
------------------------

The :class:`Configuration` class provides a way to generate a full testing scenario by simulating the
combination of different configurations (as in :class:`Configuration` instances).

For this class :class:`Configuration` has built-in ``+`` and ``*`` operators that allow creating
configuration sets out of several :class:`Configuration` instances.


Adding configurations
~~~~~~~~~~~~~~~~~~~~~

See the following example:

.. testcode::

    #!/usr/bin/env {python}

    from universum.configuration_support import Configuration, Step

    one = Configuration([Step(name="Make project", command=["make"])])
    two = Configuration([Step(name="Run tests", command=["run_tests.sh"])])

    configs = one + two

    if __name__ == '__main__':
        print(configs.dump())

The addition operator will just concatenate two lists into one, so the :ref:`result <dump>`
of such configuration file will be the following list of build steps:

.. testcode::
    :hide:

    print("$ ./.univesrum.py")
    print(configs.dump())

.. testoutput::

    $ ./.univesrum.py
    [{'name': 'Make project', 'command': 'make'},
    {'name': 'Run tests', 'command': 'run_tests.sh'}]


Multiplying configurations
~~~~~~~~~~~~~~~~~~~~~~~~~~

Multiplication operator can be used in configuration file two ways:

1. multiplying configuration by a constant
2. multiplying configuration by another configuration

Multiplying configuration by a constant is just an equivalent of multiple additions:

.. doctest::

    >>> run = Configuration([Step(name="Run tests", command=["run_tests.sh"])])
    >>> print (run * 2 == run + run)
    True

Multiplying configuration by a configuration combines their properties. For example, this configuration file:

.. testcode::

    #!/usr/bin/env {python}

    from universum.configuration_support import Configuration, Step

    make = Configuration([Step(name="Make ", command=["make"], artifacts="out")])

    target = Configuration([Step(name="Platform A", command=["--platform", "A"]),
                            Step(name="Platform B", command=["--platform", "B"])])

    configs = make * target

    if __name__ == '__main__':
        print(configs.dump())

will :ref:`produce <dump>` this list of build steps:

.. testcode::
    :hide:

    print("$ ./.univesrum.py")
    print(configs.dump())

.. testoutput::

    $ ./.univesrum.py
    [{'name': 'Make Platform A', 'command': 'make --platform A', 'artifacts': 'out'},
    {'name': 'Make Platform B', 'command': 'make --platform B', 'artifacts': 'out'}]

* `command` and `name` values are produced of `command` and `name` values of each of two configurations
* `artifacts` value, united with no corresponding value in second configuration, remains unchanged

.. note::

    Note the extra space character at the end of the configuration name `"Make "`.
    As multiplying process uses simple adding of all corresponding step settings,
    string variables are just concatenated, so without extra spaces resulting name
    would look like "MakePlatform A". If we add space character, the resulting name
    becomes "Make Platform A".


Combination of addition and multiplication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When creating a project configuration file, the two available operators, ``+`` and ``*``,
can be combined in any required way. For example:

.. testcode::

    #!/usr/bin/env {python}

    from universum.configuration_support import Configuration, Step

    make = Configuration([Step(name="Make ", command=["make"], artifacts="out")])
    test = Configuration([Step(name="Run tests for ", directory="/home/scripts", command=["run_tests.sh", "--all"])])

    debug = Configuration([Step(name=" - Release"),
                           Step(name=" - Debug", command=["-d"])])

    target = Configuration([Step(name="Platform A", command=["--platform", "A"]),
                            Step(name="Platform B", command=["--platform", "B"])])

    configs = make * target + test * target * debug

    if __name__ == '__main__':
        print(configs.dump())

This file :ref:`will get us <dump>` the following list of build steps:

.. testcode::
    :hide:

    print("$ ./.univesrum.py")
    print(configs.dump())

.. testoutput::

    $ ./.univesrum.py
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

Excluding build steps
---------------------

At the moment there is no support for ``-`` operator.
There is no easy way to exclude one of build steps, generated by adding/multiplying.
But there is a conditional including implemented. To include/exclude a `build step` depending on
environment variable, use `if_env_set` key. When script comes to executing a step with such key,
if there's no environment variable with stated name set to either "true", "yes" or "y",the step is not executed.
If any other value should be set, use ``if_env_set="VARIABLE_NAME == variable_value"`` comparison.
Please pay special attention on the absence of any quotation marks around `variable_value`:
if added, `$VARIABLE_NAME` will be compared with `"variable_value"` string and thus fail. Also, please note,
that all spaces before and after `variable_value` will be automatically removed, so
``if_env_set="VARIABLE_NAME == variable_value "`` will be equal to ``os.environ["VARIABLE_NAME"] = "variable_value"``
but not ``os.environ["VARIABLE_NAME"] = "variable_value "``.

`$VARIABLE_NAME` consist solely of letters, digits, and the '_' (underscore) and not begin with a digit.

If such environment variable should not be set to specific value, please use
``if_env_set="VARIABLE_NAME != variable_value"`` (especially ``!= True`` for variables
to not be set at all).

If executing the build step depends on more than one environment variable, use ``&&`` inside `if_env_set` value.
For example, ``if_env_set="SPECIAL_TOOL_PATH && ADDITIONAL_SOURCES_ROOT"`` step will be executed only
in case of both `$SPECIAL_TOOL_PATH` and `$ADDITIONAL_SOURCES_ROOT` environment variables set to some values.
If any of them is missing or not set in current environment, the step will be excluded from current run.
