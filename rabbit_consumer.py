import sys
import os
import logging
import threading
import functools
from rabbit_lib import RabbitMQLib
# Example taken from https://github.com/pika/pika/blob/main/examples/basic_consumer_threaded.py


# Binding key * (star) can substitute for exactly one word.
# Binding key # (hash) can substitute for zero or more words.
BINDING_KEYS = "topic.#"

def ack_message(ch, delivery_tag):
    """Note that `ch` must be the same pika channel instance via which
    the message being ACKed was retrieved (AMQP protocol constraint).
    """
    if ch.is_open:
        ch.basic_ack(delivery_tag)
    else:
        # Channel is already closed, so we can't ACK this message;
        # log and/or do something that makes sense for your app in this case.
        pass

def do_work(ch, method_frame, properties, body):
    prod_id = properties.app_id
    message_id = properties.message_id
    topic = method_frame.routing_key.split(".")[1]
    log = "Prod ID: " + prod_id + "; Message ID: " + message_id + "; Latest: False; Topic: " + topic + "; Offset: 0; Size 1000"    
    logging.info(log)
    cb = functools.partial(ack_message, ch, method_frame.delivery_tag)
    ch.connection.add_callback_threadsafe(cb)


def on_message(ch, method_frame, properties, body, args):
    thrds = args
    t = threading.Thread(target=do_work, args=(ch, method_frame, properties, body))
    t.start()
    thrds.append(t) 


if __name__ == '__main__':
    try:
        if len(sys.argv) == 1:
            node_id = "1"
            log_dir = "./logs/test"
            prefetch_count = 0
            os.system("mkdir -p "+ log_dir +"/cons")  
        else:
            node_id = sys.argv[1]
            log_dir = sys.argv[2]
            prefetch_count = int(sys.argv[3])

        # Setup logger
        log_path = log_dir + "/cons/cons-" + node_id + ".log"
        logging.basicConfig(filename=log_path,
                            format='%(asctime)s %(levelname)s:%(message)s',
                            level=logging.INFO)
        logging.info("Started consumer-" + node_id)

        # Create queue
        lib = RabbitMQLib()
        result = lib.channel.queue_declare('topic-queue', durable=True, arguments={"x-queue-type":"quorum"})
        queue_name = result.method.queue

        # Bind the queue with our binding key
        for binding_key in BINDING_KEYS:
            lib.channel.queue_bind(
                exchange=lib.exchange, queue=queue_name, routing_key=binding_key)

        
        lib.channel.basic_qos(prefetch_count=prefetch_count)
        threads = []
        on_message_callback = functools.partial(on_message, args=(threads))
        logging.info('Waiting for messages....')
        lib.channel.basic_consume(queue=queue_name, on_message_callback=on_message_callback)        
        lib.channel.start_consuming()

        # Wait for all to complete
        for thread in threads:
            thread.join()

    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
