---
status: "proposed"
date: "2026-11-25"
decision-makers: "Dan Nixon"
consulted: "Tom Willemsen, Jack Harper, Freddie Akeroyd"
informed: "Samuel Jones, Martyn Gigg, Tom Willemsen, Jack Harper, Freddie Akeroyd"
---

# 13. Data formats for in cluster messaging

## Context and Problem Statement

Components in a data collection pipeline in MNeuData must communicate with each other using a common data format.

Data transferred falls into two main classes:

- high throughput (sent frequently, potentially large message sizes) (e.g. detector data)
- low throughput (sent infrequently, variable message sizes, variable/dynamic information) (e.g. software versions/configurations, hardware information)

It is possible for data that can be classified as low throughput to be treated as high throughput.

## Decision Drivers

Each class of data has different requirements and constraints.

### Common requirements

- Standard formats, for which well proven serialization/deserialization libraries exist for any languages of interest

### High throughput

- Schema required, ideally backwards and forwards compatibility
- Small wire encoding and low overhead
- Fast serialization/deserialization

### Low throughput

- Schema optional, but desirable
- Lower need for small wire size and serialization/deserialization performance
- Self describing

## Considered Options

### High throughput

- [Avro](https://avro.apache.org)
- [Protobuf](https://protobuf.dev)
- [Flatbuffers](https://flatbuffers.dev)
- [CBOR](https://cbor.io)/[MessagePack](https://msgpack.org)
- [Postcard](https://postcard.jamesmunns.com)

### Low throughput

- [Protobuf](https://protobuf.dev/)
- [Flatbuffers](https://flatbuffers.dev)
- [JSON](https://www.json.org)
- [CBOR](https://cbor.io)/[MessagePack](https://msgpack.org)

## Decision Outcome

Chosen option: **"Flatbuffers"** for high throughput and **"JSON"** for low throughput.

High throughput data encoded with Flatbuffers will share the ESS streaming formats where possible and ISIS extensions where required.

Low throughput data encoded with JSON will be identified primarily by topic and contents, optionally conforming to or being generated using a [JSON Schema](https://json-schema.org).

### Consequences

* Good, because we are able to build upon existing work and knowledge from the ESS in kind project
* Good, because there are many existing tools and libraries that support the selcted formats
* Good, because Flatbuffer schema versioning is possible and allows for backwards compatibility
* Neutral, because JSON is not as efficient as other formats for low throughput data (especially data that is naturally binary e.g. images)

### Confirmation

All data transfer happens in either a Flatbuffer or JSON encoded message.
Flatbuffer messages are annotated with a schema ID that is used to determine the message type, and is findable in a central schema registry.

## Pros and Cons of the Options

### High throughput

#### Avro

* Good, because efficient encoding (size and time)
* Good, because schema versioning allows for backwards and forwards compatibility
* Neutral, because decoding requires a compatible schema

#### Protobuf

* Good, because widely supported and has a mature ecosystem
* Bad, because native wire types limit size efficiency

#### Flatbuffers (Chosen option)

* Good, because can leverage existing knowledge, tooling and schemas
* Good, because efficient encoding (size and time)
* Good, because schema versioning allows for backwards and forwards compatibility
* Good, because generally higher throughput than Avro
* Neutral, because decoding requires a compatible schema

#### CBOR/MessagePack

* Good, because self describing without reliance on a schema
* Neutral, because no native schema support, but possible via JSON Schema
* Bad, because poor space efficiency compared to other formats

#### Postcard

* Good, because self describing without reliance on a schema
* Good, because more space efficient than CBOR
* Bad, because no significant libraries/tooling outside of the Rust ecosystem
* Bad, because limited schema support outside of serde

### Low throughput

#### Protobuf

* Good, because it is widely supported and has mature tooling
* Good, because its schema supports explicit field types and evolution
* Bad, because producers and consumers need compatible schemas

#### Flatbuffers

* Good, because it provides a defined schema and supports schema evolution
* Neutral, because efficient access to encoded data is useful but offers little benefit for infrequent, variable-size messages
* Bad, because schemas and generated code add complexity when a lightweight, self-describing format is sufficient

#### JSON (Chosen option)

* Good, because it is human-readable and can be consumed without a separately distributed schema
* Good, because schema validation is available when needed through JSON Schema, without making a schema mandatory
* Neutral, because it is human readible(/writable), making diagnostics easier
* Bad, because it is more verbose than binary formats and does not directly represent binary data efficiently

#### CBOR/MessagePack

* Good, because it is compact while retaining a flexible, schema-optional data model
* Good, because it is self-describing without reliance on a schema
* Neutral, because no native schema support, but possible via JSON Schema
* Neutral, because poor space efficiency compared to other formats
