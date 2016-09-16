#!/usr/bin/env python

from subprocess import call, Popen, PIPE
import yaml
import sys
import pymongo
import time
import os

MONGO_DATA_DIR = "/data/db/"
CONFIG_SERVER_DATA_DIR = "/data/configdb/"
MONGOD_INSTALL_LOCATION = "/usr/bin/mongod"
MONGO_INSTALL_LOCATION = "/usr/bin/mongo "
MONGOS_INSTALL_LOCATION = "/usr/bin/mongos "
MONGODB_PORT = "27017"
CONFIG_SERVER_PORT = "27019"
QUERY_ROUTER_PORT = "27020"
YAML_PATH = "/etc/profile.d"
MONGO_DB_CONFIG_LOG_PATH = "/var/log/mongodb/mongod.log"
MONGO_DB_CONFIG_FILE_PATH="/etc/mongod.conf"
CLUSTER_FILE_LOCATION = "/etc/profile.d/cluster.yaml"
MONGO_DB_CONFIG_SERVER_DATA_PATH = "/data/configdb"
MONGODB_ULIMIT_VALUE1 = "*      soft    nofile  64000"
MONGODB_ULIMIT_VALUE2 = "*      hard    nofile  64000"
MONGODB_ULIMIT_VALUE3 = "*      soft    nproc  32000"
MONGODB_ULIMIT_VALUE4 = "*      hard    nproc  32000"
MONGODB_LIMITS_CONF_FILE = "/etc/security/limits.conf"
MONGODB_NPROC_CONF_FILE = "/etc/security/limits.d/90-nproc.conf"


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
      for i, replica_item_list in enumerate(data):
        for replica_ips in replica_item_list.items()[0][1]:
            if replica_ips["private_ip"] == curlstdout:
                is_master = replica_ips["is_master"]
                machine_ip = replica_ips["private_ip"]
                node_type = replica_ips["node_type"]

    return is_master, machine_ip, node_type


def configure_standalone_node():
    '''
    configures the standalone node
    :return:
    '''
    print "MongoDB standalone node configuration started..."
    call("service mongod stop", shell=True)
    call("mkdir " + MONGO_DATA_DIR + "  -p ", shell=True)
    command = MONGOD_INSTALL_LOCATION + " --port " + MONGODB_PORT + " --dbpath " + MONGO_DATA_DIR +\
          " < /dev/null > /dev/null 2>&1&  "
    call(command, shell=True)
    call("echo \"" + command + "&\" >> /etc/rc.local", shell=True)
    print "MongoDB standalone node configuration Completed."


def setup_cluster():
    '''
    :return:
    '''
    cluster_data = read_cluster_file()
    is_master, machine_ip, node_type = get_machine_data()

    for data in cluster_data:
      for node_list in data:
        for replica_ips in node_list.items()[0][1]:
            if replica_ips["private_ip"] == machine_ip:
                print "in first if condition."
                if node_type == "primary" or node_type == "secondary":
                    print "in second if condition."
                    configure_replica_set(node_list, is_master)
                    break
                elif node_type == "config":
                    print "in first elif condition."
                    configure_config_server()
                    break
                elif node_type == "router":
                    print "in second elif condition."
                    query_routers_host_list = data[len(data) - 1]["router"]
                    config_server_host_list = data[len(data) - 2]["config"]
                    configure_query_routers(query_routers_host_list, config_server_host_list)
                    add_shard_to_cluster(query_routers_host_list, data)
                    add_database_and_shard_collections(query_routers_host_list)
                    add_database_user(query_routers_host_list)
                    break


