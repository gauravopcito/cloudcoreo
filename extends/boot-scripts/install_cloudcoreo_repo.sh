#!/bin/sh

## install the cloudcoreo yum repo
rpm -ivh https://s3.amazonaws.com/cloudcoreo-yum/repo/tools/cloudcoreo-repo-0.0.3-1.noarch.rpm 
yum makecache
