---
status: "proposed"
date: "2026-09-16"
decision-makers: "Samuel Jones"
consulted: "Simon Hodder, Martyn Gigg"
informed: "Simon Hodder, Martyn Gigg"
---

# 5. Software infrastructure

## Context and Problem Statement

On top of the virtualised hardware (ADR 0003) we need a base software platform to support our estimated workloads. That platform spans the operating system, cluster provisioning, networking, and ingress. What should each of these layers be so the base is reproducible, low-drift, secure, and Kubernetes-native rather than built from legacy components?

## Decision Drivers

* Reproducibility and low drift: the OS and cluster should be defined in code and rebuildable deterministically, not configured by hand.
* A small, secure surface: minimal attack surface and no ad-hoc manual tampering with running nodes.
* A modern, Kubernetes-native networking and ingress stack rather than legacy components.
* Skills and tooling fit: the stack should integrate cleanly with the GitOps and LGTM layers built above it.

## Considered Options

Operating system:

* Talos Linux (immutable, API-managed)
* A traditional general-purpose distro (e.g. Ubuntu)

Provisioning:

* Terraform + Ansible (declarative, code-defined)
* Manual / imperative host configuration

Networking (CNI):

* Cilium in eBPF mode (kube-proxy replacement)
* Calico
* Flannel

Ingress:

* Envoy Gateway (Gateway API)
* An Ingress-NGINX-style controller (Ingress API)
* Cilium's native Gateway API

## Decision Outcome

Chosen options: **"Talos Linux"**, **"Terraform + Ansible"**, **"Cilium in eBPF mode"**, and **"Envoy Gateway"**. Together these give a base platform that is defined in code, immutable, eBPF-networked, and fronted by a single modern Gateway API implementation.

* Operating system: Talos Linux — an immutable OS with no SSH or shell, so nodes cannot drift or be tampered with.
* Provisioning: Terraform builds the VMs and bootstraps the cluster; Ansible installs the base platform on top. The whole stack is defined in code and rebuildable deterministically.
* Networking (CNI): Cilium runs as the CNI in eBPF mode, replacing `kube-proxy`, and Cilium LB-IPAM with L2 announcements hands out and advertises external service IPs. Cilium was chosen over Calico and Flannel primarily for its built-in observability (Hubble) and its feature-completeness as a single component (network policy, eBPF dataplane, and LB-IPAM/L2 without extra add-ons).
* Ingress: Envoy Gateway acts as the single Gateway API controller for the cluster. Cilium's own Gateway API is left disabled, to avoid two controllers competing over the same CRDs and because of a lack of HTTPRoute management tooling used in the LGTM stack.

### Consequences

* Good, because the platform becomes reproducible and low-drift: nodes are defined in code and rebuilt rather than fixed in place, giving a small, consistent, hard-to-tamper-with base for everything above it.
* Good, because eBPF networking and a single modern Gateway API implementation avoid legacy components and hardware load balancers.
* Bad, because no SSH or shell means no ad-hoc login to debug or patch a node.

### Confirmation

Nodes and their config are defined in `talos/terraform/` and `talos/ansible/`; a rebuild reproduces the platform deterministically. Runtime state is verifiable with `kubectl get nodes -o wide`, Cilium status/Hubble for the CNI, and `kubectl get gatewayclass,gateway -A` (GatewayClass `envoy-gateway`) for ingress.

## Pros and Cons of the Options

### Operating system

#### Talos Linux (Chosen option)

* Good, because it is immutable and API-managed with no SSH or shell, so nodes cannot drift or be tampered with and the attack surface is small.
* Good, because it is purpose-built for Kubernetes and pairs cleanly with declarative provisioning.
* Bad, because it removes traditional break-glass shell access and needs Talos-specific operational knowledge.

#### A traditional general-purpose distro (e.g. Ubuntu)

* Good, because it is familiar, flexible, and widely supported.
* Bad, because it is mutable and invites manual SSH changes, so nodes drift over time.
* Bad, because it carries a larger attack surface and needs more regular maintenance.

### Provisioning

#### Terraform + Ansible (Chosen option)

* Good, because the whole stack is defined in code and rebuildable deterministically.
* Good, because Terraform (infra + cluster bootstrap) and Ansible (base platform) split responsibilities cleanly.
* Neutral, because it introduces two tools to learn and keep in step.
* Bad, because adds multiple toolchains that need maintenance

#### Manual / imperative host configuration

* Good, because it is quick for a one-off and needs no tooling.
* Bad, because it drifts from documentation, leaves no audit trail, and cannot be reproduced deterministically.

### Networking (CNI)

#### Cilium in eBPF mode (Chosen option)

* Good, because its eBPF dataplane replaces `kube-proxy` for faster, more capable networking.
* Good, because it is the most feature-complete option as a single component: network policy, LB-IPAM with L2 announcements (external service IPs without hardware LBs), encryption, and more, without stitching together add-ons.
* Good, because it ships built-in observability via Hubble (relay + UI), giving network-flow visibility out of the box.
* Neutral, because it requires eBPF/Cilium-specific operational knowledge.

#### Calico

* Good, because it is mature, widely deployed, and has strong network-policy support (and an optional eBPF dataplane).
* Bad, because it has no built-in observability comparable to Hubble, so network-flow visibility needs extra tooling.
* Bad, because matching Cilium's all-in-one feature set (integrated LB-IPAM/L2, rich flow observability) requires additional components rather than coming out of the box.

#### Flannel

* Good, because it is simple, minimal overlay networking that is easy to stand up.
* Bad, because it is feature-poor: no built-in network policy, no LB-IPAM/L2, and no flow observability.
* Bad, because reaching our required feature set would mean bolting on several extra components that Cilium provides natively.

### Ingress

#### Envoy Gateway (Chosen option)

* Good, because it implements the Gateway API, the more capable and now industry-standard direction.
* Good, because it is used in other projects within ISIS and SC so configuration can be used.
* Good, because you can do per HTTPRoute security policies unlike other GatewayAPIs.
* Neutral, because Cilium's native Gateway API must be explicitly disabled to prevent two controllers competing over the same CRDs.

#### An Ingress-NGINX-style controller (Ingress API)

* Good, because it is mature and widely deployed.
* Bad, because it uses the older Ingress API rather than the Gateway API direction we want to standardise on.

#### Cilium's native Gateway API

* Good, because it would consolidate CNI and ingress in one component.
* Bad, because it lacks the HTTPRoute management tooling used in the LGTM stack.
* Bad, because running it alongside Envoy Gateway would make two controllers fight over the same CRDs.
* Bad, because you can't do per HTTPRoute security policies.