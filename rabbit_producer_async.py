# -*- coding: utf-8 -*-
# pylint: disable=C0111,C0103,R0205,W0603
import os 
import sys
import logging
import pika
import time
from pika import spec, DeliveryMode

ITERATIONS = 1000

confirmed = 0
errors = 0
published = 0

mRate = 30.0
tClass = 1


def on_open(conn):
    conn.channel(on_open_callback=on_channel_open)


def on_channel_open(channel):
    global published
    channel.exchange_declare(exchange='topic_logs', exchange_type='topic')
    channel.confirm_delivery(ack_nack_callback=on_delivery_confirmation)
    channel.queue_declare(queue='topic-queue', durable=True, exclusive=False, auto_delete=False, arguments={"x-queue-type":"quorum"})
    for _iteration in range(0, ITERATIONS):
        channel.basic_publish(
            'topic_logs', 'topic.topic-1', 'message body value',
            pika.BasicProperties(content_type='text/plain',
                                 delivery_mode=DeliveryMode.Transient))
        logging.info("Published message")
        time.sleep(1.0/(mRate*tClass))
        published += 1


def on_delivery_confirmation(frame):
    global confirmed, errors
    if isinstance(frame.method, spec.Basic.Ack):
        confirmed += 1
        logging.info('Received confirmation: %r', frame.method)
    else:
        logging.error('Received negative confirmation: %r', frame.method)
        errors += 1
    if (confirmed + errors) == ITERATIONS:
        logging.info(
            'All confirmations received, published %i, confirmed %i with %i errors',
            published, confirmed, errors)
        connection.close()



if __name__ == '__main__':    
    if len(sys.argv) == 1:
        node_id = "1"
        log_dir = "./logs/test"
        os.system("mkdir -p " + log_dir + "/prod")
    else:
        node_id = sys.argv[1]
        log_dir = sys.argv[2]

    # Setup logger
    log_path = log_dir + "/prod/prod-" + node_id + ".log"
    logging.basicConfig(filename=log_path,
                        format='%(asctime)s %(levelname)s:%(message)s',
                        level=logging.INFO)
    logging.info("Started producer-" + node_id)


    #parameters = pika.URLParameters('amqp://guest:guest@localhost:5672/%2F?connection_attempts=50')
    parameters = pika.ConnectionParameters('localhost')
    connection = pika.SelectConnection(parameters=parameters,
                                    on_open_callback=on_open)

    try:
        connection.ioloop.start()
    except KeyboardInterrupt:
        connection.close()
        connection.ioloop.start()