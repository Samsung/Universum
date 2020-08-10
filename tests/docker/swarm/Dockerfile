FROM ubuntu:bionic

ENV DEBIAN_FRONTEND noninteractive

# Update package list and install wget
RUN apt-get update && apt-get install -y apt-utils wget gnupg2

# Get perforce packages
RUN wget -q http://package.perforce.com/perforce.pubkey -O - | apt-key add - && \
    echo 'deb http://package.perforce.com/apt/ubuntu bionic release' > /etc/apt/sources.list.d/perforce.sources.list && \
    apt-get update

RUN apt-get install -y curl apache2 helix-swarm helix-cli helix-swarm-triggers helix-swarm-optional

# Volumes for server roots and triggers
#VOLUME /opt/perforce/servers
#VOLUME /opt/perforce/triggers

EXPOSE 80 443

# Add startup file and run it by default
COPY run.sh /
CMD ["/run.sh"]
