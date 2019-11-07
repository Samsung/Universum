:orphan:

Non-CI subcommand
-------------------

The purpose of this mode is improving usability of 'Universum' on a local host PC.
This mode is designed to use 'Universum' as a wrapper for a build system.
It could be useful for projects in which build system usage is complicated or unfriendly for user.
For example:

- every build command run requires to setup a lot of input parameters
- get rid of numerous bash scripts which wraps a build system like GNU Make


The 'universum nonci' has the following differences from 'default':

- report to code review system, such as 'GitHub' or 'Swarm', is disabled
- version control is disabled
- implemented removing of artifacts before build
- 'Universum' works with sources 'in place', without copying


.. argparse::
    :module: universum
    :func: define_arguments
    :prog: universum
    :path: nonci
