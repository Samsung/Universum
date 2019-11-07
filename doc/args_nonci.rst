:orphan:

Non-CI subcommand
-------------------

The purpose of this mode is running 'Universum' on local host PC.
This mode is designed to use Universum as part of build system.
The 'universum nonci' has the following differences from 'default':

- report to CI service is disabled
- VCS usage is disabled
- clean artifacts before build
- sources isn't copied unlike '-vcs=none'


.. argparse::
    :module: universum
    :func: define_arguments
    :prog: universum
    :path: nonci
