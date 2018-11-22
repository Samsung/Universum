Change log
==========

0.16.1 (2018-11-22)
-------------------

New features
~~~~~~~~~~~~

* **code_report:** replace wildcards with directory names processing for Uncrustify
* **code_report:** add regexp support in pattern filter for Uncrustify

Bug fixes
~~~~~~~~~

* **p4:** fix 'Related Change IDs' bug with wrong current review determining


0.16.0 (2018-11-07)
-------------------

New features
~~~~~~~~~~~~

* **launch:** add critical background steps
* **vcs:** make VCS-related packages (e.g. :mod:`gitpython`) not reqired if not used
* **code_report:** add separate entry points for all :doc:`static analysers <code_report>`
* **code_report:** add :ref:`Uncrustify <code_report#uncrustify>` static analyser
* **out:** add pretty step numbering padding

Bug fixes
~~~~~~~~~

* **args:** fix required argument check to not accept empty values as valid
* **launcher:** finish background steps after foreground steps failing
* **out:** add reporting failed background steps to TC


0.15.4 (2018-09-26)
-------------------

Bug fixes
~~~~~~~~~

* **swarm:** fix not adding current Swarm CL number to list of CLs to unshelve


0.15.3 (2018-09-26)
-------------------

Bug fixes
~~~~~~~~~

* **swarm:** fix '[Related change IDs]' parsing


0.15.2 (2018-09-26)
-------------------

New features
~~~~~~~~~~~~

* **swarm:** add '[Related change IDs]' parsing for Swarm reviews


0.15.1 (2018-09-17)
-------------------

BREAKING CHANGES
~~~~~~~~~~~~~~~~

* **create unified entry point for all universum subcommands.**
  New usage is ``universum poll`` and ``universum submit``

New features
~~~~~~~~~~~~

* **launcher:** add :ref:`'finish_background' <finish_background>` key to Variations

Bug fixes
~~~~~~~~~

* **submit:** fix p4 submit fails for files opened in another workspace


0.15.0 (2018-09-04)
-------------------

BREAKING CHANGES
~~~~~~~~~~~~~~~~

* **swarm:** stop legacy support of 'SHELVE_CHANGELIST' environment variable
  for Swarm CL number

Bug fixes
~~~~~~~~~

* **jenkins:** fix Jenkins relative artifact paths/links


0.14.7 (2018-08-17)
-------------------

New features
~~~~~~~~~~~~

* **out:** add Jenkins plug-in specific labels for log collapsing


0.14.6 (2018-08-15)
-------------------

New features
~~~~~~~~~~~~

* **review:** add '--build-only-latest' option for skipping
  review builds of not latest review revisions
* add hidden '--clean-build' option for repeated debugging


0.14.5 (2018-08-09)
-------------------

New features
~~~~~~~~~~~~

* **swarm:** rename environment variable for Swarm CL ('SWARM_CHANGELIST')
  old name is still supported though


0.14.4 (2018-08-03)
-------------------

Bug fixes
~~~~~~~~~

* **swarm:** fix Swarm review revision processing


0.14.3 (2018-08-01)
-------------------

Bug fixes
~~~~~~~~~

* **swarm:** fix latest Swarm review revision detection


0.14.2 (2018-07-30)
-------------------

Bug fixes
~~~~~~~~~

* **gerrit:** add exceptions on wrong Gerrit review parameters
* **swarm:** return voting for specified review version
* **swarm:** add review revision to comment text


0.14.1 (2018-07-23)
-------------------

New features
~~~~~~~~~~~~

* **report:** add '--report-no-vote' option for vote skipping

Bug fixes
~~~~~~~~~

* **configs:** remove outdated code style functions, fix get_project_root
* **code_report:** fix duplication of found issues message
* **launcher:** remove stderr from console output for launcher output type 'file'


0.14.0 (2018-06-25)
-------------------

New features
~~~~~~~~~~~~

* **code_report:** add svace analysis tool
* **main:** add finalizing execution even if interrupted by user
* **main:** add '--finalize-only' option for cleaning without execution
* **artifacts:** add recursive wildcards (**) to artifacts
* **utils:** add PyCharm case to environment detection
* **submit:** fix submitted P4 CL number in logs

Bug fixes
~~~~~~~~~

* **submit:** skip P4 submit if default CL has any files before reconciling
* **setup:** specify httpretty version to avoid SSL import errors


0.13.6 (2018-05-18)
-------------------

New features
~~~~~~~~~~~~

* **p4:** create environment variables for each mapping's sync CL

