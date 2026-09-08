# EPICS IOC Component

This directory contains the Kubernetes manifests for running EPICS Soft IOCs in the MNeuData compute cluster.

## Architecture
- **Ingress**: `hostNetwork: true` binds directly to node interface (pinned to `talos-12a-xos` / `130.246.55.57`).
- **Namespace**: `epics-test` (labeled with `pod-security.kubernetes.io/enforce: privileged` to permit `hostNetwork`).
- **Pod Hardening**: Containers are locked down (`privileged: false`, `allowPrivilegeEscalation: false`, `capabilities.drop: [ALL]`, `runAsUser: 65534`, `readOnlyRootFilesystem: true`).
- **Port Allocation**:
  - `epics-ioc-1`: Server port `5064`, repeater port `5065`
  - `epics-ioc-2`: Server port `5066`, repeater port `5067`

## Testing PVs from Bash
```bash
export PATH="/home/sam/miniforge/envs/epics-test/epics/bin/linux-x86_64:$PATH"
export EPICS_CA_AUTO_ADDR_LIST=NO
export EPICS_CA_ADDR_LIST=130.246.55.57

caget TE:MNEUDATA:FOO
caget TE:MNEUDATA:BAR
caput TE:MNEUDATA:FOO 42
caget TE:MNEUDATA:FOO
```
