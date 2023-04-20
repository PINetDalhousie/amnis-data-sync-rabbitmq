import sys
import logging
from rabbit_lib import RabbitMQLib

# Binding key * (star) can substitute for exactly one word.
# Binding key # (hash) can substitute for zero or more words.
ROUTING_KEY = "test.t"

if __name__ == '__main__':
    try:
        node_id = sys.argv[1]
        log_dir = sys.argv[2]

        # Setup logger
        log_path = log_dir + "/prod/prod-" + node_id + ".log"
        logging.basicConfig(filename=log_path,
                            format='%(asctime)s %(levelname)s:%(message)s',
                            level=logging.INFO)
        logging.info("Started producer-" + node_id)

        lib = RabbitMQLib()                

        # Send message
        message = 'Hello from producer-' + node_id
        lib.channel.basic_publish(
                    exchange=lib.exchange, routing_key=ROUTING_KEY, body=message)
        logging.info(f"Sent '{message}'")

        # Disconnect
        lib.disconnect()
    except Exception as e:
        print('Exception: ' + e)