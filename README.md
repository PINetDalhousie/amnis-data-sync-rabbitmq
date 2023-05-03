# AMNIS-RabbitMQ
Tool for emulating data synchronization in mission critical networks. This repo uses RabbitMQ as the message broker. For the Kafka version, visit: https://github.com/PINetDalhousie/amnis-data-sync/tree/main

## Requirements

In order to run a stream queue type, rabbitmq-server version 3.9.13 or greater is needed. This requires Ubuntu jammy (22.04LTS).

Classic and quorum queue types can be run with rabbitmq-server version 3.8.2 on Ubuntu focal (20.04LTS).

## Getting Started

Clone the repo

```https://github.com/PINetDalhousie/amnis-data-sync-rabbitmq.git```

Install RabbitMQ

```sudo apt install -y rabbitmq-server```

Install Pika

```python -m pip install pika --upgrade```

Copy the Config

```sudo cp config/*.conf /etc/rabbitmq/```

## Usage

```sudo python main.py```

## Uninstall

```sudo apt-get purge -y rabbitmq-server erlang*```

## Architecture

The program architecture uses RabbitMQ to send messages between nodes in a Mininet network. The program uses Python's Pika library to interact with RabbitMQ, while the Mininet network is created and managed using the Mininet Python API. 