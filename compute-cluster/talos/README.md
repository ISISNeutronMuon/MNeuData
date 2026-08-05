# Talos Kubernetes Cluster on Proxmox

This project provides a complete automated workflow for deploying a high-availability Talos Kubernetes cluster on Proxmox VE, followed by post-provisioning configuration using Ansible and GitOps.

## Project Structure

- `terraform/`: Infrastructure as Code to provision Proxmox VMs and bootstrap the Talos cluster.
- `ansible/`: Post-provisioning tasks including CNI (Cilium) installation and ArgoCD bootstrapping.
- `../gitops/`: GitOps repository structure for application management.

## Prerequisites

- [Terraform](https://www.terraform.io/downloads.html) >= 1.0.0
- [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)
- [Talosctl](https://www.talos.dev/latest/introduction/getting-started/#installing-talosctl)
- [Kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Helm](https://helm.sh/docs/intro/install/)
- Proxmox VE 9.x environment with API access.

---

## 1. Infrastructure Provisioning (Terraform)

The Terraform configuration follows a sequential deployment strategy to ensure stable cluster formation.

### Update talos version

Either manually grab the correct schematic based on current requirements or run the talos-schametic.sh script.
```bash
talos-schematic.sh --add ./variables.tf
```

### Configuration
1. **Secrets**: Create `terraform/secrets.auto.tfvars`:
   ```hcl
   proxmox_password = "your-secure-password"
   ```
2. **Variables**: Review `terraform/variables.tf` for node definitions and network settings.

### Deployment
```bash
cd terraform
terraform init
terraform apply
```

If you get an error about /dev/nvme0n1 or similar being already in use, go into the proxmox UI and for each node, go to the disks, and wipe the nvme disks that had ZSF partitions on them. Initially this should be both /dev/nvme0n1 and /dev/nvme0n1.

Example of error:
```
│ Error: Unable to Create ZFS pool "nvme-storage-pve-node1"
│ 
│   with proxmox_node_disk_zfs.nvme_storage["pve-node1"],
│   on main.tf line 17, in resource "proxmox_node_disk_zfs" "nvme_storage":
│   17: resource "proxmox_node_disk_zfs" "nvme_storage" {
│ 
│ All attempts fail:
│ #1: error creating ZFS pool: received an HTTP 500 response - Reason: device '/dev/nvme0n1' is already in use
│ #2: error creating ZFS pool: received an HTTP 500 response - Reason: device '/dev/nvme0n1' is already in use
│ #3: error creating ZFS pool: received an HTTP 500 response - Reason: device '/dev/nvme0n1' is already in use

```

### Extract Configuration
After successful deployment, extract the credentials needed for cluster management and Ansible:
```bash
# Extract Kubeconfig (Save it to the ansible directory)
terraform output -raw kubeconfig > ../ansible/kubeconfig.yaml

# Extract Talosconfig
terraform output -raw talosconfig > ../ansible/talosconfig.yaml

# Extract Ansible Inventory
terraform output -raw ansible_inventory > ../ansible/inventory/hosts.yml
```

---

## 2. Post-Provisioning (Ansible)

Once the Talos cluster is bootstrapped, Ansible is used to install Cilium as the CNI and setup ArgoCD for GitOps.

### Configuration
1. **Vault Password**: Ensure a `.vault-pass` file exists in the `ansible/` directory or be prepared to enter the password interactively.
   ```bash
   echo "your-vault-password" > ansible/.vault-pass
   ```
2. **Inventory**: The inventory at `ansible/inventory/hosts.yml` is generated from Terraform outputs to ensure consistency with the provisioned nodes.

### Deployment
Run the deployment playbook from the `ansible` directory:
```bash
cd ../ansible
rm argocd-password.txt
ansible-playbook playbooks/deploy.yml
```

---

## 3. Restart Cilium

As part of deploying Cilium, it's likely that the gateway will not set up correctly after the application is adopted by argocd. So restart it.
```bash
kubectl rollout restart ds cilium -n kube-system
kubectl rollout restart ds cilium-envoy -n kube-system
kubectl rollout restart deployment cilium-operator -n kube-system
```

---

## 4. Verification & GitOps

### ArgoCD
ArgoCD is bootstrapped using an "App of Apps" pattern pointing to the `MNeuData` repository.

1. **Get Admin Password**:
   ```bash
   cat argocd-password.txt
   ```
2. **Access UI**: Port-forward to the ArgoCD server:
   ```bash
   kubectl -n argocd port-forward svc/argocd-server 8080:443
   ```
3. **Check Applications**:
   The `app-of-apps` application should be visible in the ArgoCD UI, managing all other cluster components. After the argocd app is adopted by itself as an argocd application the base path will become /argocd, so https://localhost:8080/argocd will be the url.

## Maintenance

- **Scaling**: Add nodes to `terraform/variables.tf` and re-run `terraform apply`.
- **Updates**: Update versions in `ansible/group_vars/all.yml` and re-run the Ansible playbook.
