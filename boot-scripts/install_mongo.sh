#!/bin/bash

MONGO_DB_VERSION="${MONGO_DB_VERSION:-3.2.5}"
MONGO_DATA_DIR="${MONGO_DATA_DIR:-}"

echo "====================IN INSTALL MONGO SCRIPT=========================="
yum install -y "mongodb-org-${MONGO_DB_VERSION}" "mongodb-org-server-${MONGO_DB_VERSION}" "mongodb-org-shell-${MONGO_DB_VERSION}" "mongodb-org-mongos-${MONGO_DB_VERSION}" "mongodb-org-tools-${MONGO_DB_VERSION}"

## don't upgrade mongo now that we have it installed
if ! grep -q "exclude=mongodb-org,mongodb-org-server,mongodb-org-shell,mongodb-org-mongos,mongodb-org-tools" /etc/yum.conf; then
    echo "exclude=mongodb-org,mongodb-org-server,mongodb-org-shell,mongodb-org-mongos,mongodb-org-tools" >> /etc/yum.conf
fi

## mongodb mounts in /data/db by default - if we want it somewhere else we keep that dir for simplicity and ln -sf it to the new path
if [ -z "$MONGO_DATA_DIR" ]; then
    rm -rf /data/db
    mkdir -p "${MONGO_DATA_DIR}"
    # link the new dir
    ln -sf "${MONGO_DATA_DIR}" /opt/mongodb
fi

perl -i -pe 's{(^\s*bindIp:)}{#\1}g' /etc/mongod.conf

service mongod stop || echo "mongo already stopped"

