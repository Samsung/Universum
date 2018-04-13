Change log
==========

0.13.5 (2018-04-??)
-------------------


0.13.4 (2018-04-13)
-------------------

New features
~~~~~~~~~~~~

* **code report:** add number of issues to build status
* **artifacts:** add link to artifact files to build log

Bug fixes
~~~~~~~~~

* **p4:** p4 client now is created with allwrite option
* **gerrit:** report all issues to review with a single request
* **code report:** return error if pylint is not installed


0.13.3 (2018-03-22)
-------------------

New features
~~~~~~~~~~~~

* **config:** add :ref:`negative 'if_env_set' values <filtering>`

Bug fixes
~~~~~~~~~

* **add return of exit codes to all main scripts**
* **report:** fix bug with multiple success reporting

0.13.2 (2018-03-07)
-------------------

New features
~~~~~~~~~~~~

* **artifacts:** add CONFIGS_DUMP.txt to build artifacts
* **reporter:** add support for pylint3 for ubuntu14, restore LogWriterCodeReport
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
* **launcher:** critical steps for groups
* **setup:** add entry points for all high level scripts

Bug fixes
~~~~~~~~~

* **files:** fix cleaning sources function in finalize for Git
* **tests:** add stderr and exception/traceback detection
* **tests:** remove pylint error ignoring
* **report:** add exit codes for code report


0.12.5 (2018-02-06)
-------------------

Bug fixes
~~~~~~~~~

* **gerrit:** update 'Verified' to work with non-default labels
* **docs:** doc files removed from master
* **artifacts:** fix exception message when encountering existing artifacts


0.12.4 (2018-01-31)
-------------------

New features
~~~~~~~~~~~~

* **report:** implement static analysis (CL 12985863)


0.12.3 (2018-01-19)
-------------------

New features
~~~~~~~~~~~~

* **report:** add code report executor (CL 12860825)
* **tests:** make errors in finalize affect exit code (CL 12878366)

Bug fixes
~~~~~~~~~

* **docs:** update TeamCity-related documentation (CL 12915420)
* **tests:** fix docker images makefiles (CL 12922742)


0.12.2 (2017-12-27)
-------------------

New features
~~~~~~~~~~~~

* **submit:** reconcile files and directories from list (CL 12710825)
* **submit:** reconcile using wildcards (CL 12758317)
* **artifacts:** change to shell-style wildcards instead of old limited ones (CL 12757961)
* **report:** update list of all performed steps, add successful (CL 12767801)
* **docs:** new :doc:`Variations keys <configuring>` described (CL 12759230)

Bug fixes
~~~~~~~~~

* **report:** fix reporter message for build started (CL 12740827)
* **p4:** exit committed CL precommit check wihout failing (CL 12769930)
* **tests:** remove docker container caching where not necessary (CL 12683160)
* **tests:** fix import thirdparty detection (CL 12711385)


0.12.1 (2017-12-11)
-------------------

New features
~~~~~~~~~~~~

* **artifacts:** clean artifacts before build (CL 12646340)
* **git:** add user and email to Git module parameters (CL 12670277)

Bug fixes
~~~~~~~~~

* **vcs:** roll back of import fixes from CL12362747 causing Swarm builds of submitted CLs to fail (CL 12655701)
* **git:** set user and email in testing Git repo (CL 12670234)


0.12.0 (2017-11-29)
-------------------

Bug fixes
~~~~~~~~~

* **git-submit:** fix incorrectly back-ported fix from the new architecture,
  which prevented submit from working
* **gerrit:** fix bug with accessing url path by incorrect index and with including username
  into url in build log on pre-commit check
