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
- Proxmox VE 8.x environment with API access.

---

## 1. Infrastructure Provisioning (Terraform)

The Terraform configuration follows a sequential deployment strategy to ensure stable cluster formation.

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
ansible-playbook playbooks/deploy.yml
```

---

## 3. Verification & GitOps

### Cilium
Verify that Cilium is running and has replaced kube-proxy:
```bash
export KUBECONFIG=$(pwd)/kubeconfig.yaml
kubectl -n kube-system get pods -l k8s-app=cilium
```

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
   The `app-of-apps` application should be visible in the ArgoCD UI, managing all other cluster components.

## Maintenance

- **Scaling**: Add nodes to `terraform/variables.tf` and re-run `terraform apply`.
- **Updates**: Update versions in `ansible/group_vars/all.yml` and re-run the Ansible playbook.
