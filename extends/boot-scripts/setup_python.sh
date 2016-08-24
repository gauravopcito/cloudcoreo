#!/bin/sh

## make sure pip is installed
if ! rpm -qa | grep -q python-pip; then
    yum install -y python-pip
fi

## make sure we have the latest boto installed
if ! pip list | grep -q boto; then
    pip install boto --upgrade
fi

## make sure we have filechunkio
if ! pip list | grep -q filechunkio; then
    pip install filechunkio --upgrade
fi
