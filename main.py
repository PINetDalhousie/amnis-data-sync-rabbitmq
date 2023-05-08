import datetime
import os
import sys
import subprocess
import time
import configparser
import logging
import socket
from random import seed, randint, choice
from mininet_lib import MininetLib
from mininet.cli import CLI
from rabbit_lib import RabbitMQLib

LOG_DIR = "./logs/" +datetime.datetime.now().strftime('%Y-%m-%d-%H-%M') 

# Reset rabbitmq by killing old processes and removing old database data
def cleanRabbitState():
    print("Resetting RabbitMQ State...")
    # Kill Producer Processes
    os.system("pkill -9 -f rabbit_producer.py")
    os.system("pkill -9 -f rabbit_producer_async.py")    
    # Kill Consumer Processes
    os.system("pkill -9 -f rabbit_consumer.py")
    os.system("pkill -9 -f rabbit_consumer_async.py")
    # Kill remaining rabbitmq processes
    os.system("pkill -9 -f rabbitmq")
    # Kill remaining erlang processes
    os.system("pkill -9 -f erlang")
    # Kill bandwidth monitor process
    os.system("pkill -9 -f bandwidth-monitor.py")

    # Clean up the database for future simulation runs
    os.system("rm -rf /var/lib/rabbitmq/mnesia")

def read_config():
    config = configparser.ConfigParser()
    config.read('config/config.ini')
    # Log all the options and values for each section
    for section in config.sections():
        logging.info('Config values:')
        for option, value in config.items(section):
            logging.info(f'{option} = {value}')
    return config

def validate_config(config):
    section='Simulation'    
    if not config.has_option(section, 'debug'):
        print("ERROR: Config requries debug to be specified as a boolean.")
        sys.exit(1)
    if not config.has_option(section, 'test_duration') or config.getint(section, 'test_duration') <= 0:
        print("ERROR: Config requires test_duration to be specified as an integer greater than zero.")
        sys.exit(1)
    if not config.has_option(section, 'topology_file'):
        print("ERROR: Config requires topology_file to be specified.")
        sys.exit(1)
    queue_list = ['classic', 'quorum', 'stream']
    if not config.has_option(section, 'queue_type') or (not config.get(section, 'queue_type') in queue_list):
        print("ERROR: Config requires queue_type to be specified as one of the following:")
        print(*queue_list, sep = ", ") 
        sys.exit(1)
    if not config.has_option(section, 'prefetch_count') or config.getint(section, 'prefetch_count') <= 0:
        if config.get(section, 'queue_type') == 'stream':
            print("ERROR: Config requires prefetch_count to be specified as an integer greater than zero for streams.")
            sys.exit(1)
        elif config.getint(section, 'prefetch_count') < 0:
            print("ERROR: Config requires prefetch_count to be specified as an integer of zero or greater.")
            sys.exit(1)

def setup_logging():
    # Create parent folder
    os.system("mkdir -p " + LOG_DIR)
    os.system("mkdir "+ LOG_DIR +"/cons")    
    os.system("mkdir "+ LOG_DIR +"/prod")
    os.system("mkdir " + LOG_DIR + "/bandwidth")

    # Setup logger
    filename = LOG_DIR + "/events.log"
    logging.basicConfig(filename=filename,
                        format='%(asctime)s %(levelname)s:%(message)s',
                        level=logging.INFO)
    logging.info("Started simulation")

def get_rabbitmq_logs():
    os.system("cp -R /var/log/rabbitmq/ " + LOG_DIR +"/rabbitmq/")
    
def run_bandwidth_plot(switches):
    switch_ports = ""
    for i in range(switches):
        switch_ports += "S" + str(i+1) + "-P1,"
    switch_ports = switch_ports[:-1]
    os.system("python3 plot-scripts/bandwidthPlotScript.py --number-of-switches " + str(switches) +
              " --port-type access-port --message-size fixed,10 --message-rate 30.0 --ntopics 2 --replication " + str(switches) +
              " --log-dir " + LOG_DIR + " --switch-ports " + switch_ports)
    # --switch-ports S1-P1,S2-P1,S3-P1,S4-P1,S5-P1,S6-P1,S7-P1,S8-P1,S9-P1,S10-P1

def trace_wireshark(hosts, title):
    for h in hosts:
        hostName = h.name
        filename = "/tmp/" + hostName + "-eth1" + "-" + title + ".pcap"
        output = h.cmd("sudo tcpdump -i " + hostName +
                       "-eth1 -w " + filename + " &", shell=True)
        print(output)

def startProducers(hosts, logDir, tClassString, mSizeString, mRate, nTopics, messageFilePath, asyncClients):
    tClasses = tClassString.split(',')
    #print("Traffic classes: " + str(tClasses))
    nodeClassification = {}
    classID = 1
    for tClass in tClasses:
        nodeClassification[classID] = []
        classID += 1
    #Distribute nodes among classes
    for node in hosts:
        nodeClass = randint(1,len(tClasses))
        nodeClassification[nodeClass].append(node)
    i=0

    for nodeList in nodeClassification.values():
        for node in nodeList:
            node_id = str(node.name)[1:] 
            if asyncClients:   
                h.popen("python3 rabbit_producer_async.py " + node_id+ " " + logDir + " &", shell=True)
            else:
                h.popen("python3 rabbit_producer.py " + node_id+ " " + logDir + " " + tClasses[i] + " " + mSizeString + " " + str(mRate) + " " + str(nTopics) + " " + str(messageFilePath) + " &", shell=True)
        i += 1

