import configparser
import pika
import sys


class RabbitMQLib:
    def __init__(self, node_id) -> None:
        # Read config
        config = configparser.ConfigParser()
        config.read('config/config.ini')
        queue_type = config.get('Simulation', 'queue_type')
        single_queue = config.getboolean('Simulation', 'single_queue')

        # Create connection
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()

        # Create an exchange
        self.exchange = 'topic_logs'
        self.channel.exchange_declare(exchange=self.exchange,
                                      exchange_type='topic')
    
        queue = 'topic-' + node_id
        if single_queue:
            queue = 'topic-queue'
        result = self.channel.queue_declare(queue=queue, durable=True, exclusive=False, auto_delete=False, arguments={"x-queue-type":queue_type})
        self.queue_name = result.method.queue        

    def disconnect(self):
        # Close connection to flush out buffers
        self.connection.close()
