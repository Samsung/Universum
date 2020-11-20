FROM ubuntu:bionic
ARG PYTHON=python3.7

# Update package list and install wget
RUN apt update && apt install -y wget

# Install latest python & pip
RUN apt install -y ${PYTHON} ${PYTHON}-distutils gnupg2
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