if __name__ == '__main__':

    # Set logger
    setup_logging()

    # Read config
    config = read_config()
    validate_config(config)
    test_duration = config.getint('Simulation', 'test_duration')
    topology_file = config.get('Simulation', 'topology_file')
    debug = config.getboolean('Simulation', 'debug')
    prefetch_count = config.getint('Simulation', 'prefetch_count')
    queue_type = config.get('Simulation', 'queue_type')
    wireshark_capture = config.getboolean('Simulation', 'wireshark_capture')
    async_clients = config.getboolean('Simulation', 'async_clients')
    traffic_classes = config.get('Simulation', 'traffic_classes')
    message_size = config.get('Simulation', 'message_size')
    message_rate = config.getfloat('Simulation', 'message_rate')
    num_topics  = config.getint('Simulation', 'num_topics')
    message_file = config.get('Simulation', 'message_file')
    disconnect_random = config.getint('Disconnect', 'disconnect_random')
    disconnect_hosts = config.get('Disconnect', 'disconnect_hosts')
    disconnect_duration = config.getint('Disconnect', 'disconnect_duration')
    is_disconnect = disconnect_random != 0 or disconnect_hosts != "None"

    # Cleanup rabbitmq state
    cleanRabbitState()

    # Start mininet
    mininet = MininetLib(LOG_DIR)
    mininet.start("topologies/" + topology_file)

    # Start bandwidth monitoring
    print("Starting bandwidth monitor")
    subprocess.Popen("python3 bandwidth-monitor.py " +
                     str(len(mininet.net.hosts))+" " + LOG_DIR + " &", shell=True)
    
    # Start Wireshark
    if wireshark_capture:
        trace_wireshark(mininet.net.hosts, "start")

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


    sleep_duration = 30
    print(f"Sleeping for {sleep_duration}s to allow RabbitMQ servers to start")
    time.sleep(sleep_duration)

    # Run RabbitMQ consumer on each node
    print("Starting consumers")    
    for h in mininet.net.hosts:
        node_id = str(h.name)[1:]
        if async_clients:
            h.popen("python3 rabbit_consumer_async.py " + node_id + " " + LOG_DIR + " &", shell=True)
        else:
            h.popen("python3 rabbit_consumer.py " + node_id + " " + LOG_DIR +  " " + str(prefetch_count) + " &", shell=True)        
        

    # Let consumers settle before sending messages
    sleep_duration = 30
    print(f"Sleeping for {sleep_duration}s to allow RabbitMQ consumers to start")
    time.sleep(sleep_duration)

    # Set the network delay back to to .graphml values before spawning producers so we get accurate latency
    mininet.setNetworkDelay()
    time.sleep(10)

    # Run producers
    print("Starting producers")
    startProducers(mininet.net.hosts, LOG_DIR, traffic_classes, message_size, message_rate, num_topics, message_file, async_clients)
    #for h in mininet.net.hosts:   
    #    node_id = str(h.name)[1:]  
    #    if async_clients:   
    #        h.popen("python3 rabbit_producer_async.py " + node_id+ " " + LOG_DIR + " &", shell=True)
    #    else:
    #        h.popen("python3 rabbit_producer.py " + node_id+ " " + LOG_DIR + " &", shell=True)        

    # Set up disconnect
    if is_disconnect:
        isDisconnected = False        
        netHosts, hostsToDisconnect = mininet.processDisconnect()

    # Let simulation run for specified duration    
    print(f"Simulation started. Running for {test_duration}s")
    logging.info('Simulation started at ' + str(datetime.datetime.now()))      
    timer = 0
    while timer < test_duration:
        time.sleep(10)
        percentComplete = int((timer/test_duration)*100)
        print("Processing workload: "+str(percentComplete)+"%\r")
        if is_disconnect and percentComplete >= 10:
            if not isDisconnected:			
                mininet.disconnect_hosts(netHosts, hostsToDisconnect)				
                isDisconnected = True
            elif isDisconnected and disconnect_duration <= 0: 			
                mininet.reconnectHosts(netHosts, hostsToDisconnect)
                if wireshark_capture:
                    trace_wireshark(hostsToDisconnect, "reconnect")
                isDisconnected = False
                is_disconnect = False
            if isDisconnected:
                disconnect_duration -= 10
        timer += 10

    print("Simulation complete\r")
    logging.info('Simulation complete at ' + str(datetime.datetime.now()))      

    # Reset rabbitmq state
    cleanRabbitState()

    mininet.stop()
    get_rabbitmq_logs()
    print("Network stopped")
    logging.info('Network stopped at ' + str(datetime.datetime.now()))

    print("Generating visualizations")
    switches = len(mininet.net.hosts)
    os.system("python3 plot-scripts/modifiedLatencyPlotScript.py --number-of-switches " + str(switches) + " --log-dir " + LOG_DIR + "/")
    run_bandwidth_plot(switches)
    if async_clients:
        os.system("python3 plot-scripts/messageHeatMap.py --log-dir " + LOG_DIR + "/" + " --prod " + str(switches) + " --cons " + str(switches) + " --topic " + str(num_topics))
        os.system("sudo mv msg-delivery/ " + LOG_DIR + "/" )   
        os.system("sudo mv failed-messages/ " + LOG_DIR + "/")   
        os.system("sudo mv broker-confirmation/ " + LOG_DIR + "/")   

    if wireshark_capture:
        print("Moving wireshark pcaps")
        os.system("chmod ugo+rwx /tmp/*pcap")
        os.system("mkdir " + LOG_DIR + "/pcaps/")
        os.system("mv /tmp/*pcap " + LOG_DIR + "/pcaps/")
