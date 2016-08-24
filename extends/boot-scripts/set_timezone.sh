#!/bin/bash

if [ -z "${TIMEZONE:-}" ]; then
    TIMEZONE="America/Chicago"
fi
ln -sf /usr/share/zoneinfo/${TIMEZONE} /etc/localtime
