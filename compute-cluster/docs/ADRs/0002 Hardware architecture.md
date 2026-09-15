<!-- Implementation notes:
- Bare-metal Dell PowerEdge servers run Proxmox VE 9.x as the hypervisor layer; each Kubernetes node is a QEMU VM provisioned declaratively from talos/terraform/ (main.tf + modules/talos_node), so nodes are reproducible from code rather than hand-installed.
- Physical topology: one VM per dedicated physical node — every cluster node gets a whole PowerEdge box to itself, giving full fault isolation so any single physical node loss removes at most one Kubernetes node.
- Quorum-safe control plane: 3 dedicated control-plane physical nodes (odd number) give a Raft/etcd quorum that survives one node loss but collapses on two; running each on its own host ensures a single hardware failure only costs one control-plane member.
- Worker fleet: start with 3 dedicated worker physical nodes and add further worker nodes as projected MNeuData demand grows; worker sizing targets large hosts (32/64-core, 128–256 GB RAM) to maximise compute-per-cost, with control-plane hosts kept smaller and allowSchedulingOnControlPlanes=false so user workload only lands on workers.
- Local storage per host is a mirrored (RAID1) ZFS pool over two physical NVMe drives (/dev/nvme0n1 + /dev/nvme1n1), created by proxmox_node_disk_zfs; VM disk/EFI/cloud-init all sit on this 'nvme-storage-<host>' datastore for local redundancy and throughput.
- Networking: nodes attach to Proxmox bridge vmbr0 with static MAC-to-IP bindings on the 130.246.52.0/22 subnet (gateway 130.246.52.254), keeping node identity stable across rebuilds; bulk/experiment storage is delegated to central ISIS infrastructure rather than local disks.
- Because provisioning is fully Terraform-driven (physical placement is just a per-node variable), scaling out — adding worker physical nodes — is a config change plus apply rather than a redesign.
- Rationale: fewer, larger, dedicated nodes give better compute-per-cost while the odd control-plane count on isolated hardware preserves HA, and the model scales cleanly by appending worker nodes as demand grows across beam cycles.
-->
# 2. Hardware architecture

Date: 2026-09-01
## Status

First Draft

## Context

The desire to provide a reliable, highly availiable, hardware backbone for a computing cluster.

This will ensure that the MNeudata project has somewhere to perform its various computing tasks, during cycles with limited downtimes.

## Decision

A centralised series of large nodes that act as a compute backbone for various software architecture layers. The nodes will consist of some [quorum-able](https://medium.com/@prakashpsgcse/the-raft-algorithm-a-friendly-guide-to-distributed-consensus-a709abbaf045) (3, 5, 7, i.e. an odd number) number of control plane nodes, and workers based on projected demand of the cluster and the ability to scale up over time.

Control plane:
- 3 Nodes (minimum)
- Requires a [Quorum](https://medium.com/@prakashpsgcse/the-raft-algorithm-a-friendly-guide-to-distributed-consensus-a709abbaf045) to be formable
- 8/16 Core, 32GB RAM, Some local storage

Worker nodes:
- Starting with 3
- Initially 2 based on HRPD-X Workers (already in service)
  - 32/64 Core 128GB RAM
- 1 of the larger nodes (To be bought from now on)
  - 64/128 CPU Cores, 256GB RAM

Networking:
- TBD (Load balancing, switches, etc)

Storage:
- Take advantage of Storage operated by ISIS Infrastructure and utilise internal Storage solutions where possible such as SMB, CephFS, etc.

## Consequences

Control plane availability will survive one node going offline, and will operate at risk of total collapse if a second does.

Worker node sizing will be more efficient based on estimations, larger nodes can pack in more compute for less overall cost, having fewer large nodes is less redundant but will give more value for money in the current market for computer parts.