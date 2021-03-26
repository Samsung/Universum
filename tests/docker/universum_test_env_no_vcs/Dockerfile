FROM ubuntu:bionic
ARG PYTHON=python3.7

# Update package list and install wget
RUN apt update && apt install -y wget software-properties-common

# Install latest python & pip
RUN add-apt-repository ppa:deadsnakes/ppa && apt update
RUN apt install -y ${PYTHON} ${PYTHON}-distutils gnupg2
RUN wget --no-check-certificate -O get-pip.py 'https://bootstrap.pypa.io/get-pip.py'
RUN ${PYTHON} get-pip.py
