FROM ubuntu:bionic
ARG PYTHON=python3.7

# Update package list and install wget
RUN apt update && apt install -y wget software-properties-common

# Install python 2 for pylint testing
RUN DEBIAN_FRONTEND=noninteractive apt install -y python
RUN wget --no-check-certificate -O get-pip.py 'https://bootstrap.pypa.io/pip/2.7/get-pip.py'
RUN python get-pip.py
RUN python -m pip install pylint

# Install uncrustify for testing
RUN DEBIAN_FRONTEND=noninteractive apt install -y uncrustify

# Install latest python & pip
RUN add-apt-repository ppa:deadsnakes/ppa && apt update
RUN DEBIAN_FRONTEND=noninteractive apt install -y ${PYTHON}-dev ${PYTHON}-distutils gnupg2 libssl-dev build-essential
RUN wget --no-check-certificate -O get-pip.py 'https://bootstrap.pypa.io/get-pip.py'
RUN ${PYTHON} get-pip.py

# Install Git & gitpython
RUN apt install -y git
RUN ${PYTHON} -m pip install gitpython

# Install Perforce and p4python
RUN wget -q http://package.perforce.com/perforce.pubkey -O - | apt-key add - && \
    echo "deb http://package.perforce.com/apt/ubuntu bionic release" > /etc/apt/sources.list.d/perforce.list && \
    apt update

RUN apt install -y helix-cli
RUN ${PYTHON} -m pip install p4python
