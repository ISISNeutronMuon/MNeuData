<!-- Implementation notes:
- This ADR covers stateful/quorum workloads that cannot simply be killed and rescheduled without data loss or outage; the pattern is redundancy + durable backing storage + graceful shutdown, since Talos nodes are immutable and get rebooted/replaced.
- PostgreSQL uses CloudNativePG with a 3-instance Cluster (postgres-cluster, PG 17.2) doing streaming replication for HA; it sits on the dedicated smb-postgres StorageClass (uid/gid 26, 0700/0600) required by initdb, and wal_level=logical enables logical replication/publications.
- Kafka (Mimir's ingest buffer) runs in KRaft mode with persistence on the local-path StorageClass (local NVMe under /var/lib/kubelet) rather than SMB, because the broker needs low-latency durable local disk; consequence: broker state is node-pinned, so it depends on the specific node's NVMe surviving.
- Loki is run in Distributed mode with replication_factor 3, which forces ingester autoscaling minReplicas=2 (never 1) — a single ingester breaks quorum and returns 500s on ingest; ingesters hold recent un-flushed chunks so they must not all restart at once.
- Mimir/Loki stateful components (ingester, store-gateway, compactor) hold data on persistent volumes and mount SMB with supplementalGroups [1000]; long-term blocks are offloaded to S3 (VersityGW) so a pod restart only risks the small in-memory/WAL window, not historical data.
- Graceful lifecycle: these workloads rely on PodDisruptionBudgets and extended terminationGracePeriodSeconds so pods flush WAL/chunks to storage before termination, and rolling updates/node drains respect quorum instead of taking out multiple replicas simultaneously.
- Rationale: keep at least N+1 replicas for quorum-based services, put durable state on the right storage class (SMB for shared durability, local-path for throughput, S3 for long term), and drain gracefully so routine Talos reboots never cause data loss or ingestion outages.
-->
# 9. Software that can't restart

Date: 2026-08-06
## Status

First Draft

## Context

Kubernetes normally assumes a workload can be freely rescheduled onto any node's pods are cattle, and moving one is expected. Some of our applications break that assumption: they cannot migrate between nodes without disrupting the service or the clients that depend on them, for example, a motor controller or robot controller.

The cases we need to handle:

- Applications whose network identity is tied to a specific node. These run with `hostNetwork: true` and are reached on the node's own IP rather than a cluster Service, for example, EPICS IOCs, whose clients target a fixed node IP via unicast address lists. If such a pod is rescheduled to a different node, its address changes and clients lose it.
- Applications that hold node-local state, or are otherwise sensitive to being restarted or moved, and need to come back on the same node.

We want these workloads to stay put on a known node, be managed through the same Kubernetes/GitOps model as everything else where possible, and still have a way out for the rare cases that do not fit Kubernetes cleanly.

## Decision

We will keep these workloads pinned to a known node rather than letting them float, using Kubernetes primitives first and only dropping to Proxmox when Kubernetes is a poor fit.

- Node pinning (main method): pin the workload to a named node with a node selector / affinity so it always runs on the same node.
  - Its node IP stays constant, so `hostNetwork` apps stay reachable and clients' unicast address lists keep working.
  - Each EPICS IOC, for example, is bound to a specific node this way.
  - Stable storage for state and caching: where a pinned workload holds local state or a cache, back it with a stable PersistentVolume so that data survives pod restarts and comes back with the pod on its node, rather than being lost or re-created each time.
- Proxmox fallback (not the default): for the rare workload that does not fit Kubernetes cleanly, run it directly on Proxmox as a dedicated VM or container.
  - We do not expect to use this often, but the virtualisation layer (ADR 0003) gives us the flexibility when it is the right tool.

## Consequences

These workloads get the stability they need: they stay on a known node, keep a constant address, and retain their state across restarts, so node-bound and restart-sensitive software runs reliably alongside everything else in the same GitOps model.

The trade-offs:

- Pinning removes automatic failover: if the chosen node is down or drained, the workload is down until that node returns or is manually pinned to a different node, rather than being rescheduled elsewhere.
- Node placement becomes something we own and must track — which app is pinned where — and it constrains maintenance, since draining a node deliberately takes its pinned workloads offline.
- A stable PersistentVolume ties recovery to that storage being available and correct; the data is only as safe as the volume behind it.
- The Proxmox fallback sits outside Kubernetes and GitOps, so anything run that way is managed and observed separately and does not benefit from the cluster's normal deployment and reconciliation.
