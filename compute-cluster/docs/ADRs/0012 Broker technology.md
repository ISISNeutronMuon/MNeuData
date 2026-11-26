---
status: "proposed"
date: "2026-11-25"
decision-makers: "Dan Nixon"
consulted: "Martyn Gigg, Tom Willemsen, Jack Harper, Freddie Akeroyd"
informed: "Samuel Jones, Martyn Gigg, Tom Willemsen, Jack Harper, Freddie Akeroyd"
---

# 12. Broker technology

## Context and Problem Statement

Message passing using a central broker as an in-flight data store is the core backbone of MNeuData.
Planned data pipelines call for a message passing topology supporting topic based distribution, using any of SPSC, SPMC, MPMC, MPSC, or combinations thereof.

## Decision Drivers

- Resilience, broker will survive hardware/node failures
- Performance, must be capable of supporting the required data volume
- Efficiency, should make best use of compute resources
- Cost, should be licensed such that the base product is free to use

## Considered Options

- [Apache Kafka](https://kafka.apache.org/)
- [Redpanda](https://redpanda.com/)
- [Apache Pulsar](https://pulsar.apache.org/)
- [NATS with JetStream](https://nats.io/)
- [RabbitMQ](https://www.rabbitmq.com/)

## Decision Outcome

Chosen option: **Redpanda**, because it provides Kafka-compatible clients and tooling while keeping the broker deployment and operations comparatively simple.
Its resource use and throughput has already been demonstrtated to handle throughput intesive workloads.
The Community offering meets the no license cost requirement.
Its Raft-based architecture allows it to run as a standalong service, making it easier to deploy and manage.

### Consequences

* Good, because Kafka protocol compatibility lets the project use the established Kafka client ecosystem and reduces migration friction.
* Good, because the cluster does not need a separate ZooKeeper deployment, reducing operational components.
* Good, because throughput and resource efficiency are sufficient and higher than Apache Kafka.
* Neutral, because Kafka API compatibility does not guarantee complete compatibility with every Kafka feature or third-party integration.

### Confirmation

A Redpanda broker can be deployed via IaC on the target infrastructure (see [ADR 0003](./0003 Proxmos virtualization layer.md)).
Broker cluster is resilient and provides the required throughput.
Cluster is appropriately monitored using Grafana Agent (see [ADR 0007](./0007 Monitoring and alerting.md)).

## Pros and Cons of the Options

### Apache Kafka

* Good, because it is a mature, widely adopted event-streaming platform with a large ecosystem of clients, connectors, and operational knowledge.
* Good, because its Apache 2.0 license permits use without a product license fee.
* Neutral, because it has strong compatibility and a well understood operational model.
* Bad, because a self managed cluster may require more operational components and tuning than Redpanda and not reach the same performance.

### Redpanda (Chosen option)

* Good, because Kafka API compatibility provides access to Kafka clients and much of the surrounding ecosystem without requiring Kafka itself.
* Good, because its Raft-based design avoids a separate ZooKeeper service and its C++ implementation avoids a JVM runtime, simplifying the broker deployment.
* Good, because the self-hosted Community offering is available without a license fee for the intended use.
* Neutral, because Kafka compatibility is not feature-for-feature identity
* Bad, because its Community license is not the same as an OSI approved open-source license.

### Apache Pulsar

* Good, because it separates serving brokers from persistent storage and supports multi-tenancy and several messaging patterns.
* Good, because the Apache 2.0 license permits use without a product license fee.
* Bad, because the additional broker and storage layers increase operational complexity.
* Bad, because adopting it would use a different protocol and ecosystem from Kafka-compatible tooling.

### NATS

* Good, because NATS is lightweight and offers straightforward subject-based messaging; JetStream adds persistence and replay.
* Good, because it is available under the Apache 2.0 license.
* Bad, because adopting it would use a different protocol and ecosystem from Kafka-compatible tooling.

### RabbitMQ

* Good, because it is a mature broker with flexible routing, acknowledgements, and broad client support for queue-oriented messaging.
* Good, because it is available under the Mozilla Public License 2.0.
* Bad, because its queue and exchange model is a less direct fit for the durable, replayable, high-volume topic log required by these data pipelines.
* Bad, because adopting it would use a different protocol and ecosystem from Kafka-compatible tooling.
