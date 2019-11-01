:orphan:

Non-CI subcommand
-------------------

Purpose of this mode is running 'Universum' configurations locally.
This mode is designed to use Universum as part of build system.
When 'Universum' running in this mode, the following CI-related features disabled:

- reporting (to review board for example)
- strict verifying of artifacts before build
- running build scripts within a temporary project directory when VCS is none

However you still have pretty build result summary.


.. argparse::
    :module: universum
    :func: define_arguments
    :prog: universum
    :path: nonci
