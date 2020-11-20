FROM ubuntu:bionic
ARG PYTHON_VERSION=3.7
ARG PYTHON=python${PYTHON_VERSION}

# Update package list and install wget
RUN apt update && apt install -y wget

# Install latest python & pip
RUN apt install -y ${PYTHON} ${PYTHON}-distutils gnupg2
RUN wget --no-check-certificate -O get-pip.py 'https://bootstrap.pypa.io/get-pip.py'
RUN ${PYTHON} get-pip.py
