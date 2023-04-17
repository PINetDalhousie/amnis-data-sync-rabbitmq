import os
import time
import configparser
from mininet_lib import MininetLib
from rabbit_lib import RabbitMQLib

if __name__ == '__main__':

    # Read config
    config = configparser.ConfigParser()
    config.read('config.ini')
    test_duration = config.getint('Simulation', 'test_duration')
    topology_file = config.get('Simulation', 'topology_file')

    # Clean existing logs
    os.system("sudo rm -rf ./logs")
    os.system("mkdir -p ./logs/cons ./logs/prod")    

    # Start mininet
    mininet = MininetLib()
    mininet.start("topologies/" + topology_file)
    sleep_duration = 30
    print(f"Sleeping for {sleep_duration}s to allow network to start")
    time.sleep(sleep_duration)

    # Run RabbitMQ server on each node
    print("Starting servers")
    for h in mininet.net.hosts:
        out = h.cmd('rabbitmq-server &', shell=True)
        break
    sleep_duration = 60
    print(f"Sleeping for {sleep_duration}s to allow RabbitMQ servers to start")
    time.sleep(sleep_duration)

    # Run RabbitMQ consumer on each node
    print("Starting consumers")
    consumer_script = ""
    for h in mininet.net.hosts:
        node_id = str(h.name)[1:]
        h.popen("python3 rabbit_consumer.py " + node_id + " &", shell=True)
        break

    # Run a single producer
    print("Starting producers")
    for h in mininet.net.hosts:   
        node_id = str(h.name)[1:]     
        h.popen("python3 rabbit_producer.py " + node_id + " &", shell=True)
        break

    # Let simulation run for specified duration
    print("Simulation started")
    print(f"Running for {test_duration}s")
    time.sleep(test_duration)

    # Stop and cleanup
    mininet.stop()
    print("Simulation finished")
