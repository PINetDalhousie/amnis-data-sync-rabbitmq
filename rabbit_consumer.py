import sys
import os
import logging
from rabbit_lib import RabbitMQLib


# Binding key * (star) can substitute for exactly one word.
# Binding key # (hash) can substitute for zero or more words.
BINDING_KEYS = "test.#"


def callback(ch, method, properties, body):
    print(" [x] %r:%r" % (method.routing_key, body))
    log = method.routing_key + " " + body.decode("utf-8")
    logging.info("Message: " + log)


if __name__ == '__main__':
    try:
        node_id = sys.argv[1]

        # Setup logger
        log_path = "logs/cons/cons-" + node_id + ".log"
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
