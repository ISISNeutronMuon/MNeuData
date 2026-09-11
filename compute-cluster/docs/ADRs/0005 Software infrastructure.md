<!-- Implementation notes:
- OS is immutable Talos Linux v1.13.8 (API-managed, no SSH/shell): Terraform builds the VMs and applies machine config (CNI=none, kube-proxy disabled, kubePrism enabled, searchDomain isis.cclrc.ac.uk), then Ansible (playbooks/deploy.yml) does post-provisioning Helm/kubectl installs. Clear split: Terraform = infra + cluster bootstrap, Ansible = base platform.
- CNI is Cilium 1.19.6 (installed by the ansible cilium role into kube-system) with kubeProxyReplacement=true (eBPF, no kube-proxy), ipam.mode=kubernetes, and cgroup autoMount disabled with hostRoot=/sys/fs/cgroup to suit Talos; k8sServiceHost=localhost:7445 targets Talos kubePrism.
- LoadBalancer IPs come from Cilium LB-IPAM: CiliumLoadBalancerIPPool 'lan-pool' owns the single static VIP 130.246.55.235/32, advertised on the LAN by CiliumL2AnnouncementPolicy over node interfaces (^ens[0-9]+) via ARP — no external LB hardware needed.
- Ingress is Envoy Gateway 1.9.1 as the SOLE Gateway API controller (GatewayClass 'envoy-gateway'); Cilium's native Gateway API is disabled (gatewayAPI.enabled=false) to avoid two controllers fighting over the same CRDs.
- The EnvoyProxy param object pins the Envoy Service to the VIP (annotation io.cilium/lb-ipam-ips: 130.246.55.235) and sets externalTrafficPolicy: Cluster — mandatory, because with L2 announcements 'Local' makes an ARP-leader node without a local Envoy pod drop traffic; Envoy runs 2 replicas.
- A single cluster-wide Gateway (envoy-gateway-system) has listeners on 80 (HTTP, redirected to HTTPS) and 443 (HTTPS, TLS Terminate using secret compute-tls), accepting HTTPRoutes from all namespaces; per-service hostnames like hubble.compute... route to backends, and tenant paths get SHA-hashed basic-auth via SecurityPolicy (bcrypt unsupported by Envoy Gateway).
- Observability of the network layer: Hubble (relay + UI) is enabled in Cilium and published through the Gateway.
- Rationale: an immutable, declaratively-provisioned OS plus eBPF networking and a single modern Gateway API implementation gives a reproducible, low-drift, hardware-LB-free platform that other GitOps apps build on.
-->
# 5. Software infrastructure

Date: 2026-08-06
## Status

First Draft

## Context

On top of the virtualised hardware (ADR 0003) we need a base software platform for supporting our estimated workloads, the platform includes operating system, cluster provisioning, networking, and ingress. 

What we want from that platform:

- reproducibility and low drift: the OS and cluster should be defined in code and rebuildable deterministically, not configured by hand
- a small, secure surface: minimal attack surface and no ad-hoc manual tampering with running nodes
- a modern, Kubernetes-native networking and ingress stack rather than legacy components.

## Decision

We will standardise the base platform on an immutable OS, declarative provisioning, and a Kubernetes-native networking and ingress stack:

- Operating system: Talos Linux.
  - An immutable OS with no SSH or shell, so nodes cannot drift or be tampered with.
  - Rejected: a traditional general-purpose distro, such as Ubuntu, which is mutable, invites manual SSH changes, carries a larger attack surface, and needs more regular maintenance.
- Provisioning: Terraform + Ansible.
  - Terraform builds the VMs and bootstraps the cluster.
  - Ansible installs the base platform on top.
  - Result: the whole stack is defined in code and rebuildable deterministically.
- Networking (CNI): Cilium.
  - Runs as the CNI in eBPF mode, replacing `kube-proxy`.
  - Feature rich, such as built-in capable monitoring, 
  - Cilium LB-IPAM and L2 announcements hand out and advertise external service IPs.
  - Rejected: classic `kube-proxy` (iptables) networking as the slower, less capable legacy path.
- Ingress: Envoy Gateway.
  - Acts as the single Gateway API controller for the cluster.
  - Rejected: an Ingress-NGINX-style controller, in favour of the Gateway API, the more capable and now industry standard direction.
  - Cilium's own Gateway API is left disabled, due to a lack of HTTPRoute management tooling used in the LGTM stack.

## Consequences

The platform becomes reproducible and low-drift: nodes are defined in code and rebuilt rather than fixed in place, giving a small, consistent, hard-to-tamper-with base for everything above it.

The trade-offs:

- No SSH or shell means no ad-hoc login to debug or patch a node; every change goes through the code-and-rebuild flow, which is safer but less familiar and removes traditional break-glass access.
- The stack is opinionated and modern (Talos, eBPF Cilium, Gateway API), so operating it needs those specific skills rather than general Linux/`kube-proxy`/Ingress-NGINX experience.
