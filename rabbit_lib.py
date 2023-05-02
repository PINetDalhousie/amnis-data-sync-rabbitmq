import configparser
import pika
import sys


class RabbitMQLib:
    def __init__(self, node_id) -> None:
        # Read config
        config = configparser.ConfigParser()
        config.read('config/config.ini')
        publisher_confirms = config.getboolean('Simulation', 'publisher_confirms')
        queue_type = config.get('Simulation', 'queue_type')

        # Create connection
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()

        # Create an exchange
        self.exchange = 'topic_logs'
        self.channel.exchange_declare(exchange=self.exchange,
                                      exchange_type='topic')
        
        result = self.channel.queue_declare('topic-' + node_id, durable=True, exclusive=False, auto_delete=False, arguments={"x-queue-type":queue_type})
        self.queue_name = result.method.queue
        
        # Enable publisher confirms
        if publisher_confirms:
            self.channel.confirm_delivery()

    def disconnect(self):
        # Close connection to flush out buffers
        self.connection.close()
