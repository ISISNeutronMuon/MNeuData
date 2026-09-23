---
status: "proposed"
date: "2026-09-16"
decision-makers: "Samuel Jones, Simon Hodder, Martyn Gigg"
consulted: "Martyn Gigg, Simon Hodder, Daniel Nixon, Tom Willemsen, Jack Harper"
informed: "Samuel Jones, Simon Hodder, Martyn Gigg, Daniel Nixon"
---

# 2. Hardware architecture

## Context and Problem Statement

The MNeuData project needs a reliable, highly-available hardware backbone to run its computing workloads, and that backbone must stay available during beam cycles. What shape should the hardware take, how many nodes, how large, and where should they live with the aim of providing high availability and good compute-per-cost while being able to grow with demand

## Decision Drivers

* High availability: survive the loss of a physical node without losing the cluster.
* Compute-per-cost efficiency in the current market for server parts.
* Ability to scale up over time as MNeuData demand grows across beam cycles.
* Resilience and network proximity to ISIS storage and instrument hardware, reachable throughout a beam cycle.
* Low operational burden (fewer things to run, patch, and physically maintain).

## Considered Options

Control-plane topology:

* 3 dedicated control-plane nodes (odd number, quorum-forming)
* 5 or more control-plane nodes
* Managed / cloud Kubernetes control plane

Worker sizing & placement:

* Few large dedicated nodes centralised in one server room
* Many smaller nodes dispersed through the facility, next to the hardware they communicate with
* STFC Cloud compute
* 3rd Party Compute

## Decision Outcome

Chosen options: **"3 dedicated control-plane nodes (odd quorum)"** and **"few large dedicated nodes centralised in one server room"**, scaling out by adding more worker nodes as demand grows.

We will build a centralised set of large nodes acting as a compute backbone for the software layers above. The control plane uses an odd number of nodes so a [Raft/etcd quorum](https://medium.com/@prakashpsgcse/the-raft-algorithm-a-friendly-guide-to-distributed-consensus-a709abbaf045) is always formable, and a physical node can fail and maintain the state of the compute cluster.

Control plane:

* 3 nodes (minimum), quorum-forming
* 8/16 core, 32GB RAM, some local storage

Worker nodes:

* Starting with 3
* Initially 2 based on HRPD-X workers already in service (32/64 core, 128GB RAM)
* 1 larger node (bought going forward): 64/128 CPU cores, 256GB RAM (determined based on spec currently availiable in the same box from dell that the HRPD-X workers were ordered in)

Networking: TBD (load balancing, switches, etc.).

Storage: take advantage of storage operated by ISIS Infrastructure and use internal solutions where possible (e.g. SMB, CephFS) rather than self-hosting bulk storage.

### Consequences

* Good, because control-plane availability survives one node going offline.
* Good, because fewer, larger nodes pack more compute for less overall cost in the current market conditions.
* Good, because scaling is additive: more worker nodes can be appended as demand grows.
* Bad, because fewer large nodes mean coarser fault granularity — losing one box removes a larger share of capacity than losing one of many small nodes.

### Confirmation

Node inventory and roles are verifiable with `kubectl get nodes -o wide` (3 control-plane + workers). Quorum tolerance is confirmed by draining/rebooting a single control-plane node and observing the API stays available.

## Pros and Cons of the Options

### Control-plane topology

#### 3 dedicated control-plane nodes (odd quorum) (Chosen option)

* Good, because an odd number always forms a quorum and tolerates a node loss.
* Bad, because it costs three machines before any user workload runs.

#### 5 or more control-plane nodes

* Good, because it tolerates minimum two simultaneous control-plane node failures.
* Neutral, because it only adds value once availability requirements exceed "survive one loss".
* Bad, because it consumes more dedicated hardware and increases etcd write overhead for little gain at our scale, and with notably higher costs.

#### Managed / cloud Kubernetes control plane

* Good, because it removes the burden of running and patching the control plane.
* Bad, because it moves a critical component off-site, adding multiple new dependencies and cost that undermine resilience during a beam cycle.
* Bad, because it splits the cluster across on-prem workers and an off-site control plane, complicating networking and data locality.

### Worker sizing & placement

#### Few large dedicated nodes centralised in one server room (Chosen option)

* Good, because large nodes maximise compute-per-cost and centralisation keeps them on together and close to the Kafka/Redpanda cluster.
* Good, because one-box-per-node keeps fault isolation clean and provisioning reproducible.
* Bad, because fewer nodes mean each failure removes more capacity, and all nodes share one server room as a locality.

#### Many smaller nodes dispersed near the hardware they serve

* Good, because compute sits next to the instruments/hardware it talks to, reducing network distance for latency-sensitive or high-throughput control software.
* Good, because finer granularity means any single failure removes less capacity.
* Bad, because many dispersed nodes cost more per core, add management and physical-maintenance overhead, and complicate the design.

#### STFC Cloud compute

* Good, because capacity can burst elastically without acquiring new hardware, while staying on STFC-operated infrastructure and network.
* Good, because it avoids commercial cloud spend and keeps data within STFC.
* Bad, because it still sits off the local ISIS network, so availability and latency to instruments/storage depend on the wider STFC network path rather than the local ISIS network.
* Bad, because the SLA does not cover our use case within Beam Cycles.

#### 3rd Party Compute

* Good, because capacity can burst elastically without owning fixed hardware.
* Bad, because it moves workloads fully off-site with recurring commercial cost and a network dependency that is potentially fragile during a beam cycle.
* Bad, because data locality to ISIS storage and instruments is lost, and data leaves STFC entirely.
* Bad, far more expensive in the longest term than self-managing hardware.
