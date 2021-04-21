GitHub Handler
==============

GitHub Handler is a Universum mode that serves as `GitHub Application <https://docs.github.com/en/developers/apps>`__,
helping to perform and report checks on new commits to a repository. It can create new check runs on GitHub
and trigger an already set up automation server to perform these checks. GitHub Handler parses all required params
and passes them to the triggered builds.


How to set up GitHub auto check using Unversum
----------------------------------------------

Default Universum ('main' mode) can post `check run` statuses to GitHub to be depicted both on 'Checks' page
in pull requests and as a simple icon near any checked commit.
To do so, it needs a set of parameters to be passed to it:

* ``--vcs-type=github``
* ``--report-to-review``
* `GitHub-related parameters <args.html#GitHub>`__

.. note::

    During these checks, if some steps were using :doc:`Universum analyzers <code_report>`,
    and any issues are found, they will also be reported in comments. See
    `this example <https://github.com/Samsung/Universum/pull/459/commits/f777fad41fd7de37365f17dc20e3e34b2ffdeee7>`_.

Some of these required parameters are sent by GitHub via web-hooks after the required `check run` is created:

* ``--git-repo``: exact repository to pull sources from
* ``--git-refspec``: PR source branch to perform check on
* ``--git-checkout-id``: exact commit ID from the branch (not necessarily latest) to check
* ``--github-check-id``: GitHub check run ID to be reported to
* ``--github-installation-id``: parameter required for authorization

To get a web-hook payload and retrieve the last two of these parameters, a GitHub Application is required,
and GitHub Handler could be used as such.

.. note::

    GitHub Handler is a simple script, receiving web-hook payload and event as parameters.
    To work as GitHub Application it still needs a web server to receive actual web-hooks and pass their
    contents as parameters to Handler.

One of the easiest ways to make it work is to put the GitHub Handler execution into an automation server
(such as Jenkins) job triggered by incoming web-hooks from GitHub. GitHub Handler parses the incoming
web-hook event (passed via "x-github-event" header) and payload content. If a new `check run` is required,
it sends a request to GitHub to create one. If the `check run` is already created, it parses the required parameters
and triggers the set up automation server to run a previously described check by Universum in 'main' mode (see above).

See example of such Jenkins job `in the next section <Jenkins jobs example_>`_.

.. note::

    Webhook Handler job and a checking job can be set up on different automation servers

The following picture represents a possible event sequence leading to a check result for a commit displayed on GitHub:

.. raw:: html
    :file: _static/github_handler.svg

On this picture numbers depict the following events:

1. User makes a new commit
2. GitHub detects a commit, creates a check suite and sends a web-hook payload with ``check_suite`` event
   in "x-github-event" header to an already set up automation server (in this case, Jenkins)
3. `Generic Webhook Trigger` plugin triggers a preconfigured Jenkins job ('GitHub Webhook handler'),
   passing payload and "x-github-event" header contents
4. GitHub Handler checks that repo name and web-hook event are applicable, and if so, sends a request via
   `GitHub API <https://docs.github.com/en/rest/reference/checks#create-a-check-suite>`__
   to create a new check run to GitHub
5. GitHub creates a new check run and sends a new web-hook payload with ``check_run`` event
6. `Generic Webhook Trigger` plugin triggers the 'GitHub Webhook handler' job again, now with different event and
   payload
7. Based on received event, GitHub Handler triggers another preconfigured job with usual `Universum` call
   ('Check commit') via HTTP call, retrieving all required parameters from GitHub web-hook payload and passing them
   to the build via `build with parameters` trigger mechanism
8. Receiving all required parameters, Universum in default mode with ``--report-to-review`` on and ``--vcs-type=github``
   performs a commit check according to :doc:`configuration file <configuring>`,
   set up in `build parameters <args.html#Configuration\ execution>`__
9. [optional] If ``--report-build-start`` set in `build parameters <args.html#Result\ reporting>`__, Universum will
   inform the GitHub that a check is already in progress using
   `GitHub API <https://docs.github.com/en/rest/reference/checks#update-a-check-run>`__,
   leaving a message to wait until it's over