def configure_replica_set(replica_host_list, is_master):
    '''
    Configures the replica set
    :return:
    '''

    print "Configure replica set of MongoDB started..."
    replica_name = replica_host_list.items()[0][0]
    call("service mongod stop", shell=True)
    call("mkdir " + MONGO_DATA_DIR + "  -p ", shell=True)
    print "replica name " + replica_name
    command = MONGOD_INSTALL_LOCATION + " --replSet " + replica_name + " --port " + MONGODB_PORT \
              + " --logpath " + MONGO_DB_CONFIG_LOG_PATH + " --dbpath " + MONGO_DATA_DIR \
              + " --rest < /dev/null > /dev/null 2>&1&  "
    call("echo \"" + command + "\" > /tmp/mongo.sh", shell=True)
    call("bash /tmp/mongo.sh &", shell=True)
    call("echo \"" + command + "&\" >> /etc/rc.local", shell=True)

    try:
        call("echo " + MONGODB_ULIMIT_VALUE1 + " >> " + MONGODB_LIMITS_CONF_FILE)
        call("echo " + MONGODB_ULIMIT_VALUE2 + " >> " + MONGODB_LIMITS_CONF_FILE)
        call("echo " + MONGODB_ULIMIT_VALUE3 + " >> " + MONGODB_LIMITS_CONF_FILE)
        call("echo " + MONGODB_ULIMIT_VALUE4 + " >> " + MONGODB_LIMITS_CONF_FILE)

        call("echo " + MONGODB_ULIMIT_VALUE1 + " >> " + MONGODB_NPROC_CONF_FILE)
        call("echo " + MONGODB_ULIMIT_VALUE2 + " >> " + MONGODB_NPROC_CONF_FILE)
        call("echo " + MONGODB_ULIMIT_VALUE3 + " >> " + MONGODB_NPROC_CONF_FILE)
        call("echo " + MONGODB_ULIMIT_VALUE4 + " >> " + MONGODB_NPROC_CONF_FILE)
    except Exception as e:
        print "Exception while updating limits.comf file. " + e.message

    # if this is a master instance update node configuration
    if is_master:
        print "Master node configuration started."
        connection = pymongo.MongoClient()
        members_list = []
        for index, replica_ips in enumerate(replica_host_list.items()[0][1]):
            members_list.append({'_id': index, 'host': replica_ips["private_ip"] + ":" + MONGODB_PORT})
        conf = {'_id': replica_name, 'members': members_list}
        db = connection.get_database("admin")

        retry = 1
        max_try = 10
        while retry < max_try:
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

        add_collection()
        add_database_user()
    print "Configure replica set of MongoDB completed..."


def configure_config_server():
    '''
    Configure config servers i.e mongo instances
    :return:
    '''
    try:
        print "Config server configuration started."
        call("service mongod stop", shell=True)
        call("mkdir " + CONFIG_SERVER_DATA_DIR + "  -p ", shell=True)
        #call("chown " + CONFIG_SERVER_DATA_DIR, shell=True)
        command = MONGOD_INSTALL_LOCATION + " --configsvr --dbpath " + MONGO_DB_CONFIG_SERVER_DATA_PATH + " --logpath " + \
                  MONGO_DB_CONFIG_LOG_PATH + " --port " + CONFIG_SERVER_PORT + " < /dev/null > /dev/null 2>&1&"
        call("echo \"" + command + "\" > /tmp/mongo.sh", shell=True)
        call("bash /tmp/mongo.sh &", shell=True)
    except Exception as e:
        print "Exception while configuring config server. " + e.message


def configure_query_routers(config_server_host_list):
    '''
    Configure query routers i.e mongos instances
    :return:
    '''
    try:
        print "Query router configuration started."
        call("service mongod stop", shell=True)
        config_server_hostname_string = ""
        number_of_host = len(config_server_host_list.items()[0][1])
        for index, host_dict in enumerate(config_server_host_list.items()[0][1]):
            if index != number_of_host-1:
                config_server_hostname_string = config_server_hostname_string + host_dict["private_ip"] + ":" + CONFIG_SERVER_PORT + ","
            else:
                config_server_hostname_string = config_server_hostname_string + host_dict["private_ip"] + ":" + CONFIG_SERVER_PORT

        command = MONGOS_INSTALL_LOCATION + " --logpath " + MONGO_DB_CONFIG_LOG_PATH + " --configdb " \
                  + config_server_hostname_string + " --" + MONGODB_PORT + " < /dev/null > /dev/null 2>&1&"
        call("echo \"" + command + "\" > /tmp/mongo.sh", shell=True)
        call("bash /tmp/mongo.sh &", shell=True)
        print "Query router configuration completed."
    except Exception as e:
        print "Exception while configuring query routers. " + e.message


def add_shard_to_cluster(query_routers_host_list, data):
    '''
    add shards to cluster
    :return:
    '''
    try:
        print "Add shard to cluster started."
        query_router_host = query_routers_host_list.items()[0][1]["private_ip"]
        call("service mongod stop", shell=True)
        for node_list in data:
            replica_name = node_list.items()[0][0]
            for replica_ips in node_list.items()[0][1]:
                if replica_ips["node_type"] == "primary":
                    # Here we need to specify replicaset name and host name to add shard
                    call(MONGO_INSTALL_LOCATION + " " + query_router_host + ":" + MONGODB_PORT +
                         "/admin --eval 'db.runCommand( {addShard : \"" + replica_name + "/" + replica_ips["private_ip"]
                         + ":" + MONGODB_PORT + "\"})'")
        print "Add shard to cluster completed."
    except Exception as e:
        print "Exception while adding shard to cluster. " + e.message


