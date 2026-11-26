---
status: "proposed"
date: "2026-11-25"
decision-makers: "Dan Nixon"
consulted: "Tom Willemsen, Jack Harper, Freddie Akeroyd"
informed: "Samuel Jones, Martyn Gigg, Tom Willemsen, Jack Harper, Freddie Akeroyd"
---

# 13. Data formats for high throughput in-cluster messaging

## Context and Problem Statement

Components in a data collection pipeline in MNeuData must communicate with each other using a common data format.

Data transferred falls into two main classes:

- high throughput (sent frequently, potentially large message sizes) (e.g. detector data)
- low throughput (considered in [ADR 14](./0014 Data format for low throughput data.md))

## Decision Drivers

- Standard formats, for which well proven serialization/deserialization libraries exist for any languages of interest
- Schema required, ideally backwards and forwards compatibility
- Small wire encoding and low overhead
- Fast serialization/deserialization

## Considered Options

- [Avro](https://avro.apache.org)
- [Protobuf](https://protobuf.dev)
- [Flatbuffers](https://flatbuffers.dev)
- [CBOR](https://cbor.io)/[MessagePack](https://msgpack.org)
- [Postcard](https://postcard.jamesmunns.com)

## Decision Outcome

Chosen option: **"Flatbuffers"**, high throughput data encoded with Flatbuffers will share the ESS streaming formats where possible and ISIS extensions where required.

### Consequences

* Good, because we are able to build upon existing work and knowledge from the ESS in kind project
* Good, because Flatbuffer schema versioning is possible and allows for backwards compatibility

### Confirmation

All high throughput data transfer happens via either Flatbuffer ncoded messages.
Flatbuffer messages are annotated with a schema ID that is used to determine the message type, and is findable in a central schema registry.

## Pros and Cons of the Options

### Avro

* Good, because efficient encoding (size and time)
* Good, because schema versioning allows for backwards and forwards compatibility
* Neutral, because decoding requires a compatible schema

### Protobuf

* Good, because widely supported and has a mature ecosystem
* Bad, because native wire types limit size efficiency

### Flatbuffers (Chosen option)

* Good, because can leverage existing knowledge, tooling and schemas
* Good, because efficient encoding (size and time)
* Good, because schema versioning allows for backwards and forwards compatibility
* Good, because generally higher throughput than Avro
* Neutral, because decoding requires a compatible schema

### CBOR/MessagePack

* Good, because self describing without reliance on a schema
* Neutral, because no native schema support, but possible via JSON Schema
* Bad, because poor space efficiency compared to other formats

### Postcard

* Good, because self describing without reliance on a schema
* Good, because more space efficient than CBOR
* Bad, because no significant libraries/tooling outside of the Rust ecosystem
* Bad, because limited schema support outside of serde
