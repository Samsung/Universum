FROM ubuntu:bionic
ARG PYTHON=python3.7

# Update package list and install wget
RUN apt-get update && apt-get install -y wget software-properties-common

# Install latest python & pip
RUN add-apt-repository ppa:deadsnakes/ppa && apt-get update
RUN apt-get install -y ${PYTHON}-dev ${PYTHON}-distutils gnupg2 libssl-dev build-essential
RUN wget --no-verbose --no-check-certificate -O get-pip.py 'https://bootstrap.pypa.io/get-pip.py'
RUN ${PYTHON} get-pip.py
