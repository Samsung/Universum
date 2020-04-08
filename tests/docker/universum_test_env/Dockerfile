FROM ubuntu:bionic

# Update package list and install wget
RUN apt update && apt install -y wget

# Install latest python & pip
RUN apt install -y python3.7 python3.7-distutils gnupg2
RUN wget --no-check-certificate -O get-pip.py 'https://bootstrap.pypa.io/get-pip.py'
RUN python3.7 get-pip.py

# Install Git & gitpython
RUN apt install -y git
RUN python3.7 -m pip install gitpython six

# Install Perforce and p4python
RUN wget -q http://package.perforce.com/perforce.pubkey -O - | apt-key add - && \
    echo "deb http://package.perforce.com/apt/ubuntu bionic release" > /etc/apt/sources.list.d/perforce.list && \
    apt update

RUN apt install -y helix-cli && apt-get install -y perforce-p4python3-python3.7
RUN ln -sfn /usr/bin/python3.7 /usr/bin/python3
