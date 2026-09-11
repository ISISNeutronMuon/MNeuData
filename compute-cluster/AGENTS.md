# Agent Documentation: MNeuData Compute Cluster

This document provides a technical operational guide for automated agents and engineers working on the `compute-cluster` sub-directory in this repository.

---

## 1. Core Infrastructure & Topology

- **Environment**: Bare-metal Dell PowerEdge servers running Proxmox VE 9.x.
- **Operating System**: [Talos Linux](https://www.talos.dev/) v1.13.8 (immutable squashfs root, kernel 6.18, containerd 2.2).
- **Kubernetes**: v1.36.0 (3 Control-Plane nodes + 3 Worker nodes).
  - Control-Plane: `130.246.55.77`, `130.246.55.45`, `130.246.55.68`
  - Workers (16-core, 48GB RAM, 1TB NVMe on `/var`): `130.246.55.57`, `130.246.55.51`, `130.246.55.67`
- **Provisioning Flow**:
  - `talos/terraform/`: Creates Proxmox VMs, manages ZFS pools, and bootstraps Talos machines.
  - `talos/ansible/`: Installs post-provisioning base manifests (Cilium CNI, ArgoCD GitOps).
  - `gitops/`: Pure GitOps application definitions managed by ArgoCD.

---

## 2. GitOps & Operational Workflow Rules

1. **Human-in-the-Loop GitOps**:
   - **Agents must never commit or push directly to remote git repositories.**
   - All cluster mutations must follow GitOps:
     1. Agent edits/creates files locally in `compute-cluster/gitops/`.
     2. Human reviews, commits, and pushes to `compute_cluster` branch.
     3. Human syncs the target application in ArgoCD.
2. **Cluster Access**:
   - Kubeconfig: `talos/ansible/kubeconfig.yaml`
   - Talosconfig: `talos/ansible/talosconfig.yaml`
3. **App-of-Apps Architecture**:
   - Root application: `app-of-apps` (`gitops/apps/app-of-apps/deployment.yml`) automatically recurses and deploys every application under `gitops/apps/<app-name>/`.
4. **Multi-Source Helm Pattern**:
   - Applications declare multiple sources:
     - `sources[0]`: Upstream Helm chart (or OCI registry).
     - `sources[1]`: Git repo with `ref: values` providing `$values/compute-cluster/gitops/apps/<app>/values.yml`.
     - `sources[2]`: Git repo with `path: compute-cluster/gitops/components/<app>` providing custom Kubernetes manifests.

---

## 3. Ingress & Networking Architecture

- **CNI**: [Cilium](https://cilium.io/) 1.19.6 running with eBPF kube-proxy replacement.
  - **LB-IPAM**: `CiliumLoadBalancerIPPool` (`lan-pool`) allocates the dedicated static IP **`130.246.55.235`**.
  - **L2 Announcements**: Advertises `130.246.55.235` over node physical interfaces via ARP on the Proxmox LAN.
  - **CRITICAL CONSTRAINT**: Services using L2 announcements **must** set `externalTrafficPolicy: Cluster`. Setting `Local` causes ARP leader nodes without local pods to refuse/drop traffic.
- **Gateway API Controller**: [Envoy Gateway](https://gateway.envoyproxy.io/) 1.9.1 (`gatewayClassName: envoy-gateway`).
  - Cilium's native Gateway API is disabled (`gatewayAPI.enabled: false`) to prevent controller conflicts.
  - An `EnvoyProxy` parameter (`gitops/components/envoy-gateway/envoy-proxy.yml`) configures the Envoy LoadBalancer Service with `io.cilium/lb-ipam-ips: "130.246.55.235"` and `externalTrafficPolicy: Cluster`.
  - Single cluster-wide `Gateway` in `envoy-gateway-system` with listeners for port 80 (HTTP) and port 443 (HTTPS with TLS termination referencing secret `compute-tls`).
- **TLS Certificate**:
  - Managed by `cert-manager` (`gitops/components/cert-manager/certificate.yml`) in namespace `envoy-gateway-system`.
  - Issues explicit SANs for all 10 cluster domains (no wildcards):
    `compute.isis.cclrc.ac.uk`, `argo.*`, `hubble.*`, `s3.*`, `s3-admin.*`, `versity.*`, `loki.*`, `mimir.*`, `tempo.*`, `grafana.*`.
- **Per-Tenant Path Routing & Security**:
  - User traffic paths: `https://<service>.compute.isis.cclrc.ac.uk/<tenant>` (e.g. `/mneudata-compute`).
  - **`HTTPRoute`**: Matches `PathPrefix: /<tenant>`, uses `URLRewrite` (`ReplacePrefixMatch: /`) to strip the prefix, and `RequestHeaderModifier` to inject `X-Scope-OrgID: <tenant>`.
  - **`SecurityPolicy`**: Attaches directly to the tenant's `HTTPRoute`, enforcing HTTP Basic Authentication at the Envoy Gateway edge.
  - **CRITICAL CONSTRAINT**: Envoy Gateway's `SecurityPolicy.basicAuth` requires **SHA** hashed entries in `.htpasswd` (generated via `htpasswd -cbs .htpasswd <user> <pass>`). Bcrypt is **not** supported.

---

## 4. Storage Architecture

| Class / Storage | Provisioner | Mount Options / Path | Intended Workloads |
|---|---|---|---|
| **`smb`** (default) | `smb.csi.k8s.io` | `dir_mode=0775, file_mode=0774, gid=1000` on Windows CIFS | General persistent storage (Mimir TSDB blocks, VersityGW backend). **Non-root pods MUST declare `supplementalGroups: [1000]`.** |
| **`smb-postgres`** | `smb.csi.k8s.io` | `dir_mode=0700, file_mode=0600, uid=26, gid=26` | Dedicated exclusively for CloudNativePG PostgreSQL 17 (`initdb` strict permission requirement). |
| **`local-path`** | `rancher/local-path-provisioner` | `/var/lib/kubelet/local-path-provisioner` (`0777`) on NVMe | High-throughput local storage (Kafka KRaft broker). |
| **S3 Object Storage** | `versitygw` | `s3.compute.isis.cclrc.ac.uk:443` | Long-term TSDB block storage for Loki, Mimir, and Tempo. |

### Talos Linux Storage Constraints
- The root filesystem (`/`) is an immutable squashfs. HostPath volumes outside `/var/lib/kubelet` fail with `read-only file system` because kubelet runs in an isolated container mount namespace.
- Local NVMe volumes must use paths under `/var/lib/kubelet/...`.
- The `local-path-storage` namespace must have label `pod-security.kubernetes.io/enforce: privileged` for helper pods to execute directory setup/teardown.

### VersityGW S3 Compatibility
- All S3 clients (Loki, Mimir, Tempo) must configure:
  - **Path-style addressing**: `s3ForcePathStyle: true` (Loki/Tempo) or `bucket_lookup_type: path` (Mimir).
  - **TLS verification**: `tls_insecure_skip_verify: true` (due to self-signed TLS cert).
  - **Region**: `us-east-1` (default VersityGW region).

---

## 5. Secrets Management (HashiCorp Vault & VSO)

- **Operator**: HashiCorp `vault-secrets-operator` v0.9.1.
- **Vault Endpoint**: `https://secrets.isis.rl.ac.uk` (mount `isis-compute-cluster`).
- **Kubernetes Auth**: Role `cluster` on auth mount `isis-compute-cluster-poc`.
- **Per-Namespace RBAC Pattern**: Every namespace requiring Vault secrets must have a `vault-auth-<namespace>.yml` manifest declaring:
  - `VaultConnection` (`default`)
  - `ServiceAccount` (`vault-op`)
  - `VaultAuth` (`static-auth`)
  - Role, RoleBinding, and ClusterRoleBinding delegating `system:auth-delegator`.

### Vault Path Conventions
- **Tenant Basic Auth**: `<service>/user-basic-auth/<tenant>`
  - Key: `.htpasswd` (SHA-hashed entry for Envoy Gateway `SecurityPolicy`).
- **Telemetry Client Auth**: `monitoring/<service>-basic-auth`
  - Keys: `username`, `password` (plaintext credentials used by Alloy).
- **Service / Host Infrastructure Secrets**: `<service>/host/<secret-name>`
  - Examples: `grafana/host/credentials` (`username`, `password`), `grafana/host/database` (`username`, `password`), `loki/host/loki-auth` (`SELF_MONITORING_PASSWORD`).
- **Shared Storage Secrets**: `versity-s3-root` (`S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`), `smb-creds`.

---

## 6. LGTM Observability Stack

### Loki (`gitops/apps/loki/`)
- **Chart**: `grafana-community/loki` v18.8.0 (Distributed mode).
- **Object Storage**: VersityGW bucket `loki-s3`.
- **Quorum Requirement**: `replication_factor: 3` mandates **`ingester.autoscaling.minReplicas: 2`**. Setting 1 replica causes 500 errors on all log ingestion.
- **Distributor**: Must have `extraArgs: [-config.expand-env=true]` and S3 `extraEnv` to prevent AWS EC2 metadata lookup timeouts.

### Mimir (`gitops/apps/mimir/`)
- **Chart**: `grafana/mimir-distributed` v6.2.0.
- **Kafka Ingest Buffer**: Runs Apache Kafka in KRaft mode with persistence on StorageClass **`local-path`**.
- **Storage Permissions**: Compactor, ingester, and store-gateway mount SMB volumes and **must** declare `securityContext.supplementalGroups: [1000]`.
- **S3 Configuration**: Must use `bucket_lookup_type: path` under `mimir.structuredConfig.common.storage.s3`.

### Tempo (`gitops/apps/tempo/`)
- **Chart**: `grafana-community/tempo-distributed` v2.26.2 (Tempo 2.10.7).
  *(Note: Do not upgrade to 3.x unless deploying an external Kafka cluster for trace ingestion).*
- **Object Storage**: VersityGW bucket `tempo-s3`.
- **MetricsGenerator**: Remote-writes derived metrics to `http://mimir-gateway.mimir.svc.cluster.local:80/prometheus` with `X-Scope-OrgID: mneudata-compute`.

### Grafana (`gitops/apps/grafana/`)
- **Chart**: `grafana-community/grafana` v13.1.0.
- **High Availability**: 3 replicas, stateless (`persistence.enabled: false`).
- **Database Backend**: CloudNativePG PostgreSQL 17 cluster (`postgres-cluster-rw.postgres-system.svc.cluster.local:5432`) running on `smb-postgres`.
  - Database password dynamically injected via `envValueFrom.GF_DATABASE_PASSWORD` referencing secret `grafana-db-creds`.
- **Sidecars**: Watches and auto-reloads ConfigMaps with label `grafana_datasource: "1"`, `grafana_dashboard: "1"`, etc.
- **Provisioned Data Sources**:
  - `Mimir-Mneudata-compute`: Default Prometheus metrics source with exemplar links to Tempo.
  - `Loki-Mneudata-compute`: LogQL source with derived-field trace ID links to Tempo.
  - `Tempo-Mneudata-compute`: OTLP trace source with trace-to-logs query links to Loki and service-map links to Mimir.

### Observability / Alloy (`gitops/apps/observability/`)
- **Chart**: `grafana/k8s-monitoring` v4.5.0.
- **Collectors**:
  - `alloy-metrics` (StatefulSet, clustered): Scrapes cAdvisor, kubelet, and Prometheus ServiceMonitors/PodMonitors.
  - `alloy-logs` (DaemonSet): Tails container logs on node host filesystem and streams to Loki.
  - `alloy-singleton` (Deployment): Captures cluster Kubernetes events.
  - `alloy-receiver` (Deployment): Ingests in-cluster OTLP telemetry on ports 4317 (gRPC) and 4318 (HTTP).
- **Targeting**: Pushes to `https://<service>.compute.isis.cclrc.ac.uk/mneudata-compute` with `tls.insecureSkipVerify: true` using credentials from `monitoring/*-basic-auth`.

### S3 Metrics Exporter (`gitops/apps/s3-exporter/`)
- **Components**: `gitops/components/s3-exporter/` deployed into namespace `monitoring-system`.
- **Image**: `ghcr.io/isisneutronmuon/s3-exporter@sha256:f76b04f0f1a5430a01bb16ca89c6039828a13196498a19fa65658dfc354297ad`.
- **Target Endpoint**: In-cluster HTTP `http://versitygw.versitygw-system.svc.cluster.local:7070` (bypasses self-signed TLS and external DNS resolution).
- **Credentials**: `VaultStaticSecret` syncing secret `versity-s3-root` (`S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`) from Vault mount `isis-compute-cluster` into `monitoring-system`.
- **Addressing Style Constraint**: VersityGW requires path-style addressing. Configured via ConfigMap `s3-exporter-aws-config` (`AWS_CONFIG_FILE: /aws/config`) declaring `s3 = addressing_style = path`.
- **Scrape Pipeline**: `Service` + `ServiceMonitor` on port 8000 (`metrics`, interval 60s) auto-discovered by `alloy-metrics` in namespace `monitoring-system` and pushed to Mimir (`mneudata-compute`).
- **Exported Metrics**:
  - `s3_bucket_size_bytes{bucket="..."}`: Total size of S3 bucket in bytes.
  - `s3_bucket_object_count{bucket="..."}`: Total object count in S3 bucket.
- **Tracked Buckets**: `loki-s3`, `loki-ruler-s3`, `mimir-s3`, `mimir-ruler-s3`, `tempo-s3`.

---

## 7. Common Operational Commands

```bash
# Set kubeconfig
export KUBECONFIG=/home/sam/mneudata/compute-cluster/talos/ansible/kubeconfig.yaml

# Check cluster nodes
kubectl get nodes -o wide

# Check GitOps application health
kubectl get applications -n argocd

# Check Gateway API status and LB IP binding
kubectl get gateway -n envoy-gateway-system
kubectl get httproute -A
kubectl get securitypolicy -A

# Test external endpoints through Envoy Gateway
curl -k -I https://argo.compute.isis.cclrc.ac.uk
curl -k -I https://grafana.compute.isis.cclrc.ac.uk
curl -k -I https://mimir.compute.isis.cclrc.ac.uk/mneudata-compute/ready   # Expect 401
curl -k -I https://loki.compute.isis.cclrc.ac.uk/mneudata-compute/ready    # Expect 401
curl -k -I https://tempo.compute.isis.cclrc.ac.uk/mneudata-compute/ready   # Expect 401

# Query Grafana data sources API
USER=$(kubectl get secret -n grafana grafana-creds -o jsonpath='{.data.username}' | base64 -d)
PASS=$(kubectl get secret -n grafana grafana-creds -o jsonpath='{.data.password}' | base64 -d)
curl -k -s -u "$USER:$PASS" https://grafana.compute.isis.cclrc.ac.uk/api/datasources | jq .

# Verify PostgreSQL cluster health
kubectl get cluster -n postgres-system
kubectl exec -n postgres-system postgres-cluster-1 -c postgres -- psql -U postgres -d grafana -c "\l"

# Verify S3 metrics exporter & query bucket sizes from Mimir
kubectl get pods,svc,servicemonitor -n monitoring-system -l app.kubernetes.io/name=s3-exporter
kubectl logs -n monitoring-system -l app.kubernetes.io/name=s3-exporter --tail=20
kubectl exec -n monitoring-system deployment/s3-exporter -- python -c "
import urllib.request, json
req = urllib.request.Request('http://mimir-gateway.mimir.svc.cluster.local:80/prometheus/api/v1/query?query=s3_bucket_size_bytes', headers={'X-Scope-OrgID': 'mneudata-compute'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))
    for r in data['data']['result']:
        print(f\"{r['metric']['bucket']}: {r['value'][1]} bytes\")
"

# Query EPICS Channel Access PVs (from bash using conda epics-test)
export PATH="/home/sam/miniforge/envs/epics-test/epics/bin/linux-x86_64:$PATH"
export EPICS_CA_AUTO_ADDR_LIST=NO
export EPICS_CA_ADDR_LIST=130.246.55.57

caget TE:MNEUDATA:FOO
caget TE:MNEUDATA:BAR
caput TE:MNEUDATA:FOO 42
caget TE:MNEUDATA:FOO

# Verify Kafka Event Aggregator & Stream Processing using Saluki
# 1. Sniff broker topic metadata and message watermarks
docker run --rm --network host ghcr.io/isiscomputinggroup/saluki:main sniff livedata.isis.cclrc.ac.uk:31092/TESTMACHINE_events

# 2. Simulate neutron event frames into _rawEvents (this doesn't end by itself, you have to run it in a way that end's itself)
docker run --rm --network host ghcr.io/isiscomputinggroup/saluki:main howl livedata.isis.cclrc.ac.uk:31092 TESTMACHINE --frames-per-second 2

# 3. Consume and deserialise aggregated output frames from _events
docker run --rm --network host ghcr.io/isiscomputinggroup/saluki:main consume livedata.isis.cclrc.ac.uk:31092/TESTMACHINE_events --last 5

# 4. Query aggregator Prometheus metrics
kubectl exec -n epics-test deployment/kafka-event-aggregator -- bash -c 'exec 3<>/dev/tcp/127.0.0.1/8484; echo -e "GET /metrics HTTP/1.0\r\n\r\n" >&3; cat <&3' | grep -E "aggregator_(incoming|outgoing|queue)"
```

---

## 8. EPICS Controls Infrastructure & Architecture

- **Protocol & Ingress Model**:
  - EPICS Channel Access (CA) uses UDP 5064 (search/beacon) and TCP 5064 (data). PV Access (PVA) uses UDP/TCP 5075/5076.
  - CA/PVA traffic **cannot** be proxied through Envoy Gateway (HTTP/TLS only).
  - PoC IOCs run with **`hostNetwork: true`** and bind directly to the worker node interface (`EPICS_CAS_INTF_ADDR_LIST=<node IP>`).
  - Cross-subnet clients must use **unicast** address lists (`EPICS_CA_AUTO_ADDR_LIST=NO`, `EPICS_CA_ADDR_LIST=<node IP>`).
- **Pod Security Admission (PSA) Constraint**:
  - Talos Kubernetes cluster admission defaults namespaces without labels to `baseline:latest`.
  - Because `baseline` unconditionally forbids `hostNetwork: true`, any namespace hosting `hostNetwork` pods **must** have label `pod-security.kubernetes.io/enforce: privileged`.
  - **Defense-in-Depth Pod Hardening**: Despite the namespace `privileged` admission gate, all IOC pods **must** be strictly unprivileged at the container level:
    - `securityContext.privileged: false`
    - `securityContext.allowPrivilegeEscalation: false`
    - `securityContext.capabilities.drop: ["ALL"]`
    - `securityContext.runAsNonRoot: true` (e.g. UID `65534` / `nobody`)
    - `securityContext.readOnlyRootFilesystem: true` (with ephemeral memory `emptyDir` on `/tmp`)
    - `securityContext.seccompProfile.type: RuntimeDefault`
- **Multiple IOCs per Node (Port Separation)**:
  - Under `hostNetwork: true`, multiple pods on the same node share the host network stack and cannot bind port 5064 concurrently.
  - Each IOC on the same node must declare distinct ports:
    - IOC 1: `EPICS_CA_SERVER_PORT=5064`, `EPICS_CA_REPEATER_PORT=5065`
    - IOC 2: `EPICS_CA_SERVER_PORT=5066`, `EPICS_CA_REPEATER_PORT=5067`
  - Clients target multiple IOCs via space-separated address lists: `EPICS_CA_ADDR_LIST="130.246.55.57:5064 130.246.55.57:5066"`.
- **Scaling Architecture (100+ IOCs)**:
  - Long-term scaling adopts the `epics-containers` model with a **CA/PVA Gateway** running on an allocated Cilium LoadBalancer IP.
  - IOC workloads run on the standard internal pod network (no `hostNetwork`), allowing the workload namespace to remain under `restricted` PSA.

---

## 9. Kafka DAQ Streaming Pipeline

- **Architecture**:
  - `event_udp_to_kafka`: Ingests forwarded UDP streams, applies wiring maps, and produces raw frames to `<machine>_rawEvents`.
  - `kafka_event_aggregator`: Consumes `<machine>_rawEvents`, merges and sorts neutron events by time-of-flight per frame, and emits aggregated frames (`pu00`, `ev44`) to `<machine>_events`.
  - `kafka_dae_diagnostics` (`KDAEDIAG`): Consumes `<machine>_events` and `<machine>_runInfo`, serves live diagnostics and spectra as EPICS Process Variables over **PV Access (PVA)**.
- **Broker & Network Path**:
  - Cluster connects to external Kafka bootstrap broker `livedata.isis.cclrc.ac.uk:31092`.
  - Kafka cluster advertises broker nodes (`130.246.80.191:9092`, `130.246.81.188:9092`, `130.246.81.166:9092`). Egress on both `31092` and `9092` must remain open.
- **Diagnostics Tooling (`saluki`)**:
  - Uses `ghcr.io/isiscomputinggroup/saluki:main` with `--network host` to deserialise ISIS flatbuffers directly.
  - `howl`: Injects synthetic runs, vetoes, pulse metadata, and raw neutron events.
  - `consume`: Deserialises live stream messages (`ev44`, `pu00`, `pl72`, `6s4t`).
  - `sniff`: Inspects broker partition leaders, replicas, and watermark counts.
