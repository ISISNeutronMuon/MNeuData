# Talos Kubernetes Cluster on Proxmox

This repository contains Terraform configurations to deploy a high-availability Talos Kubernetes cluster on Proxmox Virtual Environment. It automates the provisioning of virtual machines, handles the Talos machine configuration, and bootstraps the cluster in a deterministic, sequential manner.

## Architecture

### Grouped Sequential Deployment
To ensure stable cluster formation, the deployment follows a "Grouped Sequential" strategy:
1. **First Control Plane (CP1)**: Provisioned and bootstrapped first to establish the cluster API.
2. **Additional Control Planes**: Provisioned and joined to the cluster only after CP1 is successfully bootstrapped.
3. **Worker Nodes**: Provisioned and joined once the full control plane is operational.

### Unified Node Module
Infrastructure (Proxmox VMs) and software configuration (Talos Application) are unified in a single `talos_node` module. This ensures that Talos configurations are applied immediately after the VM is created and reachable, while maintaining clean, DRY code.

### Security & Defaults
- **Tainted Control Planes**: Control plane nodes are automatically tainted with `node-role.kubernetes.io/control-plane:NoSchedule` to reserve them for cluster management.
- **KubePrism**: Enabled for simplified internal cluster communication.
- **CNI**: Currently configured with `none`, allowing for manual or post-deployment installation of CNIs like Cilium.

## Prerequisites

- [Terraform](https://www.terraform.io/downloads.html) >= 1.0.0
- [Talosctl](https://www.talos.dev/latest/introduction/getting-started/#installing-talosctl)
- [Kubectl](https://kubernetes.io/docs/tasks/tools/)
- Proxmox VE 8.x environment with API access.

## Configuration

1. **Variables**: Review `variables.tf` to configure:
   - `control_plane_nodes`: Hostnames, IPs, MAC addresses, and target Proxmox nodes.
   - `worker_nodes`: Hostnames, IPs, MAC addresses, and target Proxmox nodes.
   - `iso_url`: The Talos ISO image to be uploaded to Proxmox.
2. **Secrets**: Create a `secrets.auto.tfvars` file to store sensitive credentials:
   ```hcl
   proxmox_password = "your-secure-password"
   ```

## Deployment Guide (Nothing to Cluster)

Follow these steps to deploy the cluster from scratch:

1. **Initialize Terraform**:
   Download the required providers (Talos, Proxmox, etc.).
   ```bash
   terraform init
   ```

2. **Validate Configuration**:
   Ensure the HCL syntax and logic are correct.
   ```bash
   terraform validate
   ```

3. **Apply Deployment**:
   Execute the plan. This will take several minutes as it uploads the ISO, creates VMs, and waits for cluster bootstrapping.
   ```bash
   terraform apply
   ```

4. **Extract Configuration**:
   Once finished, extract the `kubeconfig` and `talosconfig` from the Terraform state.
   ```bash
   # Extract Kubeconfig
   terraform output -raw kubeconfig > kubeconfig.yaml
   export KUBECONFIG=$(pwd)/kubeconfig.yaml

   # Extract Talosconfig
   terraform output -raw talosconfig > talosconfig.yaml
   ```

5. **Verify Cluster Health**:
   Check if the nodes are ready and the cluster is healthy.
   ```bash
   # Check Talos nodes
   talosctl --talosconfig talosconfig.yaml health -n <CP1_IP>

   # Check Kubernetes nodes
   kubectl get nodes
   ```

## Repository Structure

- `main.tf`: Defines machine secrets, shared configurations, and the sequential deployment logic.
- `providers.tf`: Configures the `siderolabs/talos` and `bpg/proxmox` providers.
- `variables.tf`: Defines network and infrastructure parameters.
- `modules/talos_node`: Reusable module for VM and Talos node lifecycle management.
- `secrets.auto.tfvars`: (User-provided) Sensitive credentials.

## Maintenance

To scale the cluster, simply add new entries to the `control_plane_nodes` or `worker_nodes` lists in `variables.tf` and run `terraform apply` again.
