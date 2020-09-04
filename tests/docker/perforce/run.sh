#!/bin/bash

# SIGTERM-handler
term_handler() {
  >&2 echo "Got SIGTERM"
  kill ${!}
  p4dctl stop $SERVER_NAME
  exit 143; # 128 + 15 -- SIGTERM
}

# setup handlers
# on callback, kill the last background process, which is `tail -f ...` and execute the specified handler
trap 'term_handler' SIGTERM


# Perforce paths
CONFIGURE_SCRIPT=/opt/perforce/sbin/configure-perforce-server.sh
SERVERS_ROOT=/opt/perforce/servers
CONFIG_ROOT=/etc/perforce/p4dctl.conf.d
SERVER_ROOT=$SERVERS_ROOT/$SERVER_NAME

# Theese need to be defined
if [ -z "$SERVER_NAME" ]; then
    echo FATAL: SERVER_NAME not defined 1>&2
    exit 1;
fi
if [ -z "$P4PASSWD" ]; then
    echo FATAL: P4PASSWD not defined 1>&2
    exit 1;
fi

# Default values
P4USER=${P4USER:-p4admin}
P4PORT=${P4PORT:-1666}

# Check if the server was configured. If not, configure it.
if [ ! -f $CONFIG_ROOT/$SERVER_NAME.conf ]; then
    echo Perforce server $SERVER_NAME not configured, configuring.

    # If the root path already exists, we're configuring an existing server
    $CONFIGURE_SCRIPT -n \
        -r $SERVER_ROOT \
        -p $P4PORT \
        -u $P4USER \
        -P $P4PASSWD \
        $SERVER_NAME

    p4 -p $P4PORT configure set server=1

    echo Server info:
    p4 -p $P4PORT info
else
    # Configuring the server also starts it, if we've not just configured a
    # server, we need to start it ourselves.
    p4dctl start $SERVER_NAME
fi

# Pipe server log and wait until the server dies
PID_FILE=/var/run/p4d.$SERVER_NAME.pid

# wait forever
while true
do
  /usr/bin/tail --pid=$(cat $PID_FILE) -n 0 -f "$SERVER_ROOT/logs/log" & wait ${!}
done
