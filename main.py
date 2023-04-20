import os
import subprocess
import time
import configparser
import logging
import socket
from mininet_lib import MininetLib
from mininet.cli import CLI
from rabbit_lib import RabbitMQLib

def setup_logging():
    # Clean existing logs
    os.system("sudo rm -rf ./logs")
    os.system("mkdir -p ./logs/cons ./logs/prod")    

    # Setup logger    
    logging.basicConfig(filename="logs/events.log",
                        format='%(asctime)s %(levelname)s:%(message)s',
                        level=logging.INFO)
    logging.info("Started simulation")


if __name__ == '__main__':

    # Read config
    config = configparser.ConfigParser()
    config.read('config/config.ini')
    test_duration = config.getint('Simulation', 'test_duration')
    topology_file = config.get('Simulation', 'topology_file')
    debug = config.getboolean('Simulation', 'debug')

    # Set logger
    setup_logging()

    # Start mininet
    mininet = MininetLib()
    mininet.start("topologies/" + topology_file)
    # Run RabbitMQ server on each node
    print("Starting servers")
    port = 5672
    for h in mininet.net.hosts:
        node_id = str(h.name)[1:]   
        # Start RabbitMQ server    
        #logging.info(h.cmd('rabbitmqctl start_app' + ' -n rabbit@10.0.0.' + node_id, shell=True))
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
        #port = port+1        


    # sleep_duration = 60
    # print(f"Sleeping for {sleep_duration}s to allow RabbitMQ servers to start")
    # time.sleep(sleep_duration)

    # # Run RabbitMQ consumer on each node
    # print("Starting consumers")
    # consumer_script = ""
    # for h in mininet.net.hosts:
    #     node_id = str(h.name)[1:]
    #     h.popen("python3 rabbit_consumer.py " + node_id + " &", shell=True)
    #     break

    # # Run a single producer
    # print("Starting producers")
    # for h in mininet.net.hosts:   
    #     node_id = str(h.name)[1:]     
    #     h.popen("python3 rabbit_producer.py " + node_id + " &", shell=True)
    #     break

    # # Let simulation run for specified duration
    # print("Simulation started")
    # print(f"Running for {test_duration}s")
    # time.sleep(test_duration)

    # Stop and cleanup

    #for h in mininet.net.hosts:
    #    node_id = str(h.name)[1:]   
    #    logging.info(h.cmd('rabbitmqctl stop_app' + ' -n rabbit@10.0.0.' + node_id, shell=True))

    mininet.stop()
    print("Simulation finished")
