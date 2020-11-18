FROM ubuntu:bionic
ARG PYTHON_VERSION=3.7

# Update package list and install wget
RUN apt update && apt install -y wget

# Install latest python & pip
RUN apt install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-distutils
RUN wget --no-check-certificate -O get-pip.py 'https://bootstrap.pypa.io/get-pip.py'
RUN python${PYTHON_VERSION} get-pip.py

# Install Git & gitpython
RUN apt install -y git
RUN python${PYTHON_VERSION} -m pip install gitpython

# Install Perforce and p4python
RUN wget -q http://package.perforce.com/perforce.pubkey -O - | apt-key add - && \
    echo "deb http://package.perforce.com/apt/ubuntu bionic release" > /etc/apt/sources.list.d/perforce.list && \
    apt update

RUN apt install -y helix-cli
RUN pip${PYTHON_VERSION} install p4python
