#!/usr/bin/env python

from subprocess import call, Popen, PIPE
import yaml
import sys

MONGO_DATA_DIR = "/data/db/"
AGENT_INSTALL_LOCATION = "/opt"
MONGODB_PORT = "27017"
CONFIG_SERVER_PORT = "27019"
QUERY_ROUTER_PORT = "27020"
YAML_PATH = "/etc/profile.d"
MONGO_DB_CONFIG_LOG_PATH = "/data/mongodb.log"
MONGO_DB_CONFIG_FILE_PATH="/data/mongodb.conf"
MONGODB_ULIMIT_VALUE1="*      soft    nofile  64000"
MONGODB_ULIMIT_VALUE2="*      hard    nofile  64000"
MONGODB_ULIMIT_VALUE3="*      soft    nproc  32000"
MONGODB_ULIMIT_VALUE4="*      hard    nproc  32000"
MONGODB_LIMITS_CONF_FILE="/etc/security/limits.conf"
MONGODB_NPROC_CONF_FILE="/etc/security/limits.d/90-nproc.conf"
CLUSTER_FILE_LOCATION = "/etc/profile.d/cluster.yaml"
is_master = False
machine_ip = ""


def write_cluster_file(ip_address_dict):
    '''
    :param ip_address_dict:
    :return:
    '''
    cluster_file = open(CLUSTER_FILE_LOCATION, 'w+')
    yaml.dump(ip_address_dict, cluster_file, allow_unicode=False)

    read_cluster_flile()


def read_cluster_flile():
    process = Popen(["curl", "-sL", "169.254.169.254/latest/meta-data/local-ipv4"], stdout=PIPE, stderr=PIPE)
    curlstdout, curlstderr = process.communicate()
    stream = open(CLUSTER_FILE_LOCATION, "r")
    cluster_data = yaml.load_all(stream)
    for i, replica_item_list in enumerate(cluster_data.items()):
        for replica_ips in replica_item_list[1]:
            if replica_ips["private_ip"] == curlstdout:
                is_master = replica_ips["is_master"]
                machine_ip = replica_ips["private_ip"]
    return cluster_data


def configure_standalone_node():
    '''
    configures the standalone node
    :return:
    '''
    call("ln -s /data/db/mongodb " + AGENT_INSTALL_LOCATION + "/mongodb")

    command = AGENT_INSTALL_LOCATION + "/mongodb/bin/mongod  --port " + MONGODB_PORT + " --dbpath " + MONGO_DATA_DIR +\
          " < /dev/null > /dev/null 2>&1&  "
    call(command)
    call("echo \"" + command + "&\" >> /etc/rc.local")


def setup_cluster():
    '''
    :return:
    '''
    configure_replica_set()


def configure_replica_set():
    '''
    Configures the replica set
    :return:
    '''
    # Configures three nodes replica set
    node_list = prepare_replica_nodes_list()
    call("ln -s /data/db/mongodb " + AGENT_INSTALL_LOCATION + "/mongodb")

    command = AGENT_INSTALL_LOCATION + "/mongodb/bin/mongod --replSet " + node_list[0] + " --port " + MONGODB_PORT \
              + " --logpath " + MONGO_DB_CONFIG_LOG_PATH + " --dbpath " + MONGO_DATA_DIR \
              + " --rest < /dev/null > /dev/null 2>&1&  "
    call("echo \"" + command + "\" > /tmp/mongo.sh")
    call("bash /tmp/mongo.sh &")
    call("echo \"" + command + "&\" >> /etc/rc.local")

    call("sed --in-place '$ i\\" + MONGODB_ULIMIT_VALUE1 + "' " + MONGODB_LIMITS_CONF_FILE)
    call("sed --in-place '$ i\\" + MONGODB_ULIMIT_VALUE2 + "' " + MONGODB_LIMITS_CONF_FILE)
    call("sed --in-place '$ i\\" + MONGODB_ULIMIT_VALUE3 + "' " + MONGODB_LIMITS_CONF_FILE)
    call("sed --in-place '$ i\\" + MONGODB_ULIMIT_VALUE4 + "' " + MONGODB_LIMITS_CONF_FILE)

    call("sed --in-place '$ i\\" + MONGODB_ULIMIT_VALUE1 + "' " + MONGODB_NPROC_CONF_FILE)
    call("sed --in-place '$ i\\" + MONGODB_ULIMIT_VALUE2 + "' " + MONGODB_NPROC_CONF_FILE)
    call("sed --in-place '$ i\\" + MONGODB_ULIMIT_VALUE3 + "' " + MONGODB_NPROC_CONF_FILE)
    call("sed --in-place '$ i\\" + MONGODB_ULIMIT_VALUE4 + "' " + MONGODB_NPROC_CONF_FILE)

    # if this is a master instance update node configuration
    if is_master:
        call("mongo")
        call("use admin")
        process = Popen("rs.initiate({_id:" + node_list[0] + ", members: [{_id:1, host:" + node_list[1][1]["private_ip"]
                        + ":27017},{_id:2, host:" + node_list[1][2]["private_ip"] + ":27017}])")
        process.communicate()
        process = Popen("rs.conf()")
        output, err = process.communicate()


def prepare_replica_nodes_list():
    '''
    return the list of nodes in replica
    :return: node_list
    '''
    cluster_data = read_cluster_flile()
    for data in cluster_data:
        for i,replica_item_list in enumerate(data.items()):
            for replica_ips in replica_item_list[1]:
                if replica_ips["private_ip"] == machine_ip:
                    node_list = replica_item_list
        break

    return node_list


instances = sys.argv[1]
all_node_list = []
nodes_dict = {}
replica_sets = []
instances = instances.split()
if len(instances) > 1:
    for index, instance in enumerate(instances):
        if index % 3 != 0:
            all_node_list.append({'private_ip': instance, "node_type": "primary", "is_master": True})
            replica_sets.append(all_node_list)
        else:
            all_node_list.append({'private_ip': instance, "node_type": "secondary", "is_master": False})
            replica_sets.append(all_node_list)
    nodes_dict = dict(replica_1=replica_sets)

    write_cluster_file(nodes_dict)
    setup_cluster()
else:
    configure_standalone_node()


