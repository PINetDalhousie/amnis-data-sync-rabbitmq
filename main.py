import datetime
import os
import subprocess
import time
import configparser
import logging
import socket
from mininet_lib import MininetLib
from mininet.cli import CLI
from rabbit_lib import RabbitMQLib

LOG_DIR = "./logs/" +datetime.datetime.now().strftime('%Y-%m-%d-%H-%M') 

def read_config():
    config = configparser.ConfigParser()
    config.read('config/config.ini')
    # Log all the options and values for each section
    for section in config.sections():
        logging.info('Config values:')
        for option, value in config.items(section):
            logging.info(f'{option} = {value}')
    return config

def setup_logging():
    # Create parent folder
    os.system("mkdir " + LOG_DIR)
    os.system("mkdir "+ LOG_DIR +"/cons")    
    os.system("mkdir "+ LOG_DIR +"/prod")    

    # Setup logger
    filename = LOG_DIR + "/events.log"
    logging.basicConfig(filename=filename,
                        format='%(asctime)s %(levelname)s:%(message)s',
                        level=logging.INFO)
    logging.info("Started simulation")

def get_rabbitmq_logs():
    os.system("cp -R /var/log/rabbitmq/ " + LOG_DIR +"/rabbitmq/")

if __name__ == '__main__':

    # Set logger
    setup_logging()

    # Read config
    config = read_config()
    test_duration = config.getint('Simulation', 'test_duration')
    topology_file = config.get('Simulation', 'topology_file')
    debug = config.getboolean('Simulation', 'debug')

    # Start mininet
    mininet = MininetLib()
    mininet.start("topologies/" + topology_file)
    # Run RabbitMQ server on each node
    print("Starting servers")
    port = 5672
    for h in mininet.net.hosts:
        node_id = str(h.name)[1:]   
        # Start RabbitMQ server        
        command = 'RABBITMQ_NODE_PORT=' + str(port) + ' RABBITMQ_NODENAME=rabbit@10.0.0.' + node_id + ' rabbitmq-server -detached'
        logging.info("Sending command to mininet node:\n" + command)
        out = h.cmd(command, shell=True)  
        logging.info("Output: " + out)    

        if node_id == "1":
            print("Skip cluster join for first node")
            time.sleep(20)
            logging.info("Diagnostics status")
            logging.info(h.cmd("rabbitmq-diagnostics status -n rabbit@10.0.0." + node_id , shell=True))
        else:
            time.sleep(20)
            # Join node to the cluster on rabbit@10.0.0.1 node
            print("Connecting 10.0.0."+ node_id + " to cluster")
            logging.info(h.cmd('rabbitmqctl stop_app' + ' -n rabbit@10.0.0.' + node_id, shell=True))
            logging.info(h.cmd('rabbitmqctl reset' + ' -n rabbit@10.0.0.' + node_id, shell=True))
            logging.info(h.cmd('rabbitmqctl join_cluster rabbit@10.0.0.1' + ' -n rabbit@10.0.0.' + node_id, shell=True))
            logging.info(h.cmd('rabbitmqctl start_app' + ' -n rabbit@10.0.0.' + node_id, shell=True))
        if debug:
            time.sleep(3)            
            cluster_status = h.cmd('rabbitmqctl cluster_status -n rabbit@10.0.0.' + node_id)
            logging.info(f"Cluster status of node {node_id}:\n" + cluster_status)


    sleep_duration = 60
    print(f"Sleeping for {sleep_duration}s to allow RabbitMQ servers to start")
    time.sleep(sleep_duration)

    # Run RabbitMQ consumer on each node
    print("Starting consumers")
    consumer_script = ""
    for h in mininet.net.hosts:
        node_id = str(h.name)[1:]
        h.popen("python3 rabbit_consumer.py " + node_id + " " + LOG_DIR + " &", shell=True)
        #break

    # Let consumers settle before sending messages
    time.sleep(10)

    # Run a single producer
    print("Starting producers")
    for h in mininet.net.hosts:   
        node_id = str(h.name)[1:]     
        h.popen("python3 rabbit_producer.py " + node_id+ " " + LOG_DIR + " &", shell=True)
        #break

    # Let simulation run for specified duration
    print("Simulation started")
    print(f"Running for {test_duration}s")
    time.sleep(test_duration)

    # Stop rabbitmq nodes and cleanup
    for h in mininet.net.hosts:
       node_id = str(h.name)[1:]   
       logging.info(h.cmd('rabbitmqctl stop_app' + ' -n rabbit@10.0.0.' + node_id, shell=True))
       #logging.info(h.cmd('rabbitmqctl reset' + ' -n rabbit@10.0.0.' + node_id, shell=True))
    
    # Clean up the database for future simulation runs
    os.system("sudo rm -rf /var/lib/rabbitmq/mnesia")

    mininet.stop()
    get_rabbitmq_logs()
    print("Simulation finished")
    logging.info("Simulation finished")
