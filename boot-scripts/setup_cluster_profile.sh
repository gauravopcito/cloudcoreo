#!/bin/bash
######################################################################
##
## Required Variables:
##   CLUSTER_SIZE_MIN
##
## Optional Variables:
##   WAIT_FOR_CLUSTER_MIN
##
######################################################################
##
## Required Packages
##   aws-cli in pip
##
######################################################################
set -x

work_dir='/var/tmp/cluster'

mkdir -p "$work_dir"

region="$(curl -sL 169.254.169.254/latest/meta-data/placement/availability-zone | sed '$s/.$//')"

addresses="$(python ./lib/group_addresses.py)"
## lets wait until the minimum actually exists
if [ -n "${WAIT_FOR_CLUSTER_MIN:-}" ]; then
    while [ "$(wc -l < <(echo $addresses | perl -pe 's{\s}{\n}g'))" -lt "${CLUSTER_SIZE_MIN:-0}" ]; do
	sleep 1
	addresses="$(python ./lib/group_addresses.py)"
    done
fi

python "./lib/setup_node_data.py" "$addresses"
