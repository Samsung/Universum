Integration with GitHub Actions
===============================

`Universum` requires no special integration with `GitHub Actions <https://docs.github.com/en/actions>`_. It is usually
launched as one long step in a single build stage.

.. warning::

    GitHub Actions doesn't support `report_artifacts` key in configuration.

Command line
------------

To use `universum` to check-out current repository (the repository that contains the GitHub Action workflow) is
necessary to use `GitHub Environment variables
<https://docs.github.com/en/actions/learn-github-actions/environment-variables>`_:
``python -m universum --vcs-type=git --git-repo $GITHUB_SERVER_URL/$GITHUB_REPOSITORY --git-refspec $GITHUB_REF_NAME``

`Universum` also supports reports to review from GitHub Actions. Link to build are created using environment variables
and do not require any additional command line parameters.

Logs
----

Github Actions currently supports single-level grouping of log lines
(`without nesting <https://github.com/actions/runner/issues/802>`_). Accordingly, logs is printed with next
restrictions: previously opened group is closed when a nested group is opened.

Artifacts
---------

Artifacts in GitHub Actions can be store, with the specified name, using an separate step in GitHub Actions workflow.
It is possible to store multiple files in a single artifact, but it is not possible to retrieve only one file from an
artifact. Because of these facts, it is not possible to provide references to artifacts without first creating them,
and therefore the ``report_artifacts`` key in the configuration is not supported for GitHub Actions.
