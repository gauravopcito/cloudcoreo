from subprocess import call, check_output, Popen
import yaml
import sys

DB_MOUNT_PATH = "/data/db/"
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


def write_cluster_file(ip_address_dicts):
    '''
    :param ip_address_dicts:
    :return:
    '''
    cluster_file = open(CLUSTER_FILE_LOCATION, 'w+')
    yaml.dump(ip_address_dicts, cluster_file, allow_unicode=False)

    read_cluster_flile()


def read_cluster_flile():
    local_address = check_output("curl -sL 169.254.169.254/latest/meta-data/local-ipv4")
    stream = open(CLUSTER_FILE_LOCATION, "r")
    cluster_data = yaml.load_all(stream)
    for data_list in cluster_data:
        for data in data_list:
            if data["private_ip_address"] == local_address:
                is_master = data["is_master"]


def configure_standalone_node():
    '''
    :return:
    '''
    call("chkconfig mongod on")
    call("service mongod start")
    call("ln -s /data/db/mongodb " + AGENT_INSTALL_LOCATION + "/mongodb")

    command = AGENT_INSTALL_LOCATION + "/mongodb/bin/mongod  --port " + MONGODB_PORT + " --dbpath " + DB_MOUNT_PATH +\
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
    :return:
    '''
    # Configures three nodes replica set
    node_list = prepare_replica_nodes_list()
    call("chkconfig mongod on")
    call("service mongod start")
    call("ln -s /data/db/mongodb " + AGENT_INSTALL_LOCATION + "/mongodb")

    command = AGENT_INSTALL_LOCATION + "/mongodb/bin/mongod --replSet " + "replicaSetName" + " --port " + MONGODB_PORT \
              + " --logpath " + MONGO_DB_CONFIG_LOG_PATH + " --dbpath " + DB_MOUNT_PATH \
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

    # Update master node configuration
    if is_master:
        call("mongo")
        call("use admin")
        process = Popen("rs.initiate({_id:replicaSetName, members: [{_id:1, host:" + node_list[1] + ":27017},{_id:1, host:"
             + node_list[2] + ":27017}])")
        (output, err) = process.communicate()
        process = Popen("rs.conf()")
        (output, err) = process.communicate()


def prepare_replica_nodes_list():
    '''
    :param:
    :return:
    '''
    local_address = check_output("curl -sL 169.254.169.254/latest/meta-data/local-ipv4")
    stream = open(CLUSTER_FILE_LOCATION, "r")
    cluster_data = yaml.load_all(stream)

    mongo_node_list = []
    for data_list in cluster_data:
        for index, data in enumerate(data_list):
            if data["private_ip_address"] == local_address:
                mongo_node_list.append(data["private_ip_address"])
                mongo_node_list.append(data_list[index+1]["private_ip_address"])
                mongo_node_list.append(data_list[index+2]["private_ip_address"])
                break

    return mongo_node_list


instances = sys.argv[1]
all_node_list = []
nodes_dict = {}

if len(instances.split()) > 1:
    for i, instance in enumerate(range(0, len(instances))):
                if i == 10:
            all_node_list.append({'private_ip_address': instance, "node_type": "Query", "is_master":"False"})
        if i >= 6:
            all_node_list.append({'private_ip_address': instance, "node_type": "Config", "is_master":"False"})
        if i % 3 != 0:
            all_node_list.append({'private_ip_address': instance, "node_type":"Secondary", "is_master":"False"})
        else:
            all_node_list.append({'private_ip_address': instance, "node_type":"Primary", "is_master":"True"})
        nodes_dict = all_node_list

        write_cluster_file(nodes_dict)
        setup_cluster()
else:
    configure_standalone_node()


