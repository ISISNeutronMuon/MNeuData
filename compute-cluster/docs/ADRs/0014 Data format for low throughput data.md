---
status: "proposed"
date: "2026-11-25"
decision-makers: "Dan Nixon"
consulted: "Tom Willemsen, Jack Harper, Freddie Akeroyd"
informed: "Samuel Jones, Martyn Gigg, Tom Willemsen, Jack Harper, Freddie Akeroyd"
---

# 14. Data formats for low throughput in-cluster messaging

## Context and Problem Statement

Components in a data collection pipeline in MNeuData must communicate with each other using a common data format.

Data transferred falls into two main classes:

- high throughput (considered in [ADR 13](./0013 Data format for high throughput data.md))
- low throughput (sent infrequently, variable message sizes, variable/dynamic information) (e.g. software versions/configurations, hardware information)

It is possible for data that can be classified as low throughput to be treated as high throughput.

## Decision Drivers

- Standard formats, for which well proven serialization/deserialization libraries exist for any languages of interest
- Schema optional, but desirable
- Lower need for small wire size and serialization/deserialization performance
- Self describing

## Considered Options

- [Protobuf](https://protobuf.dev/)
- [Flatbuffers](https://flatbuffers.dev)
- [JSON](https://www.json.org)
- [CBOR](https://cbor.io)/[MessagePack](https://msgpack.org)

## Decision Outcome

Chosen option: **"JSON"**, low throughput data encoded with JSON will be identified primarily by topic and contents, optionally conforming to or being generated using a [JSON Schema](https://json-schema.org).

### Consequences

* Good, because there are many existing tools and libraries that support the selcted formats
* Neutral, because JSON is not as efficient as other formats for low throughput data (especially data that is naturally binary e.g. images)

### Confirmation

All low throughput data transfer happens via JSON encoded messages.

## Pros and Cons of the Options

### Protobuf

* Good, because it is widely supported and has mature tooling
* Good, because its schema supports explicit field types and evolution
* Bad, because producers and consumers need compatible schemas

### Flatbuffers

* Good, because it provides a defined schema and supports schema evolution
* Neutral, because efficient access to encoded data is useful but offers little benefit for infrequent, variable-size messages
* Bad, because schemas and generated code add complexity when a lightweight, self-describing format is sufficient

### JSON (Chosen option)

* Good, because it is human-readable and can be consumed without a separately distributed schema
* Good, because schema validation is available when needed through JSON Schema, without making a schema mandatory
* Neutral, because it is human readible(/writable), making diagnostics easier
* Bad, because it is more verbose than binary formats and does not directly represent binary data efficiently

### CBOR/MessagePack

* Good, because it is compact while retaining a flexible, schema-optional data model
* Good, because it is self-describing without reliance on a schema
* Neutral, because no native schema support, but possible via JSON Schema
* Neutral, because poor space efficiency compared to other formats
