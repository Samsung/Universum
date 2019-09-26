This is a test change
One more change



# Project 'Universum'
[![Documentation Status](https://readthedocs.org/projects/universum/badge/?version=latest)](
https://universum.readthedocs.io/en/latest/?badge=latest)

Universum integrates various CI systems and provides additional features,
such as: customized downloading sources from VCS, running tests
described in configuration file and reporting the results to code review systems.

Full documentation can be found here: https://universum.readthedocs.io/

Please check out our [code of conduct](CODE_OF_CONDUCT.md)
and [contribution policy](.github/CONTRIBUTING.md)

## Installation from GitHub

### Latest release

Minimum prerequisites ([see documentation for details](
https://universum.readthedocs.io/en/latest/prerequisites.html)):
1. OS Linux
2. Python 2.7
3. Pip for python2
4. Git client
```bash
sudo python2 -m pip install git+https://github.com/Samsung/Universum/@release -U
```
### Latest development + tests

Additional prerequisites ([see documentation for details](
https://universum.readthedocs.io/en/latest/prerequisites.html#optional-used-for-internal-tests)):
1. Perforce CLI, P4Python (['helix-cli' and 'perforce-p4python'](
https://www.perforce.com/manuals/p4sag/Content/P4SAG/install.linux.packages.install.html))
2. Docker (['docker-ce', 'docker-ce-cli'](
https://docs.docker.com/install/linux/docker-ce/ubuntu/#install-docker-ce))
3. Current user added to 'docker' group (use `sudo usermod -a -G docker $USER` and then relogin)
```bash
git clone https://github.com/Samsung/Universum.git universum-working-dir
cd universum-working-dir
git checkout master
pip install .[test] -U
make images
```
After this run `make tests` and ensure all tests are passing.

Also note that running `pip uninstall universum` will remove Universum itself,
but all the dependency modules will remain in the system.

## Project contents

`universum.py` is project executable. It uses the following modules from `_universum` directory:
* `main`/`poll`/`submit`/`api` - managing modules for different Universum modes
* `configuration_support` - special module for [configuring the project](
https://universum.readthedocs.io/en/latest/configuring.html)
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

`analyzers` directory is not a part of Universum itself. It contains [example external scripts](
https://universum.readthedocs.io/en/latest/code_report.html) compatible with Universum
for static (and other types of) analysis.

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

## Contributing

Further versions of this README file should include:

1. Notification on mandatory code review for all commits to master
2. Notification on mandatory documenting of the newly added features
3. Description of CI process, links to configurations/logs/build results/etc.
