#!/bin/bash

MXHOST=localhost
TCLIENT='temp_client_for_swarm'

if [ ! -e /var/run/configure-swarm ]; then
    /opt/perforce/swarm/sbin/configure-swarm.sh -n \
        -p "$P4PORT" -u "$P4USER" -w "$P4PASSWD" \
        -H "$HOSTNAME" -e "$MXHOST"
    touch /var/run/configure-swarm
    rm -f /etc/apache2/sites-enabled/000-default.conf
    service apache2 restart
    redis-server --port 7379 &
    echo $P4PASSWD | p4 login
    p4 depot -o .swarm | p4 depot -i
    p4 client -o $TCLIENT | p4 client -i
    p4 -c $TCLIENT sync .swarm/...
    mkdir -p .swarm/triggers
    p4 -c $TCLIENT edit .swarm/...
    cp /opt/perforce/swarm/p4-bin/scripts/swarm-trigger.pl .swarm/triggers/
    cp /opt/perforce/etc/swarm-trigger.conf .swarm/triggers/
    p4 -c $TCLIENT reconcile .swarm/...
    p4 -c $TCLIENT --field "Description=Add swarm triggers" change -o | p4 -c $TCLIENT submit -i
    p4 configure set dm.keys.hide=2
    p4 configure set filetype.bypasslock=1

    rm -rf .swarm
    p4 client -d $TCLIENT
fi
echo '<?php phpinfo(); ?>' > /opt/perforce/swarm/public/phpinfo.php
for i in `seq 20`; do
    test -e /var/run/httpd/httpd.pid && break
    sleep 2
done

exec  --pid=$(cat $PID_FILE) -F /var/log/httpd/*
