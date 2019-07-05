# Project 'Universum'
[![Documentation Status](https://readthedocs.org/projects/universum/badge/?version=latest)](
https://universum.readthedocs.io/en/latest/?badge=latest)

Universum integrates various CI systems and provides additional features,
such as: customized downloading sources from VCS, running tests
described in configuration file and reporting the results to code review systems.

Full documentation can be found here: https://universum.readthedocs.io/

Please check out our [code of conduct](CODE_OF_CONDUCT.md)
and [contribution policy](.github/CONTRIBUTING.md)

# Installation from GitHub

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

## Plan for improving README

Further versions of this README file should include:

1. Instructions for Universum developers:
   * What to install
   * How to set up
   * How to run tests
   * Minimal architecture overview
2. Notification on mandatory code review for all commits to master
3. Notification on mandatory documenting of the newly added features
3. Description of CI process, links to configurations/logs/build results/etc.
