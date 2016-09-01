import subprocess
import yaml
import sys

DB_MOUNT_PATH = "/data/db/"
AGENT_INSTALL_LOCATION = "/opt"
REPLICA_PORT = "27017"
CONFIG_SERVER_PORT = "27019"
QUERY_ROUTER_PORT = "27020"
YAML_PATH = "/etc/profile.d"


def setup_node_type(ip_address_dicts):
    '''
    :param ip_address_dicts:
    :return:
    '''
    ip_address = subprocess.check_output("curl -sL 169.254.169.254/latest/meta-data/local-ipv4")

    profile_script = "/etc/profile.d"

    yaml_file = open(profile_script + "/cluster.yaml", 'w+')
    yaml.dump(ip_address_dicts, yaml_file, allow_unicode=False)

    stream = open(profile_script + "/cluster.yaml", "r")
    cluster_data = yaml.load_all(stream)
    for data_list in cluster_data:
        for data in data_list:
            if data["private_ip_address"] == ip_address:
                is_master = data["is_master"]


def configure_standalone_node():
    '''
    :return:
    '''
    subprocess.check_call("chkconfig mongod on")
    subprocess.check_call("service mongod start")
    subprocess.check_call("ln -s /data/db/mongodb " + AGENT_INSTALL_LOCATION + "/mongodb")

    command = AGENT_INSTALL_LOCATION + "/mongodb/bin/mongod  --port " + REPLICA_PORT + " --dbpath " + DB_MOUNT_PATH +\
          " < /dev/null > /dev/null 2>&1&  "
    subprocess.check_call(command)
    subprocess.check_call("echo \"" + command + "&\" >> /etc/rc.local")


def configure_replica_set():
    '''
    :return:
    '''


instances = sys.argv[1]
ip_address_list = []
ip_address_dicts = {}

if len(instances) > 1:
    for i, instance in enumerate(range(0, len(instances))):
        if i == 10:
            ip_address_list.append({'id': instances[instance].id, 'launch_time': instances[instance].launch_time,
                                    'private_ip_address': instances[instance].private_ip_address,"node_type": "Query"})
        if i >= 6:
            ip_address_list.append({'id': instances[instance].id, 'launch_time': instances[instance].launch_time,
                                    'private_ip_address': instances[instance].private_ip_address, "node_type": "Config"})
        if i % 3 != 0:
            ip_address_list.append({'id':instances[instance].id, 'launch_time':instances[instance].launch_time,
                          'private_ip_address': instances[instance].private_ip_address, "node_type":"Secondary"})
        else:
            ip_address_list.append({'id': instances[instance].id, 'launch_time': instances[instance].launch_time,
                          'private_ip_address': instances[instance].private_ip_address, "node_type":"Primary"})
        ip_address_dicts = ip_address_list

        setup_node_type(ip_address_dicts)
else:
    configure_standalone_node()

