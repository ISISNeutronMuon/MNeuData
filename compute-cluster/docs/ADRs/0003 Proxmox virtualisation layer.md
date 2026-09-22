---
status: "proposed"
date: "2026-09-16"
decision-makers: "Samuel Jones"
consulted: "Simon Hodder, Martyn Gigg"
informed: "Simon Hodder, Martyn Gigg"
---

# 3. Proxmox virtualisation layer

## Context and Problem Statement

The hardware backbone (ADR 0002) is a set of bare-metal servers that need to host the cluster's Kubernetes (Talos) nodes. Running Kubernetes directly on bare metal ties each node's lifecycle to a physical box, making provisioning, rebuilds, and recovery slow and manual. What should sit between the physical hardware and the Kubernetes nodes so that node lifecycle is reproducible, resilient, and driven from code?

## Decision Drivers

* Reproducible, automatable node lifecycle defined in code rather than configured by hand.
* Deterministic re-creation of the cluster for testing and disaster recovery.
* Pooling of local disks so storage is resilient beneath the nodes.
* Immutable, version-pinned node images and machine configuration.
* Runs on the existing servers and future hardware, allowing expansion.
* No licensing cost, integrates with Terraform, and supports the immutable Talos Linux OS.

## Considered Options

* Proxmox VE with each Talos node as a QEMU/KVM virtual machine
* A commercially-licensed hypervisor (e.g. VMware)
* Kubernetes directly on bare metal (no virtualisation layer)

## Decision Outcome

Chosen option: **"Proxmox VE with each Talos node as a QEMU/KVM virtual machine"**, because it gives cheap, reproducible, fully Terraform-managed VM lifecycle on the existing (and future) hardware with no licensing cost, while supporting immutable Talos and ZFS-mirrored local storage.

Proxmox is installed manually per host (typically via iDRAC) and joined to the cluster; that is the only manual step. From there everything is declarative:

* Hosts and VMs are provisioned with Terraform (using the `bpg/proxmox` provider), so node creation, sizing, and teardown are driven entirely from code.
* Each host's local NVMe disks form a mirrored (RAID1) ZFS pool backing the VM disks, for local redundancy and throughput.
* VMs attach to a Proxmox software bridge with static MAC-to-IP bindings, reserved to match how ISIS DHCP allocates IPs, so node network identity is stable across rebuilds.

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

### Consequences

* Good, because Kubernetes nodes become disposable: recovering from a failure or reconfiguring a node is a code change and re-apply rather than a hands-on-hardware operation, lowering the cost of rebuilds and making the cluster deterministically reproducible for testing and disaster recovery.
* Good, because the cluster gains local resilience beneath Kubernetes (ZFS mirror) without depending solely on central storage, where needed.
* Good, because node identity stays predictable across rebuilds, so higher layers (networking, ingress, GitOps) can assume stable addressing.
* Bad, because Proxmox becomes another layer to patch, troubleshoot, and support, with some overhead over bare metal and a few load-bearing hypervisor settings to maintain.

### Confirmation

The VM fleet is defined declaratively in `talos/terraform/` (the `bpg/proxmox` provider); a `terraform plan` shows no drift when the cluster matches code, and the whole cluster can be torn down and re-created with `terraform destroy` and `terraform apply`. Running nodes are verifiable via the Proxmox API and `kubectl get nodes -o wide`.

## Pros and Cons of the Options

### Proxmox VE with each Talos node as a QEMU/KVM virtual machine (Chosen option)

* Good, because it is free (no licensing cost) and runs on the existing hardware.
* Good, because the `bpg/proxmox` Terraform provider makes the whole VM lifecycle declarative and reproducible.
* Good, because ZFS mirroring gives local disk redundancy beneath the nodes.
* Neutral, because one manual step remains (installing Proxmox per host via iDRAC).
* Bad, because it adds a hypervisor layer to operate, patch, and troubleshoot, with some overhead over bare metal.

### A commercially-licensed hypervisor (e.g. VMware)

* Good, because it is a mature, widely-supported enterprise platform.
* Bad, because it carries recurring licensing cost for no more capability that we need here.
* Bad, because it is a heavier, more proprietary layer than Proxmox for the same outcome.

### Kubernetes directly on bare metal (no virtualisation layer)

* Good, because it removes the hypervisor layer and it's overhead entirely.
* Bad, because it ties each node's lifecycle to a physical box, making provisioning, rebuilds, and recovery slow and manual.
* Bad, because there is no built-in local-disk pooling/redundancy beneath the nodes and no cheap and easy way to deterministically re-create nodes from code, did investigate iDRAC Terraform provider, and it was not sufficiently capable.
