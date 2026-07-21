################################################################################
# Proxmox Resources
################################################################################

resource "proxmox_virtual_environment_file" "talos_iso" {
  for_each = toset(distinct([for node in concat(var.control_plane_nodes, var.worker_nodes) : node.pve_node]))

  content_type = "iso"
  datastore_id = "local"
  node_name    = each.key

  source_file {
    path = var.iso_url
  }
}

################################################################################
# Node Modules (VM + Talos Config)
################################################################################

module "control_plane_first" {
  source = "./modules/talos_node"

  hostname = var.control_plane_nodes[0].hostname
  pve_node = var.control_plane_nodes[0].pve_node
  ip       = var.control_plane_nodes[0].ip
  mac      = var.control_plane_nodes[0].mac
  iso_id   = proxmox_virtual_environment_file.talos_iso[var.control_plane_nodes[0].pve_node].id

  client_configuration        = talos_machine_secrets.this.client_configuration
  machine_configuration_input = data.talos_machine_configuration.controlplane.machine_configuration
  install_disk                = var.install_disk
}

module "control_plane_others" {
  source   = "./modules/talos_node"
  for_each = { for i, node in slice(var.control_plane_nodes, 1, length(var.control_plane_nodes)) : node.hostname => node }

  hostname = each.value.hostname
  pve_node = each.value.pve_node
  ip       = each.value.ip
  mac      = each.value.mac
  iso_id   = proxmox_virtual_environment_file.talos_iso[each.value.pve_node].id

  client_configuration        = talos_machine_secrets.this.client_configuration
  machine_configuration_input = data.talos_machine_configuration.controlplane.machine_configuration
  install_disk                = var.install_disk

  depends_on = [talos_machine_bootstrap.this]
}

module "worker" {
  source   = "./modules/talos_node"
  for_each = { for node in var.worker_nodes : node.hostname => node }

  hostname         = each.value.hostname
  pve_node         = each.value.pve_node
  ip               = each.value.ip
  mac              = each.value.mac
  iso_id           = proxmox_virtual_environment_file.talos_iso[each.value.pve_node].id
  cpu_cores        = 16
  memory_dedicated = 49152

  client_configuration        = talos_machine_secrets.this.client_configuration
  machine_configuration_input = data.talos_machine_configuration.worker.machine_configuration
  install_disk                = var.install_disk

  depends_on = [module.control_plane_others]
}
################################################################################

locals {
  # Derive the Talos installer image from the ISO URL to ensure consistency.
  # Example: https://factory.talos.dev/image/<schematic>/<version>/nocloud-amd64.iso 
  # -> factory.talos.dev/installer/<schematic>:<version>
  talos_installer_image = "${split("/", var.iso_url)[2]}/installer/${split("/", var.iso_url)[4]}:${split("/", var.iso_url)[5]}"

  common_machine_config = {
    cluster = {
      network = {
        cni = { name = "none" }
      }
      proxy = { disabled = true }
    }
    machine = {
      install = {
        image = local.talos_installer_image
      }
      features = {
        kubePrism = {
          enabled = true
        }
      }
    }
  }
}

################################################################################
# Machine Secrets & Base Configurations
################################################################################

resource "talos_machine_secrets" "this" {}

data "talos_machine_configuration" "controlplane" {
  cluster_name     = var.cluster_name
  cluster_endpoint = "https://${var.control_plane_nodes[0].ip}:6443"
  machine_type     = "controlplane"
  machine_secrets  = talos_machine_secrets.this.machine_secrets
  config_patches = [
    yamlencode(local.common_machine_config),
    yamlencode({
      cluster = {
        allowSchedulingOnControlPlanes = false
      }
    })
  ]
}

data "talos_machine_configuration" "worker" {
  cluster_name     = var.cluster_name
  cluster_endpoint = "https://${var.control_plane_nodes[0].ip}:6443"
  machine_type     = "worker"
  machine_secrets  = talos_machine_secrets.this.machine_secrets
  config_patches   = [yamlencode(local.common_machine_config)]
}

data "talos_client_configuration" "this" {
  cluster_name         = var.cluster_name
  client_configuration = talos_machine_secrets.this.client_configuration
  nodes                = [for node in var.control_plane_nodes : node.ip]
  endpoints            = [for node in var.control_plane_nodes : node.ip]
}

################################################################################
# Cluster Bootstrap & Kubeconfig
################################################################################

resource "talos_machine_bootstrap" "this" {
  depends_on           = [module.control_plane_first]
  client_configuration = talos_machine_secrets.this.client_configuration
  node                 = var.control_plane_nodes[0].ip
  endpoint             = var.control_plane_nodes[0].ip
}

resource "talos_cluster_kubeconfig" "this" {
  depends_on           = [talos_machine_bootstrap.this, module.control_plane_others, module.worker]
  client_configuration = talos_machine_secrets.this.client_configuration
  node                 = var.control_plane_nodes[0].ip
  endpoint             = var.control_plane_nodes[0].ip
  timeouts = {
    read = "10m"
  }
}

################################################################################
# Outputs
################################################################################

output "kubeconfig" {
  value     = talos_cluster_kubeconfig.this.kubeconfig_raw
  sensitive = true
}

output "talosconfig" {
  value     = data.talos_client_configuration.this.talos_config
  sensitive = true
}

output "ansible_inventory" {
  value = templatefile("${path.module}/templates/inventory.yml.tpl", {
    control_plane_nodes = var.control_plane_nodes
    worker_nodes        = var.worker_nodes
  })
}
