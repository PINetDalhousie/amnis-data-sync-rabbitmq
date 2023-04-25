import subprocess
import time
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
    def __init__(self) -> None:
        self.net = None
        setLogLevel('info')

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
    
    def install_rabbit_mq(self):
        print("Installing RabbitMQ")
        # Install RabbitMQ on each node in the network
        for host in self.net.hosts:
            host.cmd('apt-get update')
            host.cmd('apt-get -y install rabbitmq-server')

        # Test RabbitMQ installation by starting the RabbitMQ service on each node
        for host in self.net.hosts:
            host.cmd('service rabbitmq-server start')

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

