#!/bin/bash

MXHOST=localhost

if [ ! -e /var/run/configure-swarm ]; then
    /opt/perforce/swarm/sbin/configure-swarm.sh -n \
        -p "$P4PORT" -u "$P4USER" -w "$P4PASSWD" \
        -H $HOSTNAME -e "$MXHOST"
    touch /var/run/configure-swarm
    rm -f /etc/apache2/sites-enabled/000-default.conf
    service apache2 restart
fi
echo '<?php phpinfo(); ?>' > /opt/perforce/swarm/public/phpinfo.php
for i in `seq 20`; do
    test -e /var/run/httpd/httpd.pid && break
    sleep 2
done

exec  --pid=$(cat $PID_FILE) -F /var/log/httpd/*
