FROM ubuntu:bionic
ARG PYTHON=python3.7

# Update package list and install wget
RUN apt-get update && apt-get install -y wget software-properties-common

# Install latest python & pip
RUN add-apt-repository ppa:deadsnakes/ppa && apt-get update
RUN apt-get install -y ${PYTHON}-dev ${PYTHON}-distutils gnupg2 libssl-dev build-essential
RUN wget --no-verbose --no-check-certificate -O get-pip.py 'https://bootstrap.pypa.io/get-pip.py'
RUN ${PYTHON} get-pip.py

# Install Git & gitpython
RUN apt-get install -y git
RUN ${PYTHON} -m pip install gitpython

# Install Perforce and p4python
RUN wget -q http://package.perforce.com/perforce.pubkey -O - | APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=1 apt-key add - && \
    echo "deb http://package.perforce.com/apt/ubuntu bionic release" > /etc/apt/sources.list.d/perforce.list && \
    apt-get update

RUN apt-get install -y helix-cli
RUN ${PYTHON} -m pip install p4python
