import configparser
import logging
import subprocess
import time
from random import seed, randint
from datetime import datetime
from mininet.net import Mininet
from mininet.cli import CLI
from mininet.node import RemoteController
from mininet.link import TCLink
from mininet.topo import Topo
from mininet.node import OVSKernelSwitch, Host
from mininet.log import setLogLevel
import sys
import subprocess
import networkx as nx


class CustomTopo(Topo):
	def __init__(self, inputTopoFile):
		Topo.__init__(self)
		#Read topo information
		try:
			inputTopo = nx.read_graphml(inputTopoFile)
		except Exception as e:
			print("ERROR: Could not read topo properly.")
			print(str(e))
			sys.exit(1)

		for node in inputTopo.nodes:
			if node[0] == 'h':
				host = self.addHost(node, cls=Host)
			elif node[0] == 's':
				switch = self.addSwitch(node,dpid=node[1],cls=OVSKernelSwitch, failMode='standalone')
			else:
				print("ERROR: Wrong node identifier.")
				sys.exit(1)

		for source, target, data in inputTopo.edges(data=True):
			linkBandwidth = 1000
			if 'bandwidth' in data:
				linkBandwidth = int(data['bandwidth'])
			linkDelay = '1ms'
			if 'latency' in data:
				linkDelay = str(data['latency'])+'ms'
			self.addLink(source, target, data['sport'], data['dport'], bw=linkBandwidth, delay=linkDelay)


class MininetLib:
    def __init__(self, log_dir) -> None:
        self.net = None
        # Setup logger
        filename = log_dir + "/events.log"
        logging.basicConfig(filename=filename,
                            format='%(asctime)s %(levelname)s:%(message)s',
                            level=logging.INFO)
        setLogLevel('info')

        # Read config
        config = configparser.ConfigParser()
        config.read('config/config.ini')
        self.disconnectRandom = config.getint('Disconnect', 'disconnect_random')
        self.disconnectHosts = config.get('Disconnect', 'disconnect_hosts')
        self.disconnectDuration = config.getint('Disconnect', 'disconnect_duration')

    def start(self, topo_file, sleep_duration=30):
        print("Starting mininet")
        #Clean up mininet state
        subprocess.Popen("sudo mn -c", shell=True)
        time.sleep(2)

        #Instantiate network        
        emulatedTopo = CustomTopo(topo_file)	

        # Create network
        self.net = Mininet(topo = None,
                controller=RemoteController,
                link = TCLink,
                autoSetMacs = True,
                autoStaticArp = True,
                build=False)

        # Add topo to network
        self.net.topo = emulatedTopo
        self.net.build()

        #Start network
        print("Starting Network")
        self.net.start()
        for switch in self.net.switches:
            self.net.get(switch.name).start([])

        self.setNetworkDelay('1ms')
        print("Testing network connectivity")
        self.net.pingAll()
        print("Finished network connectivity test")
        #CLI(self.net) # Uncomment and run "h1 xterm &" for debugging
        print(f"Sleeping for {sleep_duration}s to allow network to start")
        time.sleep(sleep_duration)

    def stop(self):
        print("Stopping Network")
        self.net.stop()
        #Clean up mininet state
        subprocess.Popen("sudo mn -c", shell=True)

    def setNetworkDelay(self, newDelay=None):
        net = self.net
        nodes = net.switches + net.hosts	 
        print(f"Checking network nodes to set new delay")
        #logging.info('Setting nework delay at %s', str(datetime.now()))
        for node in nodes:
            for intf in node.intfList(): # loop on interfaces of node
                if intf.link: # get link that connects to interface (if any)
                    # Check if the link is switch to switch
                    if intf.link.intf1.name[0] == 's' and intf.link.intf2.name[0] == 's':
                        if newDelay is None:
                            # Use the values from graph.ml
                            intf1Delay = intf.link.intf1.params['delay']
                            intf.link.intf1.config(delay=intf1Delay)
                            intf2Delay = intf.link.intf2.params['delay']
                            intf.link.intf2.config(delay=intf2Delay)
                        else:						
                            # Use the passed in param				
                            intf.link.intf1.config(delay=newDelay)
                            intf.link.intf2.config(delay=newDelay)	

    def printLinksBetween(self, n1, n2):	
        net = self.net
        linksBetween = net.linksBetween(n1, n2)
        print(f"Links between {n1.name} {n2.name} {linksBetween}")	
        if len(linksBetween) > 0:
            for link in linksBetween:			
                print(link.intf1)
                print(link.intf2)

    def disconnect_hosts(self, netHosts, hosts):        
        for h in hosts:
            netHost = netHosts[h.name]		
            s = self.net.getNodeByName(netHost[1][0])		
            self.disconnectHost(h, s)

    def disconnectHost(self, h, s):	        
        print(f"***********Setting link down from {h.name} <-> {s.name} at {str(datetime.now())}")						
        logging.info('Disconnected %s <-> %s at %s', h.name, s.name,  str(datetime.now()))
        self.net.configLinkStatus(s.name, h.name, "down")			

    def reconnectHosts(self, netHosts, hosts):        
        for h in hosts:
            netHost = netHosts[h.name]		
            s = self.net.getNodeByName(netHost[1][0])
            self.reconnectHost(h, s)

    def reconnectHost(self, h, s):        
        print(f"***********Setting link up from {h.name} <-> {s.name} at {str(datetime.now())}")
        logging.info('Connected %s <-> %s at %s', h.name, s.name,  str(datetime.now()))
        self.net.configLinkStatus(s.name, h.name, "up")	

    def processDisconnect(self):        
        hostsToDisconnect = []
        netHosts = {k: v for k, v in self.net.topo.ports.items() if 'h' in k}
        if self.disconnectRandom != 0:
            seed()
            randomIndex = randint(0, len(netHosts) - 1)
            netHostsList = list(netHosts.items())
            while self.disconnectRandom != len(hostsToDisconnect):
                h = self.net.getNodeByName(netHostsList[randomIndex][0])
                if not hostsToDisconnect.__contains__(h):
                    hostsToDisconnect.append(h)
                    print(f"Host {h.name} to be disconnected for {self.disconnectDuration}s\r")
                randomIndex = randint(0, len(netHosts) - 1)
        elif self.disconnectHosts is not None:
            hostNames = self.disconnectHosts.split(',')
            for hostName in hostNames:
                h = self.net.getNodeByName(hostName)
                hostsToDisconnect.append(h)        

        return netHosts, hostsToDisconnect