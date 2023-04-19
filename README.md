# AMNIS-RabbitMQ
Tool for emulating data synchronization in mission critical networks. This repo uses RabbitMQ as the message broker. For the Kafka version, visit: https://github.com/PINetDalhousie/amnis-data-sync/tree/main


## Getting Started

Clone the repo

```https://github.com/PINetDalhousie/amnis-data-sync-rabbitmq.git```

Install RabbitMQ

```sudo apt install rabbitmq-server```

Install Pika

```python -m pip install pika --upgrade```

To Uninstall

```sudo apt-get purge rabbitmq-server erlang*```

## Usage

```python main.py```

## Architecture

The program architecture uses RabbitMQ to send messages between nodes in a Mininet network. The program uses Python's Pika library to interact with RabbitMQ, while the Mininet network is created and managed using the Mininet Python API. 