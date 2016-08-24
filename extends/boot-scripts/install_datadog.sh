#!/bin/bash

## if there is no datadog key supplied, exit
if [ -z "${DATADOG_KEY}" ]; then
    exit 0
fi

cat <<EOF > /etc/yum.repos.d/datadog.repo
[datadog]
name = Datadog, Inc.
baseurl = http://yum.datadoghq.com/rpm/x86_64/
enabled=1
gpgcheck=0
EOF

yum makecache
yum -y install datadog-agent

sh -c "sed 's/api_key:.*/api_key: ${DATADOG_KEY}/' /etc/dd-agent/datadog.conf.example > /etc/dd-agent/datadog.conf"

/etc/init.d/datadog-agent restart
