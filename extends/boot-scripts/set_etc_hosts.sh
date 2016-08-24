#!/bin/bash

host_entry="$(curl 169.254.169.254/latest/meta-data/local-ipv4) $(hostname)"

if ! grep -q "$host_entry" /etc/hosts; then
    echo "$(curl 169.254.169.254/latest/meta-data/local-ipv4) $(hostname)" >> /etc/hosts
fi
