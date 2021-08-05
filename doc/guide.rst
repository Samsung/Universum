Getting started
===============

This guide will provide an example step-by-step tutorial on setting up CI for a GitHub project, using Jenkins server,
GitHub application and Pylint analyzer. These are the steps to take:

1. :ref:`Install Universum <guide#install>`
2. :ref:`Load project to VCS <guide#create>`
3. :ref:`Initialize Unviersum <guide#init>`
4. :ref:`Configure project <guide#configure>`
5. :ref:`Add static analyzer <guide#analyzer>`
6. :ref:`Configuration filtering <guide#filter>`
7. :ref:`Upload changes to VCS <guide#upload>`
8. :ref:`Run Universum in default mode <guide#launch>`
9. :ref:`Set up Jenkins server <guide#jenkins>`
10. :ref:`Create a Jenkins job <guide#job>`
11. :ref:`Set up the simplest CI using Universum <guide#set-up-ci>`
12. :ref:`Make repo state more precise <guide#set-repo-state>`
13. :ref:`Add artifacts to the build <guide#add-artifacts>`
14. :ref:`Create a pre-commit job <guide#pre-commit>`
15. :ref:`Register a GitHub Application <guide#github-app>`


.. _guide#install:

Install Universum
-----------------

First, before setting up Continious Integration, let's implement and test Universum support locally.

1. Make sure your system meets Universum :doc:`prerequisites <install>`
2. Install Univesrum using ``{pip} install -U universum`` command from command line
3. Run ``{python} -m universum --help`` to make sure the installation was successful

If nothing went wrong, you should get a list of available :doc:`command line parameters <args>`.


.. _guide#create:

Create project in VCS
---------------------

For demonstration purposes let's create a project on GitHub. To do so, we'll need to do the following:

