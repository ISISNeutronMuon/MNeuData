<!-- Implementation notes:
- This ADR catalogues where every external dependency physically/logically lives, so operators know what is on-cluster vs. reliant on wider ISIS/STFC infrastructure.
- Compute: bare-metal Dell PowerEdge servers in the ISIS data centre running Proxmox, hosting the Talos node VMs on the 130.246.52.0/22 LAN (nodes 130.246.55.45/68/77 control-plane, .51/.57/.67 workers).
- Persistent/bulk storage: central ISIS Windows SMB share //ISISFS-ExpData2.isis.cclrc.ac.uk/MNeudataCC$ (via smb.csi), which also backs the VersityGW S3 buckets — durability/backup is owned by ISIS storage, not this cluster.
- Secrets: centralised in HashiCorp Vault at https://secrets.isis.rl.ac.uk; the cluster authenticates with Kubernetes auth on mount isis-compute-cluster-poc and reads secret data from mount isis-compute-cluster via the Vault Secrets Operator.
- Email/alerting egress: Grafana routes outbound alert mail through the STFC SMTP relay ob-mgw.stfc.ac.uk:26 (skip_verify) from alerts@grafana.compute.isis.cclrc.ac.uk.
- External ingress: a single VIP 130.246.55.235 (Cilium LB-IPAM lan-pool) announced by ARP/L2 across the local Proxmox LAN fronts all *.compute.isis.cclrc.ac.uk services via Envoy Gateway.
- Streaming/DAQ data plane: external Kafka bootstrap livedata.isis.cclrc.ac.uk:31092 (brokers 130.246.80.191 / 130.246.81.188 / 130.246.81.166 on :9092), so egress to both :31092 and :9092 must stay open.
- Rationale: deliberately lean on existing, managed ISIS/STFC services (storage, secrets, mail, Kafka, network) instead of re-hosting them, minimising what this cluster must operate and secure itself — while noting each as an external availability dependency.
-->
# 10. Resource location

Date: 2026-09-11
## Status

Pending

## Context

The resource needs to be located somewhere within the ISIS networking with redundant network and power supplies to it.

## Decision

TBD

## Consequences

TBD