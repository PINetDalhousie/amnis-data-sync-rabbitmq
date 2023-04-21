import sys
import os
import logging
from rabbit_lib import RabbitMQLib


# Binding key * (star) can substitute for exactly one word.
# Binding key # (hash) can substitute for zero or more words.
BINDING_KEYS = "topic.#"


def callback(ch, method, properties, body):
    '''
    Example Kafka Log:
    INFO:Prod ID: 02; Message ID: 000055; Latest: False; Topic: topic-0; Offset: 27; Size: 923
    '''
    #message = body.decode("utf-8")
    prod_id = properties.app_id
    message_id = properties.message_id
    topic = method.routing_key.split(".")[1]
    log = "Prod ID: " + prod_id + "; Message ID: " + message_id + "; Latest: False; Topic: " + topic + "; Offset: 0; Size 1000"    
    logging.info(log)    


if __name__ == '__main__':
    try:
        if len(sys.argv) == 1:
            node_id = "1"
            log_dir = "./logs/test"
            os.system("mkdir -p "+ log_dir +"/cons")  
        else:
            node_id = sys.argv[1]
            log_dir = sys.argv[2]

        # Setup logger
        log_path = log_dir + "/cons/cons-" + node_id + ".log"
        logging.basicConfig(filename=log_path,
                            format='%(asctime)s %(levelname)s:%(message)s',
                            level=logging.INFO)
        logging.info("Started consumer-" + node_id)

        # Create queue
        lib = RabbitMQLib()
        result = lib.channel.queue_declare('', exclusive=True)
        queue_name = result.method.queue

        # Bind the queue with our binding key
        for binding_key in BINDING_KEYS:
            lib.channel.queue_bind(
                exchange=lib.exchange, queue=queue_name, routing_key=binding_key)

        # Register callback and start consuming
        logging.info('Waiting for messages....')
        lib.channel.basic_consume(queue=queue_name,
                                  on_message_callback=callback, auto_ack=True)
        lib.channel.start_consuming()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
