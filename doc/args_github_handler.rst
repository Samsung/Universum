:orphan:

GitHub Handler command line
---------------------------

These are the parameters of :doc:`github_handler`. For GitHub Handler to work, these parameters are mandatory:

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
