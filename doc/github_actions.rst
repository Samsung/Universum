Integration with GitHub Actions
===============================

`Universum` requires no special integration with `GitHub Actions <https://docs.github.com/en/actions>`_. It is usually
launched as one long step in a single build stage.

.. warning::

    'GitHub Actions' CI system is not compatible with ``report_artifacts`` :doc:`configuration Step key <configuration_support>`.
    If this key is set nevertheless, links to artifacts will be posted, but won't work.


Command line
------------

Here's an example of a comman line to be used for running Universum in GitHub Actions::

    python -m universum --vcs-type=git --git-repo "${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}" --git-refspec "${GITHUB_REF_NAME}"

All environment variables mentioned in the example are `GitHub Environment variables
<https://docs.github.com/en/actions/learn-github-actions/environment-variables>`_.

`Universum` also supports reporting to code review systems ('--report-to-review' option) from 'GitHub Actions'. Link to
build is created using environment variables and do not require any additional command line parameters.

Logs
----

GitHub Actions web interface currently supports single-level grouping of log lines
(`without nesting <https://github.com/actions/runner/issues/802>`_). Because of that, Universum logs are printed 
as follows: an already opened group is closed if any other (including nested) group is opened.


Artifacts
---------

Artifacts can be stored in GitHub Actions with explicitly provided name via separate workflow step.
It is possible to store multiple files in a single `artifact
<https://docs.github.com/en/actions/using-workflows/storing-workflow-data-as-artifacts>`_, but it is not possible to
retrieve only one file from such artifact. This leads to the following limitations:

    - links to artifacts can only be retrieved after artifact creation (which happens after `Universum` run)
    - links to single artifact files cannot be provided at all

This is the reason the ``report_artifacts`` key can not be processed correctly and shouldn't be set in configuration.