def add_database_and_shard_collections(query_routers_host_list):
    '''
    add database and shard collections
    :return:
    '''
    try:
        print "Add database and shard collection started."
        query_router_host = query_routers_host_list.items()[0][1]["private_ip"]
        call("service mongod stop", shell=True)
        call(MONGO_INSTALL_LOCATION + " " + query_router_host + ":" + MONGODB_PORT
             + "/admin --eval 'printjson(db.runCommand( { enableSharding: \"" + os.environ.get("DATABASE_NAME") + "\" }))'", shell=True)
        print "Sharding enabled successfully."

        is_automatic_hash_on_id_enable = 1
        is_shard_keyhash_enable = 0
        if is_automatic_hash_on_id_enable == 1:
            print "In is_automatic_hash_on_id_enable."
            call(MONGO_INSTALL_LOCATION + " " + query_router_host + ":" + MONGODB_PORT + "/admin --eval 'printjson(db.runCommand( { shardCollection: \""
                 + os.environ.get("DATABASE_NAME") + "." + os.environ.get("COLLECTION_NAME") + "\", key: { \"_id\": \"hashed\" }}))'", shell=True)
            print "Sharded collection added successfully."
        else:
            # If no hash on shard key
            if is_shard_keyhash_enable == 1:
                print "In is_shard_keyhash_enable."
                call(MONGO_INSTALL_LOCATION + " " + query_router_host + ":" + MONGODB_PORT + "/admin --eval 'printjson(db.runCommand( { shardCollection: \""
                     + os.environ.get("DATABASE_NAME") + "." + os.environ.get("COLLECTION_NAME") + "\", key: {\"" + "shardkey" + "\": \"hashed\"} } ))'", shell=True)
                print "Out of is_shard_keyhash_enable."
            else:
                print "In else is_shard_keyhash_enable."
                call(MONGO_INSTALL_LOCATION + " " + query_router_host + ":" + MONGODB_PORT + "/" + os.environ.get("DATABASE_NAME")
                     + " --eval 'printjson(db.createCollection(\"" + os.environ.get("COLLECTION_NAME") + "\"))'", shell=True)
                call(MONGO_INSTALL_LOCATION + " " + query_router_host + ":" + MONGODB_PORT + "/admin --eval 'printjson(db.runCommand( { shardCollection: \""
                     + os.environ.get("DATABASE_NAME") + "." + os.environ.get("COLLECTION_NAME") + "\", key: {\"" + "shardkey" + "\":1} } ))'", shell=True)
                print "Out of else is_shard_keyhash_enable."
        print "Enable database and shard collection completed successfully."
    except Exception as e:
        print "Exception while enabling database and sharding collections. " + e.message


def add_collection(node_list):
    '''
    add collection
    :return:
    '''
    try:
         print "Add collection started..."
         call("/usr/bin/mongo " + node_list[1][0]["private_ip"] + ":" + MONGODB_PORT + "/" + os.environ.get("DATABASE_NAME")
              + " --eval 'printjson(db.createCollection(\"" - + os.environ.get("COLLECTION_NAME") + "\"))'", shell=True)
         print "Add collection completed successfully."
    except Exception as e:
        print "Exception while adding collection. " + e.message


def add_database_user(node_list):
    '''
    add database user
    :return:
    '''
    try:
        print "Add database user started..."
        call("/usr/bin/mongo " + node_list[1][0]["private_ip"] + ":" + MONGODB_PORT + "/" + os.environ.get("DATABASE_NAME")
             + " --eval 'printjson(db.createUser( { user: \"" - + os.environ.get("MASTER_USER") + "\", pwd: \"" +
             os.environ.get("MASTER_PASSWORD") + "\", roles: [ \"readWrite\" ] } ))'", shell=True)
        print "Add database user completed successfully."
    except Exception as e:
        print "Exception while adding database user. " + e.message


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
nodes_dict = {}
rep1_list = []
rep2_list = []
config_server_list = []
router_list = []
nodes_list = []
instances = instances.split()
if len(instances) > 1:
    for index, instance in enumerate(instances):
        if index < 3:
            if index % 3 != 0:
                rep1_list.append({'private_ip': instance, "node_type": "secondary", "is_master": False})
            else:
                rep1_list.append({'private_ip': instance, "node_type": "primary", "is_master": True})
            if index == 2:
                nodes_list.append(dict(rs0=rep1_list))
        elif 2 < index < 6:
            if index % 3 != 0:
                rep2_list.append({'private_ip': instance, "node_type": "secondary", "is_master": False})
            else:
                rep2_list.append({'private_ip': instance, "node_type": "primary", "is_master": True})
            if index == 5:
                nodes_list.append(dict(rs1=rep2_list))
        elif 5 < index < 9:
                config_server_list.append({'private_ip': instance, "node_type": "config", "is_master": False})
                if index == 8:
                    nodes_list.append(dict(config=config_server_list))
        elif index > 8:
                router_list.append({'private_ip': instance, "node_type": "router", "is_master": False})
                nodes_list.append(dict(router=router_list))

    write_cluster_file(nodes_list)
    setup_cluster()
else:
    for index, instance in enumerate(instances):
        rep1_list.append({'private_ip': instance, "node_type": "standalone", "is_master": False})
        nodes_list = dict(standalone=rep1_list)
    write_cluster_file(nodes_list)
    configure_standalone_node()
