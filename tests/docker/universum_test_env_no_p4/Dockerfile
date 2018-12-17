FROM ubuntu:xenial

# Update package list and install wget
RUN apt-get update && apt-get install -y wget

# Install latest python & pip
RUN apt-get install -y python
RUN wget --no-check-certificate -O get-pip.py 'https://bootstrap.pypa.io/get-pip.py'
RUN python get-pip.py

# Install Git & gitpython
RUN apt-get install -y git
RUN pip install gitpython
