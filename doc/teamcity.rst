Integration with TeamCity
=========================

The main design goal of Universum is to :doc:`integrate with various CI systems <index>`.
E.g. continuous integration/automation, version control, static analysis, testing, etc.

One of popular continuous integration systems is TeamCity, and this particular tutorial will explain
how to integrate it with Universum.

The proposed scenario includes the following steps:

0. Install and configure both TeamCity and Universum systems, prepare TeamCity build servers for
   project building/running/testing/etc.

#. Create a project on TeamCity. Configure common parameters for the project:

        a) project parameters, if any
        b) parameters for Universum

   TeamCity configurations automatically inherit all project settings,
   so configuring them once on project-level allows to avoid multiple reconfiguring
   of same parameters in each configuration, and all changes applied to project settings
   are automatically applied to all inherited settings

#. Create a common
   `TeamCity meta-runner <https://confluence.jetbrains.com/display/TCD8/Working+with+Meta-Runner>`_.
   TeamCity offers two ways of using meta-runners:

        a) creating a new configuration out of existing meta-runner
        b) using an existing meta-runner as a build step

   Both of this scenarios have their own benefits: when creating a configuration, all parameters
   are inherited too; but when using a build step, any change in meta-runner automatically
   affects all configurations using it

#. Create all needed configurations, such as:

        * precommit check
        * postcommit check
        * testing
        * etc.

This scenario pays a lot of attention to reusing settings instead of just copying them.
It is most important in cases when some of these settings have to be changed: if generalized
on project level, there's only one place to fix. And if all similar settings are duplicated,
tracking changes becomes more difficult the more times they are copied.


Install Universum on build agents
---------------------------------

0. Download Universum sources to the build server
#. Install Universum on build server by running ``sudo pip install .`` in Universum sources root directory
#. Install and configure TeamCity server
#. Install build agents on build server, add them to the project pool

Please refer to
`TeamCity official manuals <https://www.jetbrains.com/teamcity/documentation/>`_ for details.


Create a top-level project
--------------------------

0. Create new project for all Universum configurations or add a sub-project to an existing one
#. Go to `Parameters` section in Project Settings and add the following parameters:

    :env.BUILD_ID: ``%teamcity.build.id%``
    :env.CONFIGURATION_ID: ``%system.teamcity.buildType.id%``
    :env.TEAMCITY_SERVER: server URL to refer to in reports
    :env.CONFIGURATION_PARAMETERS: will be used in meta-runner; leave empty so far

Making all projects using Universum sub-projects to this one will automatically add all these
parameters to their settings.


Create a common meta-runner
---------------------------

0. Create an .xml file with the following content::

    <?xml version="1.0" encoding="UTF-8"?>
    <meta-runner name="Run build using CI system">
      <description>Basic project configuration</description>
      <settings>
        <build-runners>
          <runner name="Download and run" type="simpleRunner">
            <parameters>
              <param name="script.content"><![CDATA[
    #!/bin/bash

    EXITCODE=0

    HOST=`hostame | sed -e "s/_/-/"`
    USER=`whoami | sed -e "s/_/-/"`
    P4CLIENT="Disposable_workspace_"$HOST"-"$USER

    cmd="universum --p4-client ${P4CLIENT} --p4-force-clean %env.CONFIGURATION_PARAMETERS%"
    echo "==> Run: ${cmd}"
    ${cmd} || EXITCODE=1

    echo "##teamcity[setParameter name='STOPPED_BY_USER' value='false']"

    exit $EXITCODE]]></param>
              <param name="teamcity.step.mode" value="default" />
              <param name="use.custom.script" value="true" />
            </parameters>
          </runner>
          <runner name="Clean" type="simpleRunner">
            <parameters>
              <param name="script.content"><![CDATA[
    #!/bin/bash

    if [ %STOPPED_BY_USER% == true ]
    then
    echo "==> User interrupted, force cleaning"

    EXITCODE=0

    HOST=`hostame | sed -e "s/_/-/"`
    USER=`whoami | sed -e "s/_/-/"`
    P4CLIENT="Disposable_workspace_"$HOST"-"$USER

    cmd="python -u ./universum.py --p4-client ${P4CLIENT} --p4-force-clean %env.CONFIGURATION_PARAMETERS% --finalize-only --artifact-dir finalization_artifacts"
    echo "==> Run: ${cmd}"
    ${cmd}

    else
    echo "==> Additional cleaning not needed, skipping"
    fi
              ]]></param>
              <param name="teamcity.step.mode" value="execute_always" />
              <param name="use.custom.script" value="true" />
            </parameters>
          </runner>
        </build-runners>
      </settings>
    </meta-runner>

.. note::
    Universum default VCS type is Perforce, so this meta-runner is oriented to be used with P4.
    But the same meta-runner can be used for configurations using any other VCS type.
    Unused P4 parameters will be just ignored.

