Integration with GitHub Actions
===============================

`Universum` requires no special integration with `GitHub Actions <https://docs.github.com/en/actions>`_. It is usually
launched as one long step in a single build stage.

.. warning::

    GitHub Actions doesn't support `report_artifacts` key in configuration. If set, a broken link will be created.

Command line
------------

`Universum` command line example that can be used in GitHub Actions (see `GitHub Environment variables
<https://docs.github.com/en/actions/learn-github-actions/environment-variables>`_):
::
    python -m universum --vcs-type=git --git-repo "${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}" --git-refspec "${GITHUB_REF_NAME}"

`Universum` also supports reporting to code review systems ('--report-to-review' option) from GitHub Actions. Link to
build is created using environment variables and do not require any additional command line parameters.

Logs
----

Github Actions currently supports single-level grouping of log lines
(`without nesting <https://github.com/actions/runner/issues/802>`_). Because of that, Universum logs are printed using
the following rules: an already opened group is closed if any other (including nested) group is opened.


Artifacts
---------

Artifacts can be stored with explicitly provided name in GitHub Actions via separate workflow step.
It is possible to store multiple files in a single `artifact
<https://docs.github.com/en/actions/using-workflows/storing-workflow-data-as-artifacts>`_, but it is not possible to
retrieve only one file from an artifact. Because of these limitations it is not possible to provide references to
artifacts without first creating them, and therefore the ``report_artifacts`` key can not be processed correctly and
shouldn't be set in configuration.