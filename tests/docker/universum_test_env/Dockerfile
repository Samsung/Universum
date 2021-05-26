FROM ubuntu:bionic AS universum_test_env_no_vcs
ARG PYTHON=python3.7

# Please note: apt-get install will produce the following message in stderr:
# 'debconf: delaying package configuration, since apt-utils is not installed`
# In scope of non-interactive configuration there's no need to fix it

# Update package list and install wget
RUN apt-get update && apt-get install -y wget software-properties-common

# Install latest python & pip
RUN add-apt-repository ppa:deadsnakes/ppa && apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y ${PYTHON}-dev ${PYTHON}-distutils gnupg2 libssl-dev build-essential

# Please note: wget is writing logs to stderr, these logs are not any kind of warning
RUN wget --no-verbose --no-check-certificate -O get-pip.py 'https://bootstrap.pypa.io/get-pip.py'
RUN ${PYTHON} get-pip.py

FROM universum_test_env_no_vcs AS universum_test_env_no_p4
ARG PYTHON=python3.7

# Install Git & gitpython
RUN apt-get install -y git

# Please note, that using Pip as a root user is, indeed, a bad practice
# But in case of 'gitpython' and 'p4python' installing packages into system once per image instead of repeatedly
# installing them into every newly created container as user
# a) is not that dangerous as we use disposable docker containers anyway
# b) saves a lot of times and adds more stability to tests
RUN ${PYTHON} -m pip install gitpython

FROM universum_test_env_no_p4 AS universum_test_env
ARG PYTHON=python3.7

# Install Perforce and p4python
RUN wget -q http://package.perforce.com/perforce.pubkey -O - | APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=1 apt-key add - && \
    echo "deb http://package.perforce.com/apt/ubuntu bionic release" > /etc/apt/sources.list.d/perforce.list && \
    apt-get update

RUN apt-get install -y helix-cli
RUN ${PYTHON} -m pip install p4python
