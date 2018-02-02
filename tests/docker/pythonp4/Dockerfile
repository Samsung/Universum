FROM ubuntu:precise

# Update package list and install wget
RUN apt-get update && apt-get install -y wget

# Get perforce packages
RUN wget -q http://package.perforce.com/perforce.pubkey -O - | apt-key add - && \
    echo "deb http://package.perforce.com/apt/ubuntu precise release" > /etc/apt/sources.list.d/perforce.list && \
    apt-get update

RUN apt-get install -y helix-cli && apt-get install -y perforce-p4python && \
    apt-get install -y git

RUN wget --no-check-certificate -O get-pip.py 'https://bootstrap.pypa.io/get-pip.py'
RUN python get-pip.py

# Volumes for server roots and triggers

# Add startup file and run it by default
COPY run.sh /
CMD ["/run.sh"]
