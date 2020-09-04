FROM ubuntu:bionic

# Update package list and install wget
RUN apt update && apt install -y wget

# Install latest python & pip
RUN apt install -y python3.7 python3.7-distutils
RUN wget --no-check-certificate -O get-pip.py 'https://bootstrap.pypa.io/get-pip.py'
RUN python3.7 get-pip.py

# Install Git & gitpython
RUN apt install -y git
RUN python3.7 -m pip install gitpython six
