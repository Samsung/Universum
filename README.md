# Project 'Universum'
[![Documentation Status](https://readthedocs.org/projects/universum/badge/?version=latest)](
https://universum.readthedocs.io/en/latest/?badge=latest)

Universum integrates various CI systems and provides additional features,
such as: customized downloading sources from VCS, running tests
described in configuration file and reporting the results to code review systems.

Full documentation can be found here: https://universum.readthedocs.io/

Please check out our [code of conduct](CODE_OF_CONDUCT.md)
and [contribution policy](.github/CONTRIBUTING.md)

Project is executed with `python3.7 -m universum` command.
Independent analyzers are executed with their module name, e.g. `python3.7 -m universum.analyzers.pylint`.
Other Universum modes, such as poller or submitter, are called via command line, e.g.
`python3.7 -m universum poll`

## Installation

Minimum prerequisites ([see documentation for details](https://universum.readthedocs.io/en/latest/install.html)):
1. OS Linux
2. Python version 3.7 or greater
3. Pip version 9.0 or greater
```bash
sudo pip3.7 install -U universum
```
or
```bash
pip3.7 install --user -U universum
```
Can also be installed with [extras for using VCS](
https://universum.readthedocs.io/en/latest/install.html#vcs-related-extras),  but they also require
installing respective command-line tools, such as git or p4.

## Development

In order to prepare the development environment for the Universum, please fulfill the prerequisites,
and then use the commands listed below. Please note we use `venv` to properly select
python interpreter version and to isolate development environment from the system.

Prerequisites:
1. Install all of the VCS extras as described in the [Universum installation manual](
   https://universum.readthedocs.io/en/latest/install.html#vcs-related-extras),
   (including installation of Git and P4 CLI)
2. Install Docker (`docker-ce`, `docker-ce-cli`) as described in the [official installation manual](
   https://docs.docker.com/engine/installation/linux/ubuntu/#install-using-the-repository)

   * Also add current user to 'docker' group (use `sudo usermod -a -G docker $USER` and then relogin)
3. Install Mozilla WebDriver: `sudo apt install firefox-geckodriver`

Further commands:
```bash
python3.7 -m venv virtual-environment-python3.7
source ./virtual-environment-python3.7/bin/activate
git clone https://github.com/Samsung/Universum.git universum-working-dir
cd universum-working-dir
git checkout master
pip install -U .[test]
make images
```
And after this the `pytest` or `make test` commands can be executed (see below).

The `[test]` extra will install/update the following additional Python modules:

    * `sphinx`
    * `sphinx-argparse` (extension for `Sphinx`)
    * `sphinx_rtd_theme` (extension for `Sphinx`)
    * `docker`
    * `httpretty`
    * `mock`
    * `pytest`
    * `pylint`
    * `pytest-pylint`
    * `teamcity-messages` (is not actually used in manual testing, but is there for CI)
    * `pytest-cov`
    * `coverage`
    * `mypy`
    * `types-requests`
    * `selenium`

Although it is possible to get these modules via `pip3.7 install -U universum[test]`, it might be more convenient
to checkout the Universum branch you are currently working on, change working directory to project root and
run a `pip3.7 install -U .[test]` command from there for more flexibility. Using virtual environment (via `venv`
command) allows to separate test environment from system and provides even more control over additional modules.

Uninstalling Universum via `pip uninstall universum` will not uninstall all the dependencies installed along with it.
Simply deleting the directory with virtual environment will leave the system completely cleaned of all changes.

Docker images used in tests can be built manually or using the `make images` command.
Also `make rebuild` command can be used to update images ignoring cache (e.g. to rerun `apt update`).
Commands `make images` and `make rebuild` use Python version set in execution environment; to build images
for another supported Python version, please use environment variable `PYTHON`, e.g.:
```
PYTHON=python3.8 make images
```
Currently the following values of the `PYTHON` environment variable are supported:
'python3.6', 'python3.7' and 'python3.8'.

The `make test` command runs all the tests (including the doctests) and collects coverage. Tests can also be launched
manually via `pytest` command with any required options (such as `-k` for running tests based on keywords
or `-s` for showing the suppressed output).

To test Univesrum for all supported Python versions, please run:
```
pip install -U nox
cd universum-working-dir
nox
```
This will launch the testing scenario, described in `noxfile.py`. This scenario includes rebuilding docker images
for every supported Python version and running all the tests for corresponding Python.

Also, setting up "REUSE_DOCKER_CONTAINERS" environment variable (or running tests in PyCharm) will let tests
reuse already created and initialized containers, which speeds up the testing process. But do note that this is
recommended for development purposes only. Without recreating containers, the remnants of previous test runs
may affect the current test run.


## Project contents

`universum` is main project folder, that is being copied to Python libraries location
(e.g. `dist-packages` or `site-packages`) when installed.
It contains `__main__.py` script, that is the main entry point to the whole project.
It also contains the following modules:
* `main`/`poll`/`submit`/`api`/`nonci` - managing modules for different Universum modes
* `configuration_support` - special module for [configuring the project](
https://universum.readthedocs.io/en/latest/configuring.html)
* `analyzers` directory is not quite a part of Universum itself. It contains [independent scripts](
https://universum.readthedocs.io/en/latest/code_report.html) compatible with Universum
for implementing static (and other types of) analysis support.
* `lib` - utility functions libraries

  * `ci_exception` - internal exceptions
  * `module_arguments` - handles [command line](
    https://universum.readthedocs.io/en/latest/args.html) and other parameters
  * `gravity` - inter-module communication
  * `utils` - miscellaneous

* `modules` - independent packages

  * `api_support` - 'main' mode module to answer API requests
  * `automation_server` - drivers for CI systems (e.g. Jenkins)
  * `artifact_collector` - implements [build artifacts](
    https://universum.readthedocs.io/en/latest/configuring.html#common-variations-keys)
  * `code_report_collector` - support for [external 'code report' modules](
    https://universum.readthedocs.io/en/latest/code_report.html)
  * `launcher` - executes build scenario, described in [project configuration file](
    https://universum.readthedocs.io/en/latest/configuring.html)
  * `output` - drivers for environment-based logs
  * `project_directory` - interaction with host file system
  * `reporter` - interaction with code review systems
  * `structure_handler` - execution 'blocks' isolation, order, reporting, etc.
  * `vcs` - CI target sources preparation

Also there are 'base' modules/classes for driver implementation standardization,
and 'main' modules/classes for automated driver choosing based on environment and settings.

`doc` directory contains sources for [project documentation](
https://universum.readthedocs.io/en/latest/index.html). It can be generated
locally with running `make` from root directory using Sphinx.

`tests` directory contains test system, based on PyTest. Full tests can be started
from root directory via `make tests` command, otherwise use standard PyTest syntax.
*Commits failing any of project tests should not be merged into 'master' branch!*

`examples` contains various examples of [project configuration files](
https://universum.readthedocs.io/en/latest/configuring.html). Usage of such files
is illustrated in `run_basic_example.sh` script.

`setup.py` is 'setuptools' configuration file, and shouldn't be executed on its own.

## Quick architecture overview

1. Project only entry point (except ['analyzers'](https://universum.readthedocs.io/en/latest/code_report.html))
   is `universum.py`. Based on chosen execution mode (default, submitting, polling, etc.)
   it calls one of 'main' modules, passing them all parameters
2. Universum is a set of separate modules, each implementing its own piece of functionality.
   They are connected using special `gravity` library
3. All classes, inherited from `Module` (defined in `gravity`), automatically can:

   * use `Dependency` mechanism to use other modules
   * describe any module parameters in `define_arguments()` and receive them parsed via `self.settings`

4. `configuration_support` is, in fact, an 'external' module, used not only by Universum,
   but by [user configuration file](https://universum.readthedocs.io/en/latest/configuring.html)
   for generating project configuration
5. 'Base' classes are virtual, not implementing any actual functionality, but describing
   the structure of inherited classes and ensuring they have all required functions
   that will be called by modules using them

## Project review slides

Some additional details on how project is developed could be found in
[project review slides](doc/Universum_ProjectReview_2021-03.pdf)

## Contributing

Further versions of this README file should include:

1. Notification on mandatory code review for all commits to master
2. Notification on mandatory documenting of the newly added features
3. Description of CI process, links to configurations/logs/build results/etc.
