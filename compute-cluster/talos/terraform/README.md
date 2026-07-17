# Talos Kubernetes Cluster Terraform Implementation

This directory contains a Terraform implementation that sets up a Talos Kubernetes cluster and installs the Cilium CNI, now featuring automated bare-metal Proxmox VE provisioning using iDRAC Redfish API.

## Prerequisites

- [Terraform](https://www.terraform.io/downloads.html) >= 1.0.0
- Dell PowerEdge servers with iDRAC Redfish API access.
- iDRAC credentials with sufficient privileges (set in `idrac_username`, `idrac_password1`, and `idrac_password2` variables).
- Target OS installation password (configured via `proxmox_password`).
- `proxmox-auto-install-assistant` installed locally (used to embed answer files into the ISO):
  ```bash
  wget https://enterprise.proxmox.com/debian/proxmox-release-bookworm.gpg -O /etc/apt/trusted.gpg.d/proxmox-release-bookworm.gpg
  echo "deb http://download.proxmox.com/debian/pve bookworm pve-no-subscription" > /etc/apt/sources.list.d/pve.list
  apt-get update && apt-get install proxmox-auto-install-assistant
  ```
- The machine running Terraform must be reachable from the iDRACs over HTTP (set `iso_server_address` to its IP; port defaults to `8000`).
- Access to the nodes specified in `variables.tf` via the Talos API (usually port 50000).

## Proxmox VE Provisioning & Clustering Flow

This Terraform workspace automates the entire bare-metal lifecycle before deploying the Talos Kubernetes cluster:

1. **Automated Answer File**: Generates node-specific TOML answer files (`proxmox-installer-configuration-*.toml`) from templates to configure region, keyboard, root password (`proxmox_password`), and network settings (supporting both DHCP and static IP configuration on `nic0`).
2. **Auto-Install ISO Preparation**: Downloads the stock Proxmox VE ISO (`proxmox_iso_url`) once into `isos/`, then runs `proxmox-auto-install-assistant prepare-iso --fetch-from iso` to embed each node's answer file, producing `isos/proxmox-auto-pve-node{1,2}.iso`. This is what makes the installation fully unattended — the stock ISO on its own only boots the interactive GUI installer.
3. **Local ISO Hosting**: Starts a small HTTP server (`python3 -m http.server`, port `iso_server_port`) on the machine running Terraform so the iDRACs can stream the prepared ISOs from `http://<iso_server_address>:<port>/`. The server must remain running until installation completes.
4. **iDRAC ISO Mounting**: Uses the `dell/redfish` provider to mount each node's prepared ISO on the virtual media interface of the corresponding physical node.
5. **Hardware Boot Override & Reboot**: Overrides the boot target to Virtual Media (CD/DVD) and initiates a reboot (`ForceRestart`) via iDRAC API. The node boots into the automated installer, installs Proxmox unattended, and reboots into the installed system.
6. **iSM Installation**: Once Proxmox VE is installed and online (SSH waits up to 45 minutes), SSH-based provisioners automatically download and install the iDRAC Service Module (`dcism`/`dcism-osc`) to establish native OS-to-iDRAC telemetry.
7. **Clustering**: Automatically configures the first node as the cluster master (`pvecm create`) and joins the second node non-interactively using an automated `expect` login session (`pvecm add`).
8. **Talos VM Deployment**: Triggers the VM provisioning and Kubernetes clustering only after the Proxmox cluster is fully configured and ready.

## Usage

1. Initialize Terraform:
   ```bash
   terraform init
   ```

2. Review the plan (ensure all credentials are set in environment variables or `secrets.auto.tfvars`):
   ```bash
   terraform plan
   ```

3. Apply the configuration:
   ```bash
   terraform apply
   ```

## Repository Structure

- `providers.tf`: Centralized provider configurations (Talos, Helm, Kubernetes, Redfish).
- `variables.tf`: Input variables including network, iDRAC credentials, and fallback settings.
- `idrac.tf`: iDRAC virtual media mounting, answer file generation, and hardware booting resources.
- `proxmox_init.tf`: SSH scripts for automated iSM installation and non-interactive Proxmox clustering.
- `main.tf`: Core logic for Talos VMs, secrets, machine configurations, and bootstrapping, integrated to wait for clustering to complete.
- `cilium.tf`: Helm-based Cilium CNI installation using structured `yamlencode` values.
- `argocd.tf`: Helm-based ArgoCD installation using structured `yamlencode` values.

## Outputs

- `kubeconfig`: The generated kubeconfig for the cluster (sensitive).
- `talosconfig`: The Talos client configuration (sensitive).

To extract the kubeconfig:
```bash
terraform output -raw kubeconfig > kubeconfig.yaml
```