Bug fixes
~~~~~~~~~

* **docs:** fix change log


0.13.5 (2018-05-10)
-------------------

BREAKING CHANGES
~~~~~~~~~~~~~~~~

* **p4:** remove ``allwrite`` option in p4 client;
  please set '+w' modifier for files in VCS to be edited
* **configs:** :ref:`if_env_set <filtering>` variables should now be splat with ``&&`` only

New features
~~~~~~~~~~~~

* **report:** add support of :ref:`tagging <tc_tags>` TeamCity builds
* **swarm:** ``PASS`` and ``FAIL`` parameters are no longer mandatory
* **submit:** new files are now added to VCS by submitter with '+w' modifier
* **report:** add link to build log to successful reports
* **report:** move link to review to 'Reporting build started' block

Bug fixes
~~~~~~~~~

* **p4:** fix unhandled 'no file(s) to reconcile' P4Exception
* **out:** fix bug with decoding non-ascii strings
* **docs:** documentation fixed and updated; please pay special attention to
  :ref:`prebuild artifact cleaning <clean_artifacts>` `Variations` key


0.13.4 (2018-04-13)
-------------------

New features
~~~~~~~~~~~~

* **code_report:** add number of issues to build status
* **artifacts:** add link to artifact files to build log

Bug fixes
~~~~~~~~~

* **p4:** p4 client now is created with allwrite option
* **gerrit:** report all issues to review with a single request
* **code_report:** return error if pylint is not installed


0.13.3 (2018-03-22)
-------------------

New features
~~~~~~~~~~~~

* **configs:** add :ref:`negative 'if_env_set' values <filtering>`

Bug fixes
~~~~~~~~~

* **add return of exit codes to all main scripts**
* **report:** fix bug with multiple success reporting

0.13.2 (2018-03-07)
-------------------

New features
~~~~~~~~~~~~

* **artifacts:** add CONFIGS_DUMP.txt to build artifacts
* **code_report:** add support for pylint3 for ubuntu14, restore LogWriterCodeReport
* **report:** update build result reporting, add skipped steps
* **report:** add option to only report failed steps

Bug fixes
~~~~~~~~~

* **report:** remove duplicating comment
* **out:** fix skipped steps reporting
* **configs:** fix critical step handling while merging one-element Variations


0.13.1 (2018-02-16)
-------------------

Bug fixes
~~~~~~~~~

* **poll:** fix wrong order of polled changes


0.13.0 (2018-02-14)
-------------------

New features
~~~~~~~~~~~~

* **report:** add driver for processing Jenkins builds
* **launcher:** add critical steps for groups
* **setup:** add entry points for all high level scripts

Bug fixes
~~~~~~~~~

* **files:** fix cleaning sources function in finalize for Git
* **tests:** add stderr and exception/traceback detection
* **tests:** remove pylint error ignoring
* **code_report:** add exit codes for `code_report`


0.12.5 (2018-02-06)
-------------------

Bug fixes
~~~~~~~~~

* **gerrit:** update 'Verified' to work with non-default labels
* **artifacts:** fix exception message when encountering existing artifacts
* **docs:** doc files removed from `master` branch


0.12.4 (2018-01-31)
-------------------

New features
~~~~~~~~~~~~

* **code_report:** implement static analysis support


0.12.3 (2018-01-19)
-------------------

New features
~~~~~~~~~~~~

* **code_report:** add `code_report` stub for further static analysis support
* **tests:** make errors in finalize affect exit code

Bug fixes
~~~~~~~~~

* **docs:** update TeamCity-related documentation
* **tests:** fix docker images makefiles


0.12.2 (2017-12-27)
-------------------

New features
~~~~~~~~~~~~

* **artifacts:** change to shell-style wildcards instead of old limited ones
* **submit:** reconcile files and directories from list
* **submit:** reconcile using wildcards
* **report:** update list of all performed steps, add successful
* **docs:** new :doc:`Variations keys <configuring>` described

Bug fixes
~~~~~~~~~

* **report:** fix reporter message for build started
* **p4:** exit committed CL precommit check wihout failing
* **tests:** remove docker container caching where not necessary
* **tests:** fix import thirdparty detection


0.12.1 (2017-12-11)
-------------------

New features
~~~~~~~~~~~~

* **artifacts:** clean artifacts before build
* **git:** add user and email to Git module parameters

Bug fixes
~~~~~~~~~

* **vcs:** roll back of import fixes from release 0.10.2 causing Swarm builds of submitted CLs to fail
* **tests:** set user and email in testing Git repo


