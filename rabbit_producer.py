from random import seed, randint, gauss
from queue import Queue
from threading import Thread
import time
import sys
import logging
import re
import random
import os

from pika import BasicProperties
from rabbit_lib import RabbitMQLib

# Binding key * (star) can substitute for exactly one word.
# Binding key # (hash) can substitute for zero or more words.
ROUTING_KEY = "topic."
messageFilePath = "message-data/xml/Cars103.xml"

def processProdMsg(q):
	while True:
		msgStatus = q.get()
		kPointerKey = list(msgStatus.keys())
		kPointerValue = list(msgStatus.values())
		try:
			logMsgStatus = kPointerValue[0].get(timeout=5000)
			logging.info('Produced message ID: %s; Value: %s', str(kPointerKey[0]), logMsgStatus)
		except Exception as e:
			logging.info('Message not produced. ID: %s; Error: %s', str(kPointerKey[0]), e)


def readXmlFileMessage(file):
	lines = file.readlines()
	readFile = ' '
	for line in lines:
		readFile += line
	logging.info("Read xml file is : %s", readFile)
	return readFile

def processXmlMessage(message):
	processedMessage = ' '
	randomNum = str(random.randint(1,999))
	# Randomize values in XML message
	processedMessage = re.sub('[0-9]+', randomNum, message)	
	encodedMessage = processedMessage.encode()	
	return encodedMessage

def processFileMessage(file):
	message = file.read().encode()
	return message

def readMessageFromFile(filePath):
	file = open(filePath, 'r')
	_, fileExt = os.path.splitext(filePath)

	if(fileExt.lower() == '.xml'):
		message = readXmlFileMessage(file)
	else:
		message = processFileMessage(file)
	return message

def generateMessage(mSizeParams):
	if mSizeParams[0] == 'fixed':
		msgSize = int(mSizeParams[1])
	elif mSizeParams[0] == 'gaussian':
		msgSize = int(gauss(float(mSizeParams[1]), float(mSizeParams[2])))	
		if msgSize < 1:
			msgSize = 1		
	payloadSize = msgSize - 4            
	if payloadSize < 0:
		payloadSize = 0
	message = [97] * payloadSize
	return message

if __name__ == '__main__':
    try:
        if len(sys.argv) == 1:
            node_id = "1"
            log_dir = "./logs/test"
            os.system("mkdir -p "+ log_dir +"/prod")  
        else:
            node_id = sys.argv[1]
            log_dir = sys.argv[2]

        # Setup logger
        log_path = log_dir + "/prod/prod-" + node_id + ".log"
        logging.basicConfig(filename=log_path,
                            format='%(asctime)s %(levelname)s:%(message)s',
                            level=logging.INFO)
        logging.info("Started producer-" + node_id)

        lib = RabbitMQLib()     

        # --message-rate 30.0 --replication $SWITCHES --message-file message-data/xml/Cars103.xml --time 150 --replica-min-bytes 200000 --replica-max-wait 5000 --ntopics $TOPICS --topic-check 0.1 --consumer-rate 0.5 --compression gzip --single-consumer --batch-size 16384 --linger 5000 
        mSizeParams = 'fixed,1000'
        msgID = 0
        nodeID = node_id
        nTopics  = 2
        mRate = 30.0
        tClass = 1


        # Read the message once and save in cache
        if(messageFilePath != 'None'):
            readMessage = readMessageFromFile(messageFilePath)	
            logging.info("Messages generated from file")
        else:
            logging.info("Messages generated")

        #Use a queue and a separate thread to log messages that were not produced properly
        q = Queue(maxsize=0)
        prodMsgThread = Thread(target=processProdMsg, args=(q,))
        prodMsgThread.start()

        while True:
            if(messageFilePath != 'None'):
                message = processXmlMessage(readMessage)			
            else:
                message = generateMessage(mSizeParams)			
            newMsgID = str(msgID).zfill(6)
            bMsgID = bytes(newMsgID, 'utf-8')
            newNodeID = nodeID.zfill(2)
            bNodeID = bytes(newNodeID, 'utf-8')
            bMsg = bNodeID + bMsgID + bytearray(message)
            topicID = randint(0, nTopics-1)
            topicName = 'topic-'+str(topicID)

            #prodStatus = producer.send(topicName, bMsg)
            routing_key = ROUTING_KEY + topicName
            properties = BasicProperties(app_id=newNodeID, message_id=newMsgID)
            lib.channel.basic_publish(exchange=lib.exchange, routing_key=routing_key, properties=properties, body=message)            
            logging.info('Topic: %s; Message ID: %s; Message: %s', topicName, newMsgID, message)

            # prodStatus = ""
            # msgInfo = {}
            # msgInfo[newMsgID] = prodStatus
            # q.put(msgInfo)

            #logging.info('Topic: %s; Message ID: %s;', topicName, str(msgID).zfill(3))        
            msgID += 1
            time.sleep(1.0/(mRate*tClass))
              
    except Exception as e:
        print(e)
