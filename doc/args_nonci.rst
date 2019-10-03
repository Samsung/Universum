:orphan:

Non-CI command line
-------------------

An aim of this command is using 'Universum' as add-on for build system.


What problem this command resolves?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This command cound be useful for projects which supports a lot of build configurations and target platforms/devices.
Build system usage of such projects could be difficult and CI scripts usually contain duplications of build scripts.
However such problem can be resolved by moving build configuration functionality to CI scripts.
In this cause it's possible to use exactly same system for CI and build.

.. argparse::
    :module: universum
    :func: define_arguments
    :prog: universum
    :path: nonci