0.12.0 (2017-11-29)
-------------------

BREAKING CHANGES
~~~~~~~~~~~~~~~~

* **swarm:** the ``--swarm`` flag is replaced with ``--report-to-review``.
  All pre-commit check configuration must be updated to reflect this change

Bug fixes
~~~~~~~~~

* **submit:** fix incorrectly back-ported fix from the new architecture,
  which prevented submit to git from working
* **gerrit:** fix bug with accessing url path by incorrect index and with including username
  into url in build log on pre-commit check
* **gerrit:** fix bug with adding apostrophe character (') to the ssh command line
  and failing to submit build start report to gerrit review


0.11.2 (2017-11-24)
-------------------

New features
~~~~~~~~~~~~

* **launcher:** add support for critical steps - now steps can be marked with
  :ref:`"critical" attribute <critical_step>` to fail entire build in case of step failure.
  By default the build continues even if some steps have failed

Bug fixes
~~~~~~~~~

* **submit:** fix setup script to actually install submitter module
  and to create console script called "universum_submit"
* **submit:** add support for executing commit message hooks by using external git utility
  instead of gitpython module (required to submit to gerrit)

Known issues
~~~~~~~~~~~~

* **submit:** commit message hook is not downloaded from gerrit during cloning of the repository.
  As a workaround add installation of commit message hook to configs.py::

    configs += Variations([dict(name="Install commit message hook",
                                command=["scp", "-p", "-P", "29418",
                                         "<user>@<server>:hooks/commit-msg", ".git/hooks/"])])

* **submit:** by default, submit uses "temp" subfolder of the current folder as working directory.
  As a workaroung add the explicit setting of project root to configs.py::

    configs += Variations([dict(name="Submit",
                                command=["universum_submit",
                                         "-pr", get_project_root(),
                                         "--vcs-type", "gerrit",
                                         "--commit-message", "Publish artifacts",
                                         "--file-list", "out/module.bin"])])


0.11.1 (2017-11-22)
-------------------

New features
~~~~~~~~~~~~

* **review:** add link to review page on server to logs
* **docs:** add instructions for TeamCity integration
* **tests:** add gravity tests for cases found by coverage
* **tests:** extend `test_git_poll` test suite with special merging cases

Bug fixes
~~~~~~~~~

* **report:** remove special characters from report message
* **launcher:** fix paths processing


0.11.0 (2017-11-09)
-------------------

New features
~~~~~~~~~~~~

* **submit:** add submit functionality for Git & Gerrit
* **tests:** add coverage report
* **tests:** add test for checking referencing dependencies


0.10.7 (2017-11-07)
-------------------

Bug fixes
~~~~~~~~~

* **gerrit:** resolving issues fixed


0.10.6 (2017-11-06)
-------------------

New features
~~~~~~~~~~~~

* **tests:** add submitter initial tests

Bug fixes
~~~~~~~~~

* **files:** fix module construction order in main module and git `refspec` processing errors


0.10.5 (2017-11-03)
-------------------

New features
~~~~~~~~~~~~

* **files:** add repository state file
* **poll:** add poller for Git and initial tests


0.10.4 (2017-10-17)
-------------------

New features
~~~~~~~~~~~~

* **submit:** add an external script for submitting to repository

Bug fixes
~~~~~~~~~

* **p4:** remove reusing of existing p4 clients


0.10.3 (2017-10-17)
-------------------

Bug fixes
~~~~~~~~~

* **git:** typo fix


0.10.2 (2017-10-10)
-------------------

New features
~~~~~~~~~~~~

* **git:** add `git checkout`, `git cherry-pick` and `refspec` functionality
* **gerrit:** add Gerrit support
* **configs:** add quotes and warning if space is detected within parameter in `command` item

Bug fixes
~~~~~~~~~

* **tests:** make unused vcs module import non-obligatory


0.10.1 (2017-09-22)
-------------------

New features
~~~~~~~~~~~~

* **git:** add initial Git support; change ``--no-sync`` into switch of ``--vcs-type``


Bug fixes
~~~~~~~~~

* **p4:** fix 'Librarian checkout' exceptions


0.10.0 (2017-09-13)
-------------------

New features
~~~~~~~~~~~~

* **p4:** add ``--p4-force-clean`` instead of ``--p4-no-clean`` option:
  p4client is now not deleted by default


Bug fixes
~~~~~~~~~

* **Project 'Universe' renamed into 'Universum' to avoid name duplication**
* **reporter:** TeamCity-related parameters are no longer mandatory


0.9.1 (2017-08-25)
------------------

New features
~~~~~~~~~~~~

* **launcher:** add support for :ref:`custom environment variables values <filtering>`


0.9.0 (2017-08-22)
------------------

New features
~~~~~~~~~~~~

* **Project 'Universe' transformed into a Python module, installable with pip**


Bug fixes
~~~~~~~~~

* **docs:** update documentation on module arguments


0.8.1 (2017-08-03)
------------------

New features
~~~~~~~~~~~~

* **configs:** remove unnecessary nesting of configurations


Bug fixes
~~~~~~~~~

* **launcher:** append sys.path with config_path to import any subsidiary modules
* **report:** fix non-existing report_artifacts processing - ignore non-existing directories
* **launcher:** fix empty variable names - ' & name' is now processed correctly


0.8.0 (2017-07-26)
------------------

New features
~~~~~~~~~~~~

* **CI Framework renamed into project 'Universe'**

* **docs:** add :doc:`description <args>` of main script command-line parameters

Bug fixes
~~~~~~~~~

* **docs:** fix table content width, remove unnecessary scroll bars


0.7.0 (2017-07-21)
------------------

New features
~~~~~~~~~~~~

* **docs:** add :doc:`system prerequisites page <prerequisites>` to user manual
* **docs:** add documentation for :mod:`_universum.configuration_support` module
* **launcher:** add support for more than one environment variable to
  :ref:`filter configurations <filtering>`

Bug fixes
~~~~~~~~~

* **launcher:** fix :ref:`configuration filtering <filtering>`: filter artifacts
  as well as configurations
* **output:** use TeamCity built-in methods of stderr reporting for correct in-block
  error highlighting


0.6.3 (2017-07-13)
------------------

Bug fixes
~~~~~~~~~

* **docs:** fix product name and version display in documentation


0.6.2 (2017-07-11)
------------------

New features
~~~~~~~~~~~~

* **report:** add :ref:`direct links to build artifacts <report_artifacts>` into reports


0.6.1 (2017-07-05)
------------------

New features
~~~~~~~~~~~~

* **files:** add :ref:`working directory <get_project_root>` reference to logs

Bug fixes
~~~~~~~~~

* **p4:** bring back reverting in 'prepare repository' step and add more logs


0.6.0 (2017-07-05)
------------------

New features
~~~~~~~~~~~~

* **launcher:** add :ref:`configuration filtering <filtering>`
* **artifacts:** wildcard initial support


0.5.0 (2017-06-06)
------------------

New features
~~~~~~~~~~~~

* **tests:** add docker-based testing for p4poll
* **launcher:** change stderr printing to real-time instead of united report


0.4.1 (2017-05-30)
------------------

Bug fixes
~~~~~~~~~

* **artifacts:** fix artifacts reference before creation


0.4.0 (2017-05-30)
------------------

New features
~~~~~~~~~~~~

* **artifacts:** artifacts are now collected to a separate directory
* **main:** add version numbering


0.3.0 (2017-05-25)
------------------

New features
~~~~~~~~~~~~

* **swarm:** less default comments to Swarm, more optional
* **tests:** add pylint check
* **tests:** add doctest collecting

Bug fixes
~~~~~~~~~

* **test:** fix bug with stopping all test types once one type detects failure
* **swarm:** fix reporting to Swarm builds that did not execute actual build steps
* **launcher:** fix artifact collecting interruption
* **launcher:** fix extra dot directory in artifact archives


0.2.1 (2017-05-17)
------------------

Bug fixes
~~~~~~~~~

* **swarm:** Swarm double prefixes fixed


0.2.0 (2017-05-16)
------------------

New features
~~~~~~~~~~~~

* **p4:** switch to disposable workspaces
* **p4:** add multiple VCS roots support
* **poll:** add perforce server polling to trigger builds by opening specified URL
* **tests:** add test stub
* **tests:** switch to py.test

Bug fixes
~~~~~~~~~

* **p4:** fix argument processing & list sorting
* **p4:** add p4client name changing
* **tests:** fix configs.py
* **tests:** add missing thirdparty dependency - module 'py'


0.1.1 (2017-04-26)
------------------

Bug fixes
~~~~~~~~~

* **output:** add warnings display


0.1.0 (2017-04-26)
------------------

New features
~~~~~~~~~~~~

* **docs:** add change log
* **launcher:** add asynchronous step execution
* **docs:** update system configuring manual

Bug fixes
~~~~~~~~~

* **launcher:** change default 'command' launch directory back to project root
