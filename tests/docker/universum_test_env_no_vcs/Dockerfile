FROM ubuntu:bionic
ARG PYTHON_VERSION=3.7

# Update package list and install wget
RUN apt update && apt install -y wget

# Install latest python & pip
RUN apt install -y python${PYTHON_VERSION} python${PYTHON_VERSION}-distutils
RUN wget --no-check-certificate -O get-pip.py 'https://bootstrap.pypa.io/get-pip.py'
RUN python${PYTHON_VERSION} get-pip.py
