FROM ubuntu:bionic

# Please note: apt-get install will produce the following message in stderr:
# 'debconf: delaying package configuration, since apt-utils is not installed`
# In scope of non-interactive configuration there's no need to fix it

# Update package list and install wget
RUN apt-get update && apt-get install -y wget gnupg2

# Get perforce packages
RUN wget -q http://package.perforce.com/perforce.pubkey -O - | APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=1 apt-key add - && \
    echo "deb http://package.perforce.com/apt/ubuntu bionic release" > /etc/apt/sources.list.d/perforce.list && \
    apt-get update

RUN apt-get install -y helix-p4d curl

# Volumes for server roots and triggers
#VOLUME /opt/perforce/servers
#VOLUME /opt/perforce/triggers

EXPOSE 1666

# Add startup file and run it by default
COPY run.sh /
CMD ["/run.sh"]