1. Register a user on GitHub, if not already (press the `Sign up` button and follow the instructions)
2. Get to `Create a new repository` interactive dialog by doing any of these:

   * press `New` button in `Repositories` block on main page (https://github.com/)
   * press ``+`` button in upper right corner and select `New repository`
   * press `New` button on `Repositories` tab on personal page (https://github.com/*YOUR-USERNAME*?tab=repositories)
   * simply proceed to https://github.com/new

3. Enter requested parameters:

   * a name (we will use ``universum-test-project``)
   * `Public/Private` (we will use `Public`)
   * `Initialize this repository with` (we will use `Add a README file`)


Read more about creating repositories in `a detailed GitHub guide
<https://docs.github.com/en/free-pro-team@latest/github/getting-started-with-github/create-a-repo>`__.

After creating a repo online, clone it locally::

    git clone https://github.com/YOUR-USERNAME/universum-test-project.git
    cd universum-test-project
    ls -a

The output of the last command should be::

    .  ..  .git  README.md

From now on we will refer to this directory as a project root.


.. _guide#init:

Initialize Universum
--------------------

After previous step, we should still be in project root directory.
Let's :ref:`initialize Universum <additional_commands#init>` in that directory::

    {python} -m universum init

That will create a new file ``.universum.py`` and print a command to use it::

    {python} -m universum run

The default :doc:`configuration file <configuring>`, created by this command, looks like this::

    #!/usr/bin/env {python}

    from universum.configuration_support import Configuration

    configs = Configuration([Step(name='Show directory contents', command=['ls', '-a']),
                             Step(name='Print a line', command=['bash', '-c', 'echo Hello world'])])

    if __name__ == '__main__':
        print(configs.dump())

Running suggested command ``{python} -m universum run`` should result in launching Universum and
getting an output like this:

.. collapsible::

     .. code-block::

         ==> Universum 1.0.0 started execution
         ==> Cleaning artifacts...
         1. Processing project configs
          |   ==> Adding file /home/user/universum-test-project/artifacts/CONFIGS_DUMP.txt to artifacts...
          └ [Success]

         2. Preprocessing artifact lists
          └ [Success]

         3. Executing build steps
          |   3.1.  [ 1/2 ] Show directory contents
          |      |   $ /usr/bin/ls -a
          |      |   .  ..  artifacts  .git	README.md  .universum.py
          |      └ [Success]
          |
          |   3.2.  [ 2/2 ] Print a line
          |      |   $ /usr/bin/bash -c 'echo Hello world'
          |      |   Hello world
          |      └ [Success]
          |
          └ [Success]

         4. Reporting build result
          |   ==> Here is the summarized build result:
          |   ==> 3. Executing build steps
          |   ==>   3.1.  [ 1/2 ] Show directory contents - Success
          |   ==>   3.2.  [ 2/2 ] Print a line - Success
          |   ==> Nowhere to report. Skipping...
          └ [Success]

         5. Collecting artifacts
          └ [Success]

         ==> Universum 1.0.0 finished execution

Running this command will also produce a directory ``artifacts``, containing a single file: ``CONFIGS_DUMP.txt``.
The reason for this file existance will be explained in the next paragraph.


.. _guide#configure:

Configure project
-----------------

Let's add some actual sources to project directory. For example, a simple script ``run.sh``::

    #!/usr/bin/env bash

    if [ "$1" = "pass" ]
    then
        echo "Script succeeded"
        exit 0
    elif [ "$1" = "fail" ]
    then
        echo "Script failed"
        exit 1
    else
        echo "Unknown outcome"
        exit 2
    fi

Then, in configuration file we can refer to this script::

    configs = Configuration([Step(name='Run script', command=['run.sh', 'pass'])])

After this change, running ``{python} -m universum run`` should result in the following output:

.. collapsible::

     .. code-block::

        ==> Universum 1.0.0 started execution
        ==> Cleaning artifacts...
        1. Processing project configs
         |   ==> Adding file /home/user/universum-test-project/artifacts/CONFIGS_DUMP.txt to artifacts...
         └ [Success]

        2. Preprocessing artifact lists
         └ [Success]

        3. Executing build steps
         |   3.1.  [ 1/1 ] Run script
         |      |   $ /home/user/universum-test-project/run.sh pass
         |      |   Script succeeded
         |      └ [Success]
         |
         └ [Success]

        4. Reporting build result
         |   ==> Here is the summarized build result:
         |   ==> 3. Executing build steps
         |   ==>   3.1.  [ 1/1 ] Run script - Success
         |   ==> Nowhere to report. Skipping...
         └ [Success]

        5. Collecting artifacts
         └ [Success]

        ==> Universum 1.0.0 finished execution

More info on project configuration file can be found on :doc:`project configuration <configuring>` page.
Final configuration may be a result of :class:`~universum.configuration_support.Step` objects multiplication
and filtering, but the explicit list of steps to be executed can be found in ``CONFIGS_DUMP.txt`` file in
``artifacts`` directory.


.. _guide#analyzer:

Add static analyzer
-------------------

Say, instead of writing a script in `bash` we used `python`, and have the following script ``run.py``::

    #!/usr/bin/env {python}

    import sys

    if len(sys.argv) < 2:
        print("Unknown outcome")
        sys.exit(2)
    if sys.argv[1] == "pass":
        print("Script succeeded")
        sys.exit(0)
    print("Script failed")
    sys.exit(1)

To use this script, we'd have to modify ``configs`` to this::

    configs = Configuration([Step(name='Run script', command=['{python}', 'run.py', 'pass'])])

which will get the same result as the previous one.

But, let's presume we want to make sure our Python code style
corresponds to PEP-8 from the very beginning. We might install `Pylint <https://www.pylint.org/>`__ via
``{pip} install -U pylint``, and then add the code style check::

    configs = Configuration([
        Step(name='Run script', command=['{python}', 'run.py', 'pass']),
        Step(name='Pylint check', code_report=True, command=[
            '{python}', '-m', 'universum.analyzers.pylint', '--result-file', '${CODE_REPORT_FILE}', '--files', '*.py'
        ])
    ])

Running Universum with this config will produce the following output:

.. collapsible::

     .. code-block::

        ==> Universum 1.0.0 started execution
        ==> Cleaning artifacts...
        1. Processing project configs
         |   ==> Adding file /home/user/universum-test-project/artifacts/CONFIGS_DUMP.txt to artifacts...
         └ [Success]

        2. Preprocessing artifact lists
         └ [Success]

        3. Executing build steps
         |   3.1.  [ 1/2 ] Run script
         |      |   $ /usr/bin/{python} run.py pass
         |      |   Script succeeded
         |      └ [Success]
         |
         |   3.2.  [ 2/2 ] Pylint check
         |      |   $ /usr/bin/{python} -m universum.analyzers.pylint --result-file /home/user/universum-test-project/code_report_results/Pylint_check.json --files '*.py'
         |      |   Error: Module sh got exit code 1
         |      └ [Failed]
         |
         └ [Success]

        4. Reporting build result
         |   ==> Here is the summarized build result:
         |   ==> 3. Executing build steps
         |   ==>   3.1.  [ 1/2 ] Run script - Success
         |   ==>   3.2.  [ 2/2 ] Pylint check - Failed
         |   ==> Nowhere to report. Skipping...
         └ [Success]

        5. Collecting artifacts
         └ [Success]

        ==> Universum 1.0.0 finished execution

Which means we already have some code style issues in the project sources. Open the ``Pylint_check.json`` file
in ``code_report_results`` directory to see the code style check results::

    [
        {
            "type": "convention",
            "module": "run",
            "obj": "",
            "line": 1,
            "column": 0,
            "path": "run.py",
            "symbol": "missing-module-docstring",
            "message": "Missing module docstring",
            "message-id": "C0114"
        }
    ]

Let's presume we do not intend to add docstrings to every module. Then this check failure can be fixed by simply
putting a ``pylintrc`` file in project root with following content::

    [MESSAGES CONTROL]
    disable = missing-docstring

That should lead to `Universum` successful execution.

.. note::

    Current Pylint docs do not have a separate guide on ``rcfile``, but a sample one can be generated using
    ``pylint --generate-rcfile`` command.


.. _guide#filter:

Configuration filtering
-----------------------

Let's presume, we want to only run one of the two steps currently listed in ``confis``. For example, to double check
the code style we only want to run a ``Pylint check`` step. This can be easily achieved by simply using
the ``--filter`` `command-line parameter <args.html#Configuration\ execution>`__. When running
a ``{python} -m universum run -f Pylint`` command, we will get the following output:

.. collapsible::

     .. code-block::

        ==> Universum 1.0.0 started execution
        ==> Cleaning artifacts...
        1. Processing project configs
         |   ==> Adding file /home/user/universum-test-project/artifacts/CONFIGS_DUMP.txt to artifacts...
         └ [Success]

        2. Preprocessing artifact lists
         └ [Success]

        3. Executing build steps
         |   3.1.  [ 1/1 ] Pylint check
         |      |   $ /usr/bin/{python} -m universum.analyzers.pylint --result-file /home/user/universum-test-project/code_report_results/Pylint_check.json --files '*.py'
         |      └ [Success]
         |
         └ [Success]

        4. Reporting build result
         |   ==> Here is the summarized build result:
         |   ==> 3. Executing build steps
         |   ==>   3.1.  [ 1/1 ] Pylint check - Success
         |   ==> Nowhere to report. Skipping...
         └ [Success]

        5. Collecting artifacts
         └ [Success]

        ==> Universum 1.0.0 finished execution

This is quite useful for local checks.


.. _guide#upload:

Upload changes to VCS
---------------------

Now that the project has some sources, we can upload them to VCS. But not all of the files, that are now present
in project root directory, are required in VCS. Here are some directories, that might be present locally, but
not to be committed:

    * ``__pycache__``
    * ``artifacts``
    * ``code_report_results``

To prevent them from being committed to GitHub, create a file named ``.gitignore`` with these directories listed in it::

    __pycache__
    artifacts
    code_report_results

After this, use these common `Git` commands::

    git add --all
    git commit -m "Add project sources"
    git push

Executing these commands may require your GitHub user name, password and/or e-mail address. If so,
required info will be prompted to input via command line during command execution.

Successful repository update will lead to all the files described above arriving on GitHub, along with the new
commit ``Add project sources``.


.. _guide#launch:

Run Universum in default mode
-----------------------------

Now that project sources can be accessed online, we may launch `Universum` in default CI mode, including
downloading sources from server.

.. note::

    As we are now planing to work with Git repository, `Universum` will :doc:`require <install>`
    Git CLI installed in the system, and some additional Python packages specific for Git.

We can install all these by::

    sudo apt install git
    {pip} install -U universum[git]

Now let's leave the project root directory, as we no longer need local sources, create a new one,
``universum-ci-checks``, and launch `Universum` there::

    cd ..
    mkdir universum-ci-checks
    {python} -m universum --no-diff --vcs-type git --git-repo https://github.com/YOUR-USERNAME/universum-test-project.git

We will now get a log, very similar to previous one, but with some additional sections:

.. collapsible::

    .. code-block::
       :linenos:
       :emphasize-lines: 2-17, 26-28, 45-48, 62-66

        ==> Universum 1.0.0 started execution
        1. Preparing repository
         |   ==> Adding file /home/user/universum-ci-checks/artifacts/REPOSITORY_STATE.txt to artifacts...
         |   1.1. Cloning repository
         |      |   ==> Cloning 'https://github.com/YOUR-USERNAME/universum-test-project.git'...
         |      |   ==> Cloning into '/home/user/universum-ci-checks/temp'...
         |      |   ==> POST git-upload-pack (165 bytes)
         |      |   ==> remote: Enumerating objects: 9, done.
         |      |   ==> remote: Total 9 (delta 0), reused 6 (delta 0), pack-reused 0
         |      |   ==> Please note that default remote name is 'origin'
         |      └ [Success]
         |
         |   1.2. Checking out
         |      |   ==> Checking out 'HEAD'...
         |      └ [Success]
         |
         └ [Success]

        2. Processing project configs
         |   ==> Adding file /home/user/universum-ci-checks/artifacts/CONFIGS_DUMP.txt to artifacts...
         └ [Success]

        3. Preprocessing artifact lists
         └ [Success]

        4. Reporting build start
         |   ==> Nowhere to report. Skipping...
         └ [Success]

        5. Executing build steps
         |   5.1.  [ 1/2 ] Run script
         |      |   ==> Adding file /home/user/universum-ci-checks/artifacts/Run_script_log.txt to artifacts...
         |      |   ==> Execution log is redirected to file
         |      |   $ /usr/bin/{python} run.py pass
         |      └ [Success]
         |
         |   5.2.  [ 2/2 ] Pylint check
         |      |   ==> Adding file /home/user/universum-ci-checks/artifacts/Pylint_check_log.txt to artifacts...
         |      |   ==> Execution log is redirected to file
         |      |   $ /usr/bin/{python} -m universum.analyzers.pylint --result-file /home/user/universum-ci-checks/temp/code_report_results/Pylint_check.json --files '*.py'
         |      └ [Success]
         |
         └ [Success]

        6. Processing code report results
         |   ==> Adding file /home/user/universum-ci-checks/artifacts/Static_analysis_report.json to artifacts...
         |   ==> Issues not found.
         └ [Success]

        7. Collecting artifacts
         └ [Success]

        8. Reporting build result
         |   ==> Here is the summarized build result:
         |   ==> 5. Executing build steps
         |   ==>   5.1.  [ 1/2 ] Run script - Success
         |   ==>   5.2.  [ 2/2 ] Pylint check - Success
         |   ==> 7. Collecting artifacts - Success
         |   ==> Nowhere to report. Skipping...
         └ [Success]

        9. Finalizing
         |   9.1. Cleaning copied sources
         |      └ [Success]
         |
         └ [Success]

        ==> Universum 1.0.0 finished execution

We will look at `reporting` closer a little later, and for now pay attention to ``Preparing repository``/``Finalizing``
blocks. As a CI system, `Univesrum` downloads sources from server, runs checks on them and then clears up.
Pay attention to the directory ``artifacts``. Until now it contained only the ``CONFIGS_DUMP.txt`` file with
full step list; but now it contains a lot of new files:

    * REPOSITORY_STATE.txt
    * Run_script_log.txt
    * Pylint_check_log.txt
    * Static_analysis_report.json

The first one describes what sources were used for this exact build: repo, fetch target (e.g. `HEAD` or commit hash),
list of downloaded files. In case of other VCS types (such as Perforce or local folder) the contents of this file
will vary; the purpose of this file is repeatability of the builds.

The next two files are step execution logs. When the project configuration includes many different steps, each containing
a long execution log, reading the whole `Universum` log in console may be not that user-friendly. That's why when
executing in console, by default the logs are written to files. This befaviour may be changed via ``--out``
`command-line parameter <args.html#Output>`__.

And, finally, the last file, ``Static_analysis_report.json``, contains all issues found by ``code_report=True``
steps. As we already fixed all Pylint issues, it should now contain an empty list ``[]``.


.. _guide#jenkins:

Set up Jenkins server
---------------------

Now that CI builds are working locally, let's set up a real automated CI.

Create a ``Dockerfile`` with following content::

    FROM jenkins/jenkins:2.289.3-lts-jdk11
    USER root
    RUN apt-get update && apt-get install -y apt-transport-https \
           ca-certificates curl gnupg2 \
           software-properties-common
    RUN curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add -
    RUN apt-key fingerprint 0EBFCD88
    RUN add-apt-repository \
           "deb [arch=amd64] https://download.docker.com/linux/debian \
           $(lsb_release -cs) stable"
    RUN apt-get update && apt-get install -y docker-ce-cli
    USER jenkins
    RUN jenkins-plugin-cli --plugins "blueocean:1.24.7 docker-workflow:1.26"

If this results in outdated Jenkins server later, please consult `official Jenkins installation guide
<https://www.jenkins.io/doc/book/installing/docker/#downloading-and-running-jenkins-in-docker>`__.

Execute the following commands::

    docker network create jenkins
    docker run --name jenkins-docker --rm --detach \
      --privileged --network jenkins --network-alias docker \
      --env DOCKER_TLS_CERTDIR=/certs \
      --volume jenkins-docker-certs:/certs/client \
      --volume jenkins-data:/var/jenkins_home \
      --publish 2376:2376 docker:dind
    docker build -t myjenkins-blueocean:1.1 .
    docker run --name jenkins-blueocean --rm --detach \
      --network jenkins --env DOCKER_HOST=tcp://docker:2376 \
      --env DOCKER_CERT_PATH=/certs/client --env DOCKER_TLS_VERIFY=1 \
      --publish 8080:8080 --publish 50000:50000 \
      --volume jenkins-data:/var/jenkins_home \
      --volume jenkins-docker-certs:/certs/client:ro \
      myjenkins-blueocean:1.1

Please note that depending on exact ``Dockerfile`` contents resulting server may or may not contain Python and Pip.
If not, ether add installation to ``Dockerfile`` or execute the following after starting the container::

    docker exec -u root jenkins-blueocean apt install -y {python}
    docker exec -u root jenkins-blueocean apt install -y python3-pip
    docker exec -u root jenkins-blueocean {python} -m pip install -U pip

Go to http://localhost:8080 and unlock Jenkins, follow the instruction on a title page:

    1. execute ``docker exec jenkins-blueocean cat /var/jenkins_home/secrets/initialAdminPassword``
    2. input the required key and follow further wizard instructions

.. note::

    Please pay attention, that to let you server to be visible to GitHub (for webhook triggers), its port
    should be exposed to the Internet. Please use router settings or any other suitable means for this.

Now that we have server URL and an exposed port, we can set up `a simple PUSH notification webhook
<https://docs.github.com/en/developers/webhooks-and-events/webhooks/creating-webhooks>`__ to know about sources
updates.


.. _guide#job:

Create a simple Jenkins job
---------------------------

First let's create a simple post-commit check. On Jenkins main page click ``Create a job``, or simply go to
http://localhost:8080/newJob. There enter a job name (for example we will use ``universum_postcommit``), select
a job type (for example we will use ``Pipeline``) and proceed to project configuration.

On configuration page find ``Build Triggers`` and check the ``GitHub hook trigger for GITScm polling`` checkbox.

.. note::

    For Git SCM to work automatically, PUSH notifications should be set up right in your repository settings.
    Please refer to the following `official guide <https://plugins.jenkins.io/git/#push-notification-from-repository>`__
    on managing such triggers.

After that, go to ``Pipeline``, select ``Pipeline script`` and enter the following script::

    pipeline {
      agent any
      stages {
        stage ('Universum check') {
          steps {
            git branch: 'main', 'https://github.com/YOUR-USERNAME/universum-test-project.git'
            sh("{python} -m universum run")
          }
        }
      }
    }

But, actually running this job will fail for now with the following error::

    /usr/bin/{python}: No module named universum

Which is expected, because we have not installed neither Universum, nor Git to the Jenkins node.
Also, our config uses Pylint, so let's do the following changes to pipeline::

    pipeline {
      agent any
      stages {
        stage ('Universum check') {
          steps {
            sh("{pip} install -U universum pylint")
            git branch: 'main', 'https://github.com/YOUR-USERNAME/universum-test-project.git'
            sh("{python} -m universum run")
          }
        }
      }
    }

Keeping Universum updated is generally a good idea, as critical bugs may be fixed in new releases.

Though, now Univesrum does not look very pretty due to color codes. We recommend installing
`AnsiColor <https://plugins.jenkins.io/ansicolor/>`__ Jenkins plugin for prettier output.
See `Jenkins official guide on plugin installation <https://www.jenkins.io/doc/book/managing/plugins/>`__.
After installing the plugin and rebooting change pipeline to this::

    pipeline {
      agent any
      options {
        ansiColor('xterm')
      }
      stages {
        stage ('Universum check') {
          steps {
            sh("{pip} install -U universum pylint")
            git branch: 'main', 'https://github.com/YOUR-USERNAME/universum-test-project.git'
            sh("{python} -m universum run")
          }
        }
      }
    }

.. collapsible::
    :header: And the stage output should look like this

    .. code-block::

        [Pipeline] { (Universum check)
        [Pipeline] sh
        + {pip} install -U universum

        Defaulting to user installation because normal site-packages is not writeable
        Requirement already satisfied: universum <and it's dependencies>
        [Pipeline] git
        The recommended git tool is: NONE
        No credentials specified
         > /usr/bin/git rev-parse --is-inside-work-tree # timeout=10

        Fetching changes from the remote Git repository
        <logs of getting sources from Git>
        [Pipeline] sh
        + {python} -m universum run

        ==> Universum 1.0.0 started execution
        ==> Cleaning artifacts...
        1. Processing project configs
         |   ==> Adding file http://localhost:8080/job/universum_postcommit/1/artifact/artifacts/CONFIGS_DUMP.txt to artifacts...
         └ [Success]

        2. Preprocessing artifact lists
         └ [Success]

        3. Executing build steps
         |   3.1.  [ 1/2 ] Run script
         |      |   $ /usr/bin/{python} run.py pass
         |      └ [Success]
         |
         |   3.2.  [ 2/2 ] Pylint check
         |      |   $ /usr/bin/{python} -m universum.analyzers.pylint --result-file /var/jenkins_home/workspace/universum_postcommit/code_report_results/Pylint_check.json --files '*.py'
         |      └ [Success]
         |
         └ [Success]

        4. Reporting build result
         |   ==> Here is the summarized build result:
         |   ==> 3. Executing build steps
         |   ==>   3.1.  [ 1/2 ] Run script - Success
         |   ==>   3.2.  [ 2/2 ] Pylint check - Success
         |   ==> Nowhere to report. Skipping...
         └ [Success]

        5. Collecting artifacts
         └ [Success]

        ==> Universum 1.0.0 finished execution
        [Pipeline] }


.. _guide#set-up-ci:

Set up the simplest CI using Universum
--------------------------------------

Universum offers a lot of additional functionality, but to use it, we first have to let it know
about VCS we're using. First, let's change Jenkins GitHub plugin to
`Generic Webhook Trigger <https://plugins.jenkins.io/generic-webhook-trigger/>`__, so that it doesn't
download sources automatically before Universum even started.

.. note::

    This also can be, for example, used later, to cherry-pick some files, including Universum config itself,
    from a different commit (e.g. in another branch).

In job configuration go to ``Build Triggers``, uncheck the ``GitHub hook trigger for GITScm polling``
and instead check the ``Generic Webhook Trigger``. In revealed settings for Generic webhook we need to find
``Token`` parameter and add a triggering token; otherwise we'd have to pass user and password to webhook.

Running `Universum` in default mode will require all parameters we already `tried locally <guide#launch>`.
So first, let's change job pipeline accordingly::

    pipeline {
      agent any
      options {
        ansiColor('xterm')
      }
      stages {
        stage ('Universum check') {
          steps {
            sh("{pip} install -U universum[git] pylint")
            sh("{python} -m universum --no-diff --vcs-type git --git-repo https://github.com/YOUR-USERNAME/universum-test-project.git")
          }
        }
      }
    }

Even though first launch might be successful, further job reruns will fail with the following error::

    ==> Universum 1.0.0 started execution
    1. Preparing repository
     |   Error: File 'REPOSITORY_STATE.txt' already exists in artifact directory.
     |   Possible reason of this error: previous build artifacts are not cleaned
     └ [Failed]

    2. Finalizing
     └ [Success]

    ==> Universum 1.0.0 finished execution

The reason for such error is that CI build is meant to be run in an empty clean directory to make sure
no leftovers from previous builds could affect the result. An example of such contamination can be some build
artifacts, created with previous sources and not created in most current run at all: in this scenario the outdated
files might be considered created successfully.

So, to avoid this problem, we can install `Workspace Cleanup plugin <https://plugins.jenkins.io/ws-cleanup/>` to
Jenkins, and modify pipeline to clean working directory before execution::

    pipeline {
      agent any
      options {
        ansiColor('xterm')
      }
      stages {
        stage ('Clean workspace') {
          steps {
            cleanWs()
          }
        }
        stage ('Universum check') {
          steps {
            sh("{pip} install -U universum[git] pylint")
            sh("{python} -m universum --no-diff --vcs-type git --git-repo https://github.com/YOUR-USERNAME/universum-test-project.git")
          }
        }
      }
    }

So, for now this job will start every time we push a new commit to the Git repository and check the latest
repository state. Let's apply to this job some useful features.


.. _guide#set-repo-state:

Make repo state more precise
----------------------------

Let's presume we want to check not the *latest* repository state, but every pushed commit separately.
Every webhook notification includes a payload with a lot of useful information. Let's investigate its contents
and decide what of them we might use.

To see a payload, sent to Jenkins by GitHub, first push a commit to the repo. Then open the project settings,
``Webhooks`` page. There find a webhook you created earlier and click the ``Edit`` button. Go to the end of the
page to find ``Recent Deliveries`` and click on the latest one. There you will find the headers and request body,
sent and received by GitHub.

To check the exact commit, we will need its hash, that is referenced in payload as ``after``. We might also pay
attention to ``repository.url`` to take the value from payload instead of hardcoding it into pipeline.
But, to use this parameters, we need to extract them from payload.

So, on Jenkins go to job configuration, ``Build Triggers``, ``Generic Webhook Trigger`` and click on ``Add`` button
in ``Post content parameters`` (actually, click it twice, for we will add two parameters). Parameter usage is
described in `plugin description <https://plugins.jenkins.io/generic-webhook-trigger/>`__.

1. First, we will add parameter named ``GIT_REPO``, with value ``$.repository.url``, where ``$`` refers to payload,
   and ``.repository.url`` is a 'JSONPath'
2. Then, add parameter named ``GIT_CHECKOUT_ID`` with value ``$.after`` to refer to new commit hash

These parameters will become environment variables for the upcoming builds and without further effort will be
`recognized <args.html#Git>`__ by Universum. Therefore, there's no need to pass ``--git-repo`` directly::

    pipeline {
      agent any
      options {
        ansiColor('xterm')
      }
      stages {
        stage ('Clean workspace') {
          steps {
            cleanWs()
          }
        }
        stage ('Universum check') {
          steps {
            sh("{pip} install -U universum[git] pylint")
            sh("{python} -m universum --no-diff --vcs-type git")
          }
        }
      }
    }

This will produce a build log, very similar to those received in previous configuration; main difference will be
``Preparing repository`` part:

.. collapsible::

    .. code-block::
       :emphasize-lines: 12-14

        1. Preparing repository
         |   ==> Adding file http://localhost:8080/job/universum_postcommit/58/artifact/artifacts/REPOSITORY_STATE.txt to artifacts...
         |   1.1. Cloning repository
         |      |   ==> Cloning 'https://github.com/YOUR-USERNAME/universum-test-project'...
         |      |   ==> Cloning into '/var/jenkins_home/workspace/universum_postcommit/temp'...
         |      |   ==> POST git-upload-pack (165 bytes)
         |      |   ==> remote: Enumerating objects: 34, done.
         |      |   ==> remote: Total 34 (delta 10), reused 7 (delta 0), pack-reused 0
         |      |   ==> Please note that default remote name is 'origin'
         |      └ [Success]
         |
         |   1.2. Checking out
         |      |   ==> Checking out '4411f3378a3c82cfb9b95487afd77fe6a7a5d472'...
         |      └ [Success]
         |
         |   1.3. Registering file diff for API
         |      └ [Success]
         |
         └ [Success]

Also, the contents of ``REPOSITORY_STATE.txt`` file will vary, but for now we won't be able to see that.


.. _guide#add-artifacts:

Add artifacts to the build
--------------------------

So, now we have this directory, defined with ``--artifact-dir``
`command line parameter <args.html#Artifact\ collection>`__, that already contains some useful data about the
recent build. To be able to see it on Jenkins, we will mention it in Jenkins pipeline like this::

    pipeline {
      agent any
      options {
        ansiColor('xterm')
      }
      stages {
        stage ('Clean workspace') {
          steps {
            cleanWs()
          }
        }
        stage ('Universum check') {
          steps {
            sh("{pip} install -U universum[git] pylint")
            sh("{python} -m universum --no-diff --vcs-type git")
            archiveArtifacts artifacts: 'artifacts/', followSymlinks: false
          }
        }
      }
    }

After this, all links in log (like that one leading to ``REPOSITORY_STATE.txt``) will start to work;
and all the artifacts will be accessible from a build page on Jenkins. Later on, when we will turn on the
``--report-to-review`` `command line option <args.html#Source\ files>`__, we will be able to use ``report_artifacts``
key of :class:`~universum.configuration_support.Step`, that will result in link to a chosen file to be posted in
a comment to checked review.

There two kinds of artifacts, expected by `Universum` from a build:

1. Usual artifacts, that are results of step execution. Absence of such artifacts is a symptom of unsuccessful
   execution, and therefore is considered a failure
2. Special artifacts to be reported to a code review, such as static analysis reports. Absence of
   such artifacts may mean that there simply is nothing to report, and therefore is not considered a failure

If an artifact is to be reported to code review, but is also a mandatory outcome of a build, it should be noted
in configurations file in both ``artifacts`` and ``report_artifacts`` key.

So, let's presume we want our build checks to generate a mandatory build artifacts. As an example, let's generate
a log file in our build script ``run.py``::

    #!/usr/bin/env python

    import sys

    with open("execution.log", "w+") as new_file:
        new_file.write("Here's what a script accepted from command line:\n" + str(sys.argv))

    if len(sys.argv) < 2:
        print("Unknown outcome")
        sys.exit(2)
    if sys.argv[1] == "pass":
        print("Script succeeded")
        sys.exit(0)
    print("Script failed")
    sys.exit(1)

After that, let's inform `Universum` we expect this file to be generated as an outcome of a build check::

    #!/usr/bin/env python

    from universum.configuration_support import Configuration, Step

    configs = Configuration([
        Step(name='Run script', command=['python3.7', 'run.py', 'pass'], artifacts="execution.log"),
        dict(name="Pylint check", code_report=True, command=[
            "python3.7", "-m", "universum.analyzers.pylint", "--result-file", "${CODE_REPORT_FILE}", "--files", "*.py"
        ])
    ])

    if __name__ == '__main__':
        print(configs.dump())

Actually, if we expect more than one log file to be generated, we can pass ``artifacts="*.log"`` to collect
all of them. But, be aware: if any of this log files are committed to the repo, the build will fail, as the file,
expected to be created by step execution, is already present in project directory. If, however, such file is to be
generated anew instead of the already committed one (this is a common case for builds, utilizing
:ref:`submit <additional_commands#submit>` `Universum` mode), there's another helpful
:class:`~universum.configuration_support.Step` key: ``artifact_prebuild_clean=True``.


.. _guide#pre-commit:

Create a pre-commit job
-----------------------

So, let's presume we want to check commit before merging it into `main` branch (or any other). To do so,
we need almost the same information as for the post-commit: commit hash to checkout and a webhook notification
to know the commit was pushed to server and requires to be checked.

Let's say we don't want to check any commit, pushed to the repo; for the pre-commit we're only interested in
those pushed in scope of `pull requests` (PRs). To only react to those, go to project ``Settings``, ``Webhooks``,
find the webhook created earlier and click ``Edit``. There find the ``Which events would you like to trigger this
webhook?`` radio-button and switch to ``Let me select individual events``.

A large list of possible events should appear beneath. Find and uncheck the ``Push`` event, and instead check the
``Pull requests``. After that create a new PR (requires additional branch, can be performed by GitHub automatically
when redacting single file). This should trigger the created post-commit configuration (as pass the new info to the
old `Generic Webhook Trigger`), but the build will most likely fail due to payload content differences.

So, to see the new payload, once again in webhook settings go to ``Recent Deliveries`` and find the latest payload.
As you can see, now ``repository.url`` contains ``https://api.github.com/repos/YOUR-USERNAME/universum-test-project``,
which might not be available to anonymous cloning. For now we can replace it with ``repository.html_url``, that
still contains old familiar ``https://github.com/YOUR-USERNAME/universum-test-project``.

But why ``https://api.github.com/``, and how to use this API to report the check status back to GitHub? To get to
this, we will need a GitHub Application as a unified way of communication between CI system and GitHub.


.. _guide#github-app:

Register a GitHub Application
-----------------------------

For the next step (reporting results to GitHub) we will need an active `GitHub Application
<https://docs.github.com/en/developers/apps>`__.



.. TBD