10. Depending on build result, Universum either reports build success or failure to GitHub

    * to report successful build, a ``--report-build-success`` `option <args.html#Result\ reporting>`__ is required
11. User can see build result on 'Checks' page in pull requests and as a simple icon near the checked commit
    directly on GitHub.

.. note::

    GitHub also sends web-hook payloads on other events (such as *'check run completed'*), that are
    currently ignored by GitHub Handler

The list of GitHub Handler parameters can be found :ref:`here <additional_commands#github-handler>`.


.. _github_handler#jenkins:

Jenkins jobs example
--------------------

.. collapsible::
    :header: Here's DSL script for GitHub Handler

    .. code-block::

        pipelineJob('GitHub Webhook handler') {
          triggers {
            genericTrigger {
              genericVariables {
                genericVariable {
                  key("GITHUB_PAYLOAD")
                  value("\$")
                }
              }
              genericHeaderVariables {
                genericHeaderVariable {
                  key("x-github-event")
                  regexpFilter("")
                }
              }
              causeString('Event "\^${x_github_event}", action "\^${GITHUB_PAYLOAD_action}"')
              token('UniversumGitHub')
              printContributedVariables(false)
              printPostContent(false)
              silentResponse(false)
              regexpFilterText("")
              regexpFilterExpression("")
            }
          }
          parameters {
            stringParam("GITHUB_APP_ID", "1234", "")
            stringParam("TRIGGER_URL", "https://my.jenkins-server.com/buildByToken/buildWithParameters?job=Check%20commit&token=GITHUB", "")
          }
          definition {
            cps {
              script("""\
                pipeline {
                  agent any
                  environment {
                    KEY_FILE = credentials('github-private-key')
                    GITHUB_PRIVATE_KEY = "@\^${KEY_FILE}"
                  }
                  stages {
                    stage ('Run GitHub Handler') {
                      steps {
                        ansiColor('xterm') {
                          sh("{python} -m universum github-handler -e \^${x_github_event}")
                        }
                      }
                    }
                  }
                }
              """.stripIndent())
              sandbox()
            }
          }
        }

.. collapsible::
    :header: And here's DSL script for the job it triggers

    .. code-block::

        pipelineJob('Check commit') {
          authenticationToken("GITHUB")
          parameters {
            stringParam("GIT_REPO", "", "")
            stringParam("GITHUB_APP_ID", "1234", "")
            stringParam("GIT_REFSPEC", "", "")
            stringParam("GIT_CHECKOUT_ID", "", "")
            stringParam("GITHUB_INSTALLATION_ID", "", "")
            stringParam("GITHUB_CHECK_ID", "", "")
            stringParam("CONFIG_PATH", ".universum.py", "")
          }
          definition {
            cps {
              script("""\
                pipeline {
                  agent any
                  environment {
                    KEY_FILE = credentials('github-private-key')
                    GITHUB_PRIVATE_KEY = "@\^${KEY_FILE}"
                  }
                  stages {
                    stage ('test') {
                      steps {
                        cleanWs()
                        ansiColor('xterm') {
                          sh "{python} -m universum --no-diff -vt github --report-to-review -rst -rsu -rof"
                        }
                        junit '**/junit_results.xml'
                        junit '**/TEST*.xml'
                      }
                    }
                  }
                  post {
                    always {
                      archiveArtifacts 'artifacts/*'
                      cleanWs()
                   }
                  }
                }
              """.stripIndent())
              sandbox()
            }
          }
        }

.. note::

    Here GITHUB_APP_ID is once retrieved from GitHub Application settings and hardcoded to both jobs;
    and KEY_FILE is a private key, associated with this exact ID and stored in Jenkins credentials

Jenkins plugins used for these jobs:
    - configuration-as-code
    - job-dsl
    - workflow-aggregator
    - generic-webhook-trigger
    - ansicolor
    - ws-cleanup
    - junit
    - build-token-root
