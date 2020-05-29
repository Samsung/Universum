:orphan:

Non-CI subcommand
-------------------

The purpose of this mode is improving usability of 'Universum' on a local host PC.
This mode is designed to use 'Universum' as a wrapper for a complex build system.
In particular such wrapper could help to resolve the following issues:

- every build command run requires setting up a lot of input parameters
- bash script is used to wrap build system like GNU Make
- universum configs contain duplications of build system wrapper


The 'universum nonci' has the following differences from the regular mode:

- report to code review system, such as 'GitHub' or 'Swarm', is disabled
- version control is disabled
- implemented removing of artifacts before build
- 'Universum' works with sources 'in place', without copying


.. argparse::
    :module: universum.__main__
    :func: define_arguments
    :prog: python3.7 -m universum
    :path: nonci
