Universum modes
===============

Along with default mode Universum provides the following useful additional commands:

* `init <additional_commandst#init>`_
* `run <additional_commandst#run>`_
* `poll <additional_commandst#poll>`_
* `submit <additional_commandst#submit>`_
* `github-handler <additional_commandst#github-handler>`_


.. _additional_commandst#init:

Initialize Universum
--------------------

If you have Universum installed via ``{pip} install -U universum`` or downloaded it from GitHub and changed
working directory to project root, run ``{python} -m universum init`` to create an example configuration file,
that can be :doc:`updated according to your project needs <configuring>` later.

Running this command will not only create a configuration file, but will also provide you with a command line to
execute it with Universum.


.. _additional_commandst#run:

Run Universum locally (Non-CI mode)
-----------------------------------

The ``{python} -m universum run`` subcommand uses provided :doc:`Universum config <configuring>` to execute
the set up scenario locally. This allows to easily perform all required checks *before* submitting a change
to VCS. This mode can generally be used as a wrapper for a complex build system.

Universum in non-CI mode has the following differences from default mode:

* does not require most of :doc:`build parameters <args>` - especially the VCS-related ones
* does not :doc:`report build results <code_report>` to any code review system
* works with sources 'in place', without copying
*  automatically :ref:`cleans the artifact folder <clean_artifacts>` before the build

.. argparse::
    :module: universum.__main__
    :func: define_arguments
    :prog: {python} -m universum
    :path: run


.. _additional_commandst#poll:

Poll chosen VCS for updates
---------------------------

.. TODO: Add description

Here are the parameters for poller mode:

.. argparse::
    :module: universum.__main__
    :func: define_arguments
    :prog: {python} -m universum
    :path: poll


.. _additional_commandst#submit:

Detect changes and submit them automatically
--------------------------------------------

.. TODO: Add description

Here are the parameters for submitter mode:

.. argparse::
    :module: universum.__main__
    :func: define_arguments
    :prog: {python} -m universum
    :path: submit


.. _additional_commandst#github-handler:

GitHub Handler
--------------

:doc:`GitHub Handler <github_handler>` is a Universum mode that serves as GitHub Application, helping
to perform and report checks on new commits to a repository. It can create new check runs on GitHub and trigger
an already set up automation server to perform these checks. GitHub Handler parses all required params and
passes them to the triggered builds.

For GitHub Handler to work, these parameters are mandatory:

* ``--payload``
* ``--event``
* ``--trigger-url``
* ``--github-app-id``
* ``--github-private-key``

These and other parameters are described below.

.. argparse::
    :module: universum.__main__
    :func: define_arguments
    :prog: {python} -m universum
    :path: github-handler
