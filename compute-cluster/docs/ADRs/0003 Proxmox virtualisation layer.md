<!-- Implementation notes:
- Proxmox VE 9.x on bare-metal Dell PowerEdge is the virtualisation layer hosting all Talos Kubernetes node VMs; it is driven declaratively by the bpg/proxmox Terraform provider (v0.111.0) in talos/terraform/ against the API endpoint https://130.246.53.66:8006 as root@pam (insecure=true for the internal self-signed cert).
- Per-host VM storage is a mirrored (RAID1) ZFS pool built by proxmox_node_disk_zfs over two physical NVMe drives (/dev/nvme0n1 + /dev/nvme1n1), exposed as datastore 'nvme-storage-<host>' with add_storage and cleanup enabled; VM root disk, EFI disk, and cloud-init all live there.
- VMs (modules/talos_node) use machine type pc-q35-10.1 pinned deliberately (newer types trigger a VirtIO regression that breaks inter-node networking), BIOS=ovmf (UEFI), CPU type=host (passthrough), virtio-scsi controller (scsi0, raw, ssd=on, discard=on), and an EFI disk.
- QEMU guest agent is enabled (with fstrim) for clean IP reporting and graceful lifecycle; boot order is scsi0 then ide3 CD-ROM so the node boots from disk after Talos install.
- The Talos image is a factory.talos.dev schematic ISO (v1.13.8, nocloud-amd64) baked with siderolabs/qemu-guest-agent, iscsi-tools, and util-linux-tools extensions; the ISO is uploaded once to each Proxmox host's 'local' datastore and the matching installer image is derived from the same URL for consistency.
- Networking is software-defined via Proxmox bridge vmbr0 with static per-node MAC-to-IP bindings (130.246.52.0/22, gateway 130.246.52.254), giving stable node identity and predictable rebuilds.
- Rationale: Proxmox gives cheap, reproducible, fully Terraform-managed VM lifecycle on existing ISIS Dell hardware, with ZFS mirroring for local resilience and pinned/immutable image inputs so the whole cluster can be torn down and re-created deterministically.
-->
# 3. Proxmox virtualisation layer

Date: 2026-09-10
## Status

First Draft

## Context

The hardware backbone (ADR 0002) is a set of bare-metal servers that need to host the cluster's Kubernetes (Talos) nodes. Running Kubernetes directly on bare metal ties each node's lifecycle to a physical box, making provisioning, rebuilds, and recovery slow and manual.

We want a virtualisation layer that:

- makes node lifecycle reproducible and automatable from code
- lets the cluster be re-created deterministically for testing and disaster recovery
- pools local disks and makes them resilient beneath the nodes
- keeps node images and machine configuration immutable and version-pinned

It must run on the existing servers and future hardware allowing expansion, carry no licensing cost, integrate with Terraform, and support the immutable Talos Linux OS.

## Decision

We will use Proxmox as the virtualisation layer on the bare-metal servers, and run every Kubernetes (Talos) node as a QEMU/KVM virtual machine on top of it, being assigned most of the resources of each VM. Proxmox is installed manually per host (typically via iDRAC) and joined to the cluster; that is the only manual step.

From there everything is declarative:

- Hosts and VMs are provisioned with Terraform (the `bpg/proxmox` provider), so node creation, sizing, and teardown are driven entirely from code.
- Each host's local NVMe disks form a mirrored (RAID1) ZFS pool backing the VM disks, for local redundancy and throughput.
- VMs attach to a Proxmox software bridge with static MAC-to-IP bindings, reserved to match how ISIS DHCP allocates IPs, so node identity is stable across rebuilds.

We will not adopt a commercially-licensed hypervisor (e.g. VMware) or run Kubernetes directly on bare metal.

The result is a clear set of layers, with Proxmox sitting between the physical hardware and the Kubernetes nodes:

```text
┌────────────── Kubernetes (Talos nodes) ───────────────┐
│  the node VMs join together to form the cluster       │
├────────────────── VM  (QEMU / KVM) ───────────────────┤
│  Talos Linux · UEFI/OVMF · host CPU · virtio-scsi     │
├─────────────────── Proxmox VE 9.x ────────────────────┤
│  hypervisor · ZFS datastore · vmbr0 bridge            │
├────────────── Bare-metal Dell PowerEdge ──────────────┤
│  CPU · RAM · 2× NVMe (mirrored ZFS pool)              │
└───────────────────────────────────────────────────────┘
```

## Consequences

Kubernetes Nodes (not Hardware, or Proxmox VE nodes) become disposable: recovering from a failure or reconfiguring a node is a code change and re-apply rather than a hands-on-hardware operation, which lowers the cost of rebuilds and makes the cluster deterministically reproducible for testing and disaster recovery.

The cluster gains local resilience beneath Kubernetes without depending solely on central storage, and node identity stays predictable across rebuilds, so higher layers (networking, ingress, GitOps) can assume stable addressing.

In exchange for these benefits, Proxmox becomes a dependency that we need to support: another layer to patch and troubleshoot, some overhead over bare metal, and a few load-bearing hypervisor settings to maintain.