* **gerrit:** fix bug with adding apostrophe character (') to the ssh command line
  and failing to submit build start report to gerrit review

BREAKING CHANGES
~~~~~~~~~~~~~~~~

* **swarm:** the "--swarm" flag is replaced with "--report-to-review".
  All pre-commit check configuration must be updated to reflect this change.


0.11.2 (2017-11-24)
-------------------

New features
~~~~~~~~~~~~

* **launcher:** add support for critical steps - now steps can be marked with
  :ref:`"critical" attribute <critical_step>` to fail entire build in case of step failure.
  By default the build continues even if some steps have failed.

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

* **gravity:** add support for additional parameters in __init__, add tests for cases found by coverage (CL 12546563)
* **tests:** extend "test_git_poll" test suite with special merging cases (CL 12556440)
* **review:** add link to review page on server to logs (CL 12558908)
* **docs:** add instructions for TeamCity integration (CL 12575569)
* **tests:** add interacting with P4 to deployment testing (CL 12576315)

Bug fixes
~~~~~~~~~

* **report:** remove special character from report message (CL 12596221)
* **launcher:** fix paths processing (CL 12596388)


0.11.0 (2017-11-09)
-------------------

New features
~~~~~~~~~~~~

* **submit:** add submit functionality for Git (CL 12528642)
* **submit:** add submit functionality for Gerrit (CL 12541410)
* **gravity:** implement dependency injection framework (CL 12527454)
* **coverage:** add coverage report (CL 12541424)
* **tests:** add test for checking referencing dependencies (CL 12534211)


0.10.7 (2017-11-07)
-------------------

Bug fixes
~~~~~~~~~

* **gerrit:** resolving issues fixed (CL 12526893)


0.10.6 (2017-11-06)
-------------------

New features
~~~~~~~~~~~~

* **tests:** add submitter initial tests (CL 12515605)

Bug fixes
~~~~~~~~~

* **files:** fix module construction order in universum.py and git refspec processing errors (CL 12522270)


0.10.5 (2017-11-03)
-------------------

New features
~~~~~~~~~~~~

* **files:** add repository state file (CL 12514560)
* **poll:** add poller for Git and initial tests (CL 12504303)


0.10.4 (2017-10-17)
-------------------

New features
~~~~~~~~~~~~

* **submit:** add an external script for submitting to repository (CL 12411929)

Bug fixes
~~~~~~~~~

* **p4:** do not reuse existing p4 clients (CL 12403469)


0.10.3 (2017-10-17)
-------------------

Bug fixes
~~~~~~~~~

* **git:** typo fix (CL 12434522)


0.10.2 (2017-10-10)
-------------------

New features
~~~~~~~~~~~~

* **git:** add 'git checkout' functionality (CL 12375234)
* **git:** add 'git cherry-pick' and 'refspec' functionality (CL 12382598)
* **gerrit:** add Gerrit support (CL 12385073)
* **configuration_support:** add quotes and warning if space is detected within parameter in 'command' item (CL 12389569)

Bug fixes
~~~~~~~~~

* **tests:** make unused vcs module import non-obligatory (CL 12362747)


0.10.1 (2017-09-22)
-------------------

New features
~~~~~~~~~~~~

* **git:** add initial Git support; change --no-sync into switch of --vcs-type (CL 12338109)


Bug fixes
~~~~~~~~~

* **p4:** fix 'Librarian checkout' exceptions (CL 12337453)


0.10.0 (2017-09-13)
-------------------

New features
~~~~~~~~~~~~

* **p4:** add --p4-force-clean instead of --p4-no-clean option: P4 client is now not deleted by default (CL 12193452)


Bug fixes
~~~~~~~~~

* **Project 'Universe' renamed into 'Universum' to avoid name duplication** (CL 12192761)
* **reporter:** TeamCity-related parameters are no longer mandatory (CL 12270835)


0.9.1 (2017-08-25)
------------------

New features
~~~~~~~~~~~~

* **launcher:** add support for :ref:`custom environment variables values <filtering>` (CL 12167472)


0.9.0 (2017-08-22)
------------------

New features
~~~~~~~~~~~~

* **Project 'Universe' transformed into a Python module, installable with pip** (CL 12090448)


Bug fixes
~~~~~~~~~

* **documentation:** update documentation on module arguments (CL 12068956)


0.8.1 (2017-08-03)
------------------

New features
~~~~~~~~~~~~

* **configs:** remove unnecessary nesting of configurations (CL 12008410)


Bug fixes
~~~~~~~~~

* **launcher:** append sys.path with config_path to import any subsidiary modules (CL 12001247)
* **report:** fix non-existing report_artifacts processing - ignore non-existing directories (CL 11998180)
* **launcher:** fix empty variable names - ' & name' is now processed correctly (CL 11990844)


0.8.0 (2017-07-26)
------------------

New features
~~~~~~~~~~~~

* **CI Framework renamed into project 'Universe'** (CL 11960797)

* **documentation:** add :doc:`description <args>` of main script command-line parameters (CL 11958432)

Bug fixes
~~~~~~~~~

* **documentation:** fix table content width, remove unnecessary scroll bars (CL 11940638)


0.7.0 (2017-07-21)
------------------

New features
~~~~~~~~~~~~

* **documentation:** add :doc:`system prerequisites page <prerequisites>` to user manual (CL 11871571)
* **documentation:** add documentation for :mod:`_universum.configuration_support` module (CL 11883751)
* **launcher:** add support for more than one environment variable to
  :ref:`filter configurations <filtering>` (CL 11918355)

Bug fixes
~~~~~~~~~

* **launcher:** fix :ref:`configuration filtering <filtering>`: filter artifacts
  as well as configurations (CL 11884517)
* **output:** use TeamCity built-in methods of stderr reporting for correct in-block
  error highlighting (CL 11906945)


0.6.3 (2017-07-13)
------------------

Bug fixes
~~~~~~~~~

* **documentation:** fix product name and version display in documentation (CL 11861929)


0.6.2 (2017-07-11)
------------------

New features
~~~~~~~~~~~~

* **report:** add :ref:`direct links to build artifacts <report_artifacts>` into
  Reporter comments (CL 11840530)


0.6.1 (2017-07-05)
------------------

New features
~~~~~~~~~~~~

* **files:** add :ref:`working directory <get_project_root>` reference to logs (CL 11794980)

Bug fixes
~~~~~~~~~

* **p4:** bring back reverting in 'prepare repository' step and add more logs (CL 11795512)


0.6.0 (2017-07-05)
------------------

New features
~~~~~~~~~~~~

* **launcher:** add :ref:`configuration filtering <filtering>` (CL 11721556)
* **artifacts:** wildcard initial support (CL 11793140)


0.5.0 (2017-06-06)
------------------

New features
~~~~~~~~~~~~

* **tests:** add docker-based testing of p4poll (CL 11547138)

Bug fixes
~~~~~~~~~

* **tests:** split pytest calls to different targets to ensure all target execution (CL 11536269)
* **launcher:** change stderr printing to real-time instead of united report (CL 11546996)

Refactoring
~~~~~~~~~~~

* **reporter:** change of reporting console arguments because of new 'Reporter' module; report format tuning (CL 11535521)


0.4.1 (2017-05-30)
------------------

Bug fixes
~~~~~~~~~

* **artifacts:** fix artifacts reference before creation (CL 11525220)


0.4.0 (2017-05-30)
------------------

New features
~~~~~~~~~~~~

* **artifacts:** artifacts are now collected to a separate directory (CL 11516403)
* **main:** introduce version number (CL 11522987)


0.3.0 (2017-05-25)
------------------

New features
~~~~~~~~~~~~

* **tests:** add pylint check (CL 11429250)
* **tests:** add doctest collecting (CL 11473769)
* **swarm:** less default comments to Swarm, more optional (CL 11485014)

Bug fixes
~~~~~~~~~

* **test:** fix bug with stopping all test types once one type detects failure (CL 11428772)
* **swarm:** fix reporting to Swarm builds that did not execute actual build steps (CL 11451509)
* **launcher:** fix artifact collecting interruption (CL 11482810)
* **launcher:** fix extra dot directory in artifact archives (CL 11484785)


0.2.1 (2017-05-17)
------------------

Bug fixes
~~~~~~~~~

* **swarm:** Swarm double prefixes fixed (CL 11426957)


0.2.0 (2017-05-16)
------------------

New features
~~~~~~~~~~~~

* **p4:** switch to disposable workspaces (CL 11340806)
* **p4:** multiple VCS roots support (CL 11368679)
* **p4:** poll perforce server to trigger build by opening specified URL (CL 11406318)
* **tests:** add test stub (CL 11303440)
* **tests:** switch to py.test (CL 11414047)

Bug fixes
~~~~~~~~~

* **p4:** Perforce arguments processing fixes (CL 11340552)
* **p4:** moved argument lists preparing back to p4; list sorting bug fix (CL 11368997)
* **p4:** add client name changing (CL 11403095)
* **tests:** configs.py fix (CL 11303478)
* **tests:** add missing thirdparty dependency - module 'py' (CL 11414169)

Refactoring
~~~~~~~~~~~

* **p4:** put parsed options into dynamically created hierarchy (CL 11376372)
* **p4:** return P4WORKSPACE as P4CLIENT; SYNC_CHANGELIST fix (CL 11392504)


0.1.1 (2017-04-26)
------------------

Bug fixes
~~~~~~~~~

* **output:** add warning display (CL 11291629)


0.1.0 (2017-04-26)
------------------

New features
~~~~~~~~~~~~

* **documentation:** add change log (CL 11288927)
* **launcher:** add asynchronous step execution (CL 11281279)
* **documentation:** update system configuring manual (CL 11281382)

Bug fixes
~~~~~~~~~

* **launcher:** change default 'command' launch directory back to project root (CL 11270477)
