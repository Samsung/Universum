Getting started
===============

1. Step one: :doc:`install Universum <install>`. Use ``{python} -m universum --help`` to make sure the installation
   was successful, and also to get the list of available :doc:`parameters <args>`.

2. Step two: :ref:`initialize Universum <additional_commandst#init>` by creating a default :doc:`configuration
   file <configuring>` and modifying it according to the project needs.

3. Step three: use ``{python} -m universum run`` to :ref:`check the provided configuration
   locally <additional_commandst#run>`.

4. Step four: submit a working configuration file to a VCS and pass required :doc:`parameters <args>` to `Universum`
   to work with it.

5. Configure CI, using `Universum`, on a CI server. See the following guides for :doc:`TeamCity <teamcity>` or
   :ref:`GitHub <github_handler#jenkins>`.
