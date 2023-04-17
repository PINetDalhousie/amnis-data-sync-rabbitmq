import pika
import sys


class RabbitMQLib:
    def __init__(self) -> None:
        # Create connection
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()

        # Create an exchange
        self.exchange = 'topic_logs'
        self.channel.exchange_declare(exchange=self.exchange,
                                      exchange_type='topic')

    def disconnect(self):
        # Close connection to flush out buffers
        self.connection.close()
