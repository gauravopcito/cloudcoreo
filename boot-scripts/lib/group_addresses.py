#!/usr/bin/env python

from operator import itemgetter
import boto
import boto.ec2
import boto.ec2.autoscale
from boto.exception import EC2ResponseError
import datetime
import os
import sys
from optparse import OptionParser
from boto.vpc import VPCConnection
import subprocess
import socket
import time
import subprocess

MY_AZ = None
INSTANCE_ID = None


def cmd_output(args, **kwds):
    # this function will run a command on the OS and return the result
    kwds.setdefault("stdout", subprocess.PIPE)
    kwds.setdefault("stderr", subprocess.STDOUT)
    proc = subprocess.Popen(args, **kwds)
    return proc.communicate()[0]


def meta_data(dataPath):
    # using 169.254.169.254 instead of 'instance-data' because some people
    # like to modify their dhcp tables...
    return cmd_output(["curl", "-sL", "169.254.169.254/latest/meta-data/" + dataPath])


def get_availabilityzone():
    # cached
    global MY_AZ
    if MY_AZ is None:
        MY_AZ = meta_data("placement/availability-zone")
    return MY_AZ


def get_region():
  return get_availabilityzone()[:-1]


def getInstanceId():
    # cached
    global INSTANCE_ID
    if INSTANCE_ID == None:
        INSTANCE_ID = meta_data("instance-id")
    return INSTANCE_ID


def get_me():
    # don't cache this as our instance attributes can change
    return EC2.get_only_instances(instance_ids=[getInstanceId()])[0]


def get_myasg_name():
    allTags = get_me().tags
    for tag in allTags:
        if 'aws:autoscaling:groupName' in tag:
            return allTags[tag]


def get_asg_instances(asg_name):
    group = AUTOSCALE.get_all_groups([asg_name])[0]
    instance_ids = [i.instance_id for i in group.instances]
    reservations = EC2.get_all_instances(instance_ids)
    instances = [i for r in reservations for i in r.instances]
    get_asg_activity(asg_name)
    return instances


def get_asg_activity():
    group = AUTOSCALE.get_all_groups([my_asg_name])[0]
    activities = group.get_activities()
    activity = activities[-1]
    print "====== before activity ======="
    print activity
    return activity


EC2 = boto.ec2.connect_to_region(get_region())
AUTOSCALE = boto.ec2.autoscale.connect_to_region(get_region())

my_asg_name = get_myasg_name()
oldest_instance = None
if my_asg_name != None:
    instances = get_asg_instances(my_asg_name)
    times = []
    for instance in range(0, len(instances)):
        times.append({'id':instances[instance].id, 'launch_time':instances[instance].launch_time, 'private_ip_address': instances[instance].private_ip_address })
    sor = sorted(times, key=lambda k: k['launch_time'])
    for ins in range(0, len(sor)):
        if sor[ins]['private_ip_address'] is not None:
            print sor[ins]['private_ip_address']
else:
    print get_me().private_ip_address