1. In `Project Settings` find `Meta-Runners` page and press ``Upload Meta-Runner``
#. Select your newly created .xml file as a `Meta-Runner file`


Configure project using Perforce
--------------------------------

0. Create a sub-project to a created earlier top-level project
#. Go to `Parameters` in `Project Settings`
#. Add ``env.CONFIG_PATH``: a relative path to project :doc:`configuration file <configuring>`,
   starting from project root
#. Also add all required project-wide Perforce parameters:

        :env.P4USER: Perforce user ID
        :env.P4PASSWD: user <env.P4USER> password
        :env.P4PORT: Perforce server URL (including port if needed)
        :env.P4_MAPPINGS: Perforce mappings in :doc:`special format <args>`.
            Also can be replaced with legacy ``env.P4_PATH`` (but not both at a time)


Create basic postcommit configuration
-------------------------------------

0. After creating new build configuration, go to `Build Configuration Settings`
#. To get artifacts from default artifact directory, go to `General Settings`,
   find `Artifact paths` field and add ``artifacts/*`` line there
#. To trigger builds via TeamCity but download via Universum, go to `Version Control Settings`,
   attach required
   `VCS Root <https://confluence.jetbrains.com/display/TCD9/VCS+root>`_
   and set `VCS checkout mode` to ``Do not checkout files automatically``
#. Go to `Triggers` and add `VCS Trigger` with required settings
#. Go to `Build steps`, press ``Add build step``, in `Runner type` scroll down to
   your project runners and select a meta-runner created earlier

After setting up all the environment variables right, you must get the fully working configuration.


Create configuration for custom builds
--------------------------------------

0. As in postcommit, specify ``artifacts/*`` in `Artifact paths`
   and add your meta-runner as a `Build step`
#. Attaching `VCS root` is not necessary because custom build configurations
   usually do not use `VCS Trigger`; instead of this, add the following parameters to configuration:

    :env.SYNC_CHANGELIST: can be a CL number or a list of sync CLs for several different `P4_MAPPINGS`,
        see :doc:`'--p4-sync' option description <args>`
    :env.SHELVE_CHANGELIST: one or several coma-separated CLs to unshelve for the build


Integrate with Swarm
--------------------

0. Go to `Build Configuration Settings` (or to `Project Settings`, if you plan on having
   more than one Swarm-related configuration)
#. Create ``env.REVIEW``, ``env.PASS`` and ``env.FAIL`` parameters and leave them empty
#. In `Build Configuration Settings` --> `Parameters` and add ``--report-to-review`` option in ``env.CONFIGURATION_PARAMETERS``
#. If needed, add other :doc:`Swarm options <args>`, such as ``--report-build-start``
   and ``--report-build-success``
#. Go to Swarm project settings, check in `Automated tests` check-box and follow `this instruction
   <https://www.perforce.com/perforce/r16.2/manuals/swarm/quickstart.integrate_test_suite.html>`_

The resulting URL you should insert in text field. The URL should look like:

    \http://<user>:<password>@<TeamCity URL>/httpAuth/action.html?add2Queue=<configuration>
    &name=env.SHELVE_CHANGELIST&value={change}&name=env.PASS&value={pass}&name=env.FAIL&value={fail}
    &name=env.REVIEW&value={review}

where

    :user: is a name of a TeamCity user triggering Swarm builds (preferably some bot)
    :password: is that user's password
    :TeamCity URL: is actual server URL, including port if needed
    :configuration: is an ID of your Swarm configuration (see ``Build configuration ID`` in settings)

or, if your TeamCity supports anonymous build triggering, `user & password` can be omitted along with
``httpAuth/`` parameter.

#. Probably, in the `POST Body` field you should additionally insert below line:

    \name=STATUS&value={status}

or, any other parameter. This is a workaround for TeamCity requirement for using POST method to trigger builds.

Configure project and configurations using Git
----------------------------------------------

0. Create a sub-project to a top-level project for Universum configurations
#. In `Parameters` set ``env.CONFIG_PATH`` relative to project root
#. Add oject-wide Git parameters:

    :env.GIT_REPO: a parameter to pass to ``git clone``, e.g. ``ssh://user@server/project-name/``
    :env.GIT_REFSPEC: if some non-default
        `git refspec <https://git-scm.com/book/en/v2/Git-Internals-The-Refspec>`_
        is needed for project, specify it here

#. Create post-commit configurations `as described above <Create basic postcommit configuration_>`_
#. When creating custom build configurations, use the following parameters instead of P4-specific:

    :env.GIT_CHECKOUT_ID: parameter to be passed to ``git checkout``; can be commit hash, branch name,
        tag, etc. (see `official manual <https://git-scm.com/docs/git-checkout>`__ for details)
    :env.GIT_CHERRYPICK_ID: one or several coma-separated commit IDs to cherry-pick
        (see `official manual <https://git-scm.com/docs/git-cherry-pick>`__ for details)
