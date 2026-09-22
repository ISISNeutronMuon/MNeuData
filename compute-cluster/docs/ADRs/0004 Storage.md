---
status: "proposed"
date: "2026-09-16"
decision-makers: "Samuel Jones"
consulted: "Simon Hodder, Martyn Gigg, Anthony Shuttle"
informed: "Simon Hodder, Martyn Gigg"
---

# 4. Storage

## Context and Problem Statement

The workloads we aim to support need several kinds of storage, not one: general persistent volumes for stateful apps, a relational database for apps that need one (e.g. Grafana), low-latency local disk for performance-sensitive workloads such as Kafka (not the overall kafka, this is for metrics ingestion), and large, long-lived object (S3) storage for the LGTM stack (Loki/Mimir/Tempo). Where should this storage come from, and how should the different tiers be provided, given that we would rather consume storage that already exists than operate our own?

## Decision Drivers

* Prefer consuming existing, resilient storage, over operating our own (self-hosting Ceph or a SAN adds significant operational burden).
* Keep data on the local network so it stays, quick, resilient and reachable during a beam cycle, favouring ISIS-operated storage over wider STFC or off-site cloud.
* Work within immutable Talos Linux (ADR 0005), whose read-only root filesystem constrains where local disk can live.
* Provide the right characteristics per workload (general persistence, strict-permission database volumes, low-latency local disk, object storage) selectable by name.

## Considered Options

Storage foundation (where durable/bulk data lives):

* Self-hosted storage backend (Ceph or a dedicated SAN)
* A centralised ISIS-operated SMB share
* Wider STFC or off-site cloud storage

Object storage (S3) provision:

* VersityGW providing an S3 API layered on the storage foundation
* A dedicated/self-hosted object store (e.g. MinIO or Ceph RGW)
* Cloud object storage (e.g. AWS S3)

## Decision Outcome

Chosen options: **"a centralised ISIS-operated SMB share"** as the foundation and **"VersityGW providing an S3 API layered on the storage foundation"** for object storage. We will not run our own storage backend; instead we consume the ISIS SMB share and layer the other tiers on top of it where it makes sense, each exposed as a Kubernetes StorageClass so workloads pick the right one by name.

* General persistent storage: the ISIS SMB share via the `smb.csi.k8s.io` driver, set as the default StorageClass.
* Databases: PostgreSQL (via the CloudNativePG operator) as the cluster's relational database, backed by a dedicated SMB StorageClass configured with the strict ownership/permissions PostgreSQL requires.
* Local disk: `local-path-provisioner` on each node's NVMe, within Talos' writable paths, for latency-sensitive workloads such as Kafka.
* Object storage: VersityGW providing an S3 API backed by the same SMB share, giving the LGTM stack S3 buckets without a separate object store.

Each workload picks a StorageClass by name, and all but one tier ultimately rest on the ISIS SMB share:

```text
 Workload         StorageClass       Backend

 General apps ──▶  smb (default)  ─┐
 PostgreSQL   ──▶  smb-postgres   ─┼──▶  ISIS SMB share
 LGTM (S3)    ──▶  VersityGW (S3) ─┘

 Kafka        ──▶  local-path     ────▶  Local NVMe (per node)

 [ ISIS-backed = centralised, durable ]     [ local-path = not central or as durable ]
```

Only the local disk storage does not rest on centrally operated storage, so durability for that tier remain outside the remit of the cluster itself (should use the ZFS mirror of the SSDs on machine).

### Consequences

* Good, because most of our data inherits the ISIS SAN's durability, so we carry far less operational burden than running Ceph or a SAN.
* Good, because storage stays on the local network and reachable throughout a beam cycle, regardless of wider site network stability and capacity.
* Bad, because ISIS SMB becomes a shared foundation: as the S3 (object) tier is also backed by that share, the availability of most storage — and the LGTM stack that depends on it — hinges on the SMB share and its network path.
* Bad, because layering S3 over SMB means object storage inherits SMB's performance characteristics and quirks rather than those of a purpose-built object store.

### Confirmation

StorageClasses are verifiable with `kubectl get storageclass` (`smb` default, `smb-postgres`, `local-path`); the CloudNativePG cluster health with `kubectl get cluster -n postgres-system`; and the S3 API by listing VersityGW buckets (`loki-s3`, `mimir-s3`, `tempo-s3`) via a path-style S3 client. Backing manifests live in `gitops/` and reconcile through ArgoCD.

## Pros and Cons of the Options

### Storage foundation

#### A centralised ISIS-operated SMB share (Chosen option)

* Good, because it reuses trusted, centrally-operated storage, so durability and maintenance are owned by ISIS Infrastructure rather than us.
* Good, because it stays on the local network, remaining resilient and reachable during a beam cycle, whilst not flooding the site network.
* Neutral, because it fixes SMB (CIFS) semantics — permission/ownership handling that some workloads (e.g. PostgreSQL) need special StorageClasses for.
* Bad, because it is a single shared foundation whose availability most tiers depend on.
* Bad, because DFS is not usable on Talos, so the SMB source is pinned to a fixed host with an explicit subdirectory.


#### Self-hosted storage backend (Ceph or a dedicated SAN)

* Good, because it would give us full control and purpose-built performance/features.
* Bad, because it adds significant operational burden to run, scale, and patch ourselves.
* Bad, because it duplicates durable storage ISIS already operates.

#### Wider STFC or off-site cloud storage

* Good, because it offloads capacity and durability elsewhere.
* Bad, because it sits off the local network, so availability during a beam cycle depends on wider site or internet connectivity.
* Bad, because cloud storage adds recurring cost and moves data off-site.

### Object storage (S3) provision

#### VersityGW providing an S3 API layered on storage foundation (Chosen option)

* Good, because it gives cloud-native tools S3 buckets without operating a separate object store, reusing the same ISIS Infrastructure-backed share.
* Neutral, because it requires S3 clients to use path-style addressing.
* Bad, because it inherits the foundation's performance characteristics and quirks.

#### A dedicated/self-hosted object store (e.g. MinIO or Ceph RGW)

* Good, because it is a purpose-built object store with native S3 performance and features.
* Bad, because it is another stateful system to run, scale, and back up ourselves.
* Bad, because its durability would not automatically inherit ISIS's durability unless further integrated.

#### Cloud object storage (e.g. AWS S3)

* Good, because it is a mature, fully-managed, highly-durable object store.
* Bad, because it moves telemetry data off-site with recurring cost and egress considerations.
* Bad, because it depends on internet connectivity, which is fragile during a beam cycle.
