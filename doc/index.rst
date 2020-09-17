Project 'Universum'
===================

.. toctree::
    :hidden:

    prerequisites.rst
    guide.rst
    args.rst
    configuring.rst
    configuration_support.rst
    code_report.rst
    github_handler.rst
    universum_docs.rst
    teamcity.rst
    examples.rst
    changelog_ref.rst

.. image:: _static/logo.svg
    :height: 150
    :width: 150
    :align: right

Project `Universum` is a continuous integration framework, containing
a collection of functions that simplify implementation of the
automatic build, testing, static analysis and other steps.
The goal of this project is to provide unified approach for adding continuous integration
to any project. It currently supports Perforce, Git, Gerrit, Swarm, Jenkins and TeamCity.

Sometimes `Universum` system can be referred to as the framework or just CI.

To install Universum, make sure to :doc:`meet prerequisites <prerequisites>` and then simply run
``pip3.7 install -U universum`` from command line.

To :doc:`create an example config and execute it with Universum <create_config>`,
run ``python3.7 -m universum create-config``.
