<!-- Implementation notes:
- No self-hosted Ceph/SAN: general persistent storage is the central ISIS Windows SMB share //ISISFS-ExpData2.isis.cclrc.ac.uk/MNeudataCC$ mounted via smb.csi.k8s.io, so bulk capacity/backup is delegated to existing ISIS infrastructure rather than operated by us.
- Default StorageClass 'smb' (is-default-class=true, reclaimPolicy=Delete) mounts dir_mode=0775 / file_mode=0774 / gid=1000; consequence: non-root pods MUST set securityContext.supplementalGroups: [1000] to write, and the CSI provisioner creates a per-PV sub-directory under the share using smb-creds from kube-system.
- Dedicated 'smb-postgres' class (reclaimPolicy=Retain) mounts uid=26/gid=26, dir_mode=0700/file_mode=0600 to satisfy PostgreSQL initdb's strict ownership/permission checks; used exclusively by the CloudNativePG cluster (postgres-cluster, 3 instances, PG 17.2, wal_level=logical).
- High-throughput local storage uses rancher local-path-provisioner (class 'local-path', reclaimPolicy=Retain, WaitForFirstConsumer, not default) rooted at /var/lib/kubelet/local-path-provisioner because Talos' immutable squashfs root only allows writable HostPath under /var/lib/kubelet; used for latency-sensitive workloads like the Kafka KRaft broker.
- Long-term S3 object storage is on-prem VersityGW (v1.2.0, posix backend at /mnt/data) fronting a 4000Gi ReadWriteMany SMB-backed PV/PVC (s3-backend, statically provisioned, Retain), exposed at s3.compute... and s3-admin.compute...; buckets back Loki/Mimir/Tempo blocks.
- VersityGW quirks captured in config: DFS is not usable on Talos so the SMB source is pinned to a fixed host with an explicit subDir, and S3 clients must use path-style addressing + TLS skip-verify against the self-signed cert (region us-east-1).
- Rationale: reuse trusted, backed-up central storage for durability, keep only performance-critical data on local NVMe, and layer an S3 API on top of SMB so cloud-native tools get object storage without a separate object store.
-->
# 4. Storage

Date: 2026-09-10
## Status

First Draft

## Context

The workloads we are aiming to support need several kinds of storage, not one:

- general persistent volumes for stateful apps
- a relational database for apps that need one (e.g. Grafana)
- low-latency local disk for performance-sensitive workloads such as Kafka (used for LGTM stack as part of the monitoring)
- large, long-lived object (S3) storage for the LGTM stack (Loki/Mimir/Tempo)

We would rather consume storage that already exists than operate our own: self-hosting Ceph or a dedicated SAN adds significant operational burden, and cloud object storage sits off-site. We favour ISIS-operated storage over wider STFC infrastructure because it stays on the local network, keeping it resilient and reachable during a beam cycle. The cluster also runs on immutable Talos Linux, whose read-only root filesystem constrains where local disk can live.


## Decision

We will not run our own storage backend. Instead, we will consume a centralised ISIS SMB share as the foundation and layer the other tiers on top of it, where this makes sense to do so, each exposed as a Kubernetes StorageClass so workloads pick the right one by name.

- General persistent storage: the ISIS SMB share via the `smb.csi.k8s.io` driver, set as the default StorageClass
- Databases: we will run PostgreSQL (via the CloudNativePG operator) as the cluster's relational database, backed by a dedicated SMB StorageClass configured with the strict ownership/permissions PostgreSQL requires
- Local disk: `local-path-provisioner` on each node's NVMe, within Talos' writable paths, for latency-sensitive workloads such as Kafka
- Object storage: VersityGW providing an S3 API backed by the same SMB share, giving the LGTM stack S3 buckets without a separate object store

Each workload picks a StorageClass by name, and all but one tier ultimately rest on the ISIS SMB share:

```text
 Workload         StorageClass       Backend

 General apps ──▶  smb            ─┐
 PostgreSQL   ──▶  smb-postgres   ─┼──▶  ISIS SMB share
 LGTM (S3)    ──▶  VersityGW (S3) ─┘

 Kafka        ──▶  local-path     ────▶  Local NVMe (per node)

 [ ISIS-backed = centralised, durable ]     [ local-path = not backed up ]
```

Only the local disk storage does not rest on centrally operated storage, so durability and backup remain outside the remit of the computer itself.

## Consequences

Most of our data inherits ISIS's durability and backup, so we carry far less operational burden than running Ceph or a SAN, and storage stays on the local network and reachable throughout a beam cycle, regardless of the site-wide network stability.

The trade-offs are:

- ISIS SMB becomes a shared foundation: because the S3 (object) tier is also backed by that share, the availability of most storage — and the LGTM stack that depends on it — hinges on the SMB share and its network path.
- Local disk is the one tier ISIS does not back up. Data on it (e.g. Kafka) is node-local and at risk if a node or its NVMe fails, only data that we are willing to lose can be stored here.
- Some storage options may need their own new StorageClasses bases on permission chagnes and all of them will need maintaining. 
- Layering S3 over SMB means object storage inherits SMB's performance characteristics and quirks rather than those of a purpose-built object store.
