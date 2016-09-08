#!/usr/bin/env python

from subprocess import call, Popen, PIPE
import yaml
import sys
import pymongo
import time

MONGO_DATA_DIR = "/data/db/"
AGENT_INSTALL_LOCATION = "/usr/bin/mongod"
MONGODB_PORT = "27017"
CONFIG_SERVER_PORT = "27019"
QUERY_ROUTER_PORT = "27020"
YAML_PATH = "/etc/profile.d"
MONGO_DB_CONFIG_LOG_PATH = "/var/log/mongodb/mongod.log"
MONGO_DB_CONFIG_FILE_PATH="/etc/mongod.conf"
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


def read_cluster_file():
    '''
    read the cluster yaml file
    :return: cluster_data
    '''
    stream = open(CLUSTER_FILE_LOCATION, "r")
    cluster_data = yaml.load_all(stream)
    return cluster_data


def get_machine_data():
    '''
    get the vm details like private ip address and is_master vm
    :return:
    '''
    process = Popen(["curl", "-sL", "169.254.169.254/latest/meta-data/local-ipv4"], stdout=PIPE, stderr=PIPE)
    curlstdout, curlstderr = process.communicate()
    stream = open(CLUSTER_FILE_LOCATION, "r")
    cluster_data = yaml.load_all(stream)
    for data in cluster_data:
      for i, replica_item_list in enumerate(data.items()):
        for replica_ips in replica_item_list[1]:
            if replica_ips["private_ip"] == curlstdout:
                is_master = replica_ips["is_master"]
                machine_ip = replica_ips["private_ip"]

    return is_master, machine_ip


def configure_standalone_node():
    '''
    configures the standalone node
    :return:
    '''
    print "MongoDB standalone node configuration started..."
    call("service mongod stop", shell=True)
    call("mkdir " + MONGO_DATA_DIR + "  -p ", shell=True)
    command = AGENT_INSTALL_LOCATION + " --port " + MONGODB_PORT + " --dbpath " + MONGO_DATA_DIR +\
          " < /dev/null > /dev/null 2>&1&  "
    call(command, shell=True)
    call("echo \"" + command + "&\" >> /etc/rc.local", shell=True)
    print "MongoDB standalone node configuration Completed."


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
    node_list = prepare_replica_nodes_list()

    print "Configure replica set of MongoDB started..."
    call("service mongod stop", shell=True)
    call("mkdir " + MONGO_DATA_DIR + "  -p ", shell=True)
    command = AGENT_INSTALL_LOCATION + " --replSet " + node_list[0] + " --port " + MONGODB_PORT \
              + " --logpath " + MONGO_DB_CONFIG_LOG_PATH + " --dbpath " + MONGO_DATA_DIR \
              + " --rest < /dev/null > /dev/null 2>&1&  "
    call("echo \"" + command + "\" > /tmp/mongo.sh", shell=True)
    call("bash /tmp/mongo.sh &", shell=True)
    call("echo \"" + command + "&\" >> /etc/rc.local", shell=True)

    is_master, machine_ip = get_machine_data()

    # if this is a master instance update node configuration
    if is_master:
        connection = pymongo.MongoClient()
        conf = {'_id': node_list[0],
                     'members': [{'_id': 0, 'host': node_list[1][0]["private_ip"] + ":27017"}, {'_id': 1, 'host': node_list[1][1]["private_ip"] + ":27017"}, {'_id': 2, 'host': node_list[1][2]["private_ip"] + ":27017"}]}
        db = connection.get_database("admin")

        retry = 1
        max_try = 10
        while retry <= max_try:
            is_retry_required = False
            try:
                db.command('replSetInitiate', conf, check=True)
                print "Master node configuration completed successfully."
                print "Replica configured successfully."
                break
            except Exception as e:
                is_retry_required = True
                if is_retry_required:
                    print "rs.initiate() failed. Waiting for cluster configuration. Retrying in some time..."
                retry += 1
                time.sleep(60)
                print "retrying mongo db configuration."
                if retry == max_try:
                    print "Failed to configure replica set."

        add_collection(node_list)

        add_database_user(node_list)


def add_collection(node_list):
    '''
    add collection
    :return:
    '''
    try:
         call("/usr/bin/mongo " + node_list[1][0]["private_ip"] + ":" + MONGODB_PORT + "/" + "cloudcoreodb" + " --eval 'printjson(db.createCollection(\""
             + "cloudcoreocoll" + "\"))'", shell=True)
    except Exception as e:
        print "Collection not get added."


def add_database_user(node_list):
    '''
    add database user
    :return:
    '''
    try:
        call("/usr/bin/mongo " + node_list[1][0]["private_ip"] + ":" + MONGODB_PORT + "/" + "cloudcoreodb" + " --eval 'db.createUser( { user: \""
             + "cloudcoreouser" + "\", pwd: \"" + "cloudcoreopass" + "\", roles: [ \"readWrite\" ] } )'", shell=True)
    except Exception as e:
        print "User not get added."

def prepare_replica_nodes_list():
    '''
    return the list of nodes in replica
    :return: node_list
    '''
    process = Popen(["curl", "-sL", "169.254.169.254/latest/meta-data/local-ipv4"], stdout=PIPE, stderr=PIPE)
    curlstdout, curlstderr = process.communicate()
    stream = open(CLUSTER_FILE_LOCATION, "r")
    cluster_data = yaml.load_all(stream)
    node_list = []
    for data in cluster_data:
        for i, replica_item_list in enumerate(data.items()):
            for replica_ips in replica_item_list[1]:
                if replica_ips["private_ip"] == curlstdout:
                    node_list = replica_item_list
            break

    return node_list


instances = sys.argv[1]
all_node_list = []
nodes_dict = {}
instances = instances.split()
if len(instances) > 1:
    for index, instance in enumerate(instances):
        if index % 3 != 0:
            all_node_list.append({'private_ip': instance, "node_type": "secondary", "is_master": False})
        else:
            all_node_list.append({'private_ip': instance, "node_type": "primary", "is_master": True})
    nodes_dict = dict(rs0=all_node_list)

    write_cluster_file(nodes_dict)
    setup_cluster()
else:
    for index, instance in enumerate(instances):
        all_node_list.append({'private_ip': instance, "node_type": "standalone", "is_master": False})
    nodes_dict = dict(standalone=all_node_list)
    write_cluster_file(nodes_dict)
    configure_standalone_node()
