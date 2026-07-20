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

resource "proxmox_virtual_environment_vm" "control_plane" {
  for_each = { for node in var.control_plane_nodes : node.hostname => node }

  name      = each.value.hostname
  node_name = each.value.pve_node

  machine = "q35"
  bios    = "ovmf"

  cpu {
    cores = 4
    type  = "host"
  }

  memory {
    dedicated = 16384
    floating  = 0 # Disable memory ballooning
  }

  agent {
    enabled = true
    trim    = true
  }

  network_device {
    mac_address = each.value.mac
    bridge      = "vmbr0"
  }

  initialization {
    ip_config {
      ipv4 {
        address = "${each.value.ip}/22"
        gateway = "130.246.52.254"
      }
    }
  }

  disk {
    datastore_id = "local-lvm"
    file_format  = "raw"
    interface    = "scsi0"
    size         = 32
    discard      = "on"
    ssd          = true
  }

  efi_disk {
    datastore_id = "local-lvm"
  }

  boot_order = ["scsi0", "ide3"]

  cdrom {
    file_id   = proxmox_virtual_environment_file.talos_iso[each.value.pve_node].id
    interface = "ide3"
  }

  operating_system {
    type = "l26"
  }
}

resource "proxmox_virtual_environment_vm" "worker" {
  for_each = { for node in var.worker_nodes : node.hostname => node }

  name      = each.value.hostname
  node_name = each.value.pve_node

  machine = "q35"
  bios    = "ovmf"

  cpu {
    cores = 16
    type  = "host"
  }

  memory {
    dedicated = 49152
    floating  = 0 # Disable memory ballooning
  }

  agent {
    enabled = true
    trim    = true
  }

  network_device {
    mac_address = each.value.mac
    bridge      = "vmbr0"
  }

  initialization {
    ip_config {
      ipv4 {
        address = "${each.value.ip}/22"
        gateway = "130.246.52.254"
      }
    }
  }

  disk {
    datastore_id = "local-lvm"
    file_format  = "raw"
    interface    = "scsi0"
    size         = 32
    discard      = "on"
    ssd          = true
  }

  efi_disk {
    datastore_id = "local-lvm"
  }

  boot_order = ["scsi0", "ide3"]

  cdrom {
    file_id   = proxmox_virtual_environment_file.talos_iso[each.value.pve_node].id
    interface = "ide3"
  }

  operating_system {
    type = "l26"
  }
}

################################################################################
# Locals for shared configurations
################################################################################

locals {
  common_machine_config = {
    cluster = {
      network = {
        cni = { name = "none" }
      }
      proxy = { disabled = true }
    }
    machine = {
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
  config_patches   = [yamlencode(local.common_machine_config)]
}

data "talos_machine_configuration" "worker" {
  cluster_name     = var.cluster_name
  cluster_endpoint = "https://${var.control_plane_nodes[0].ip}:6443"
  machine_type     = "worker"
  machine_secrets  = talos_machine_secrets.this.machine_secrets
  config_patches   = [yamlencode(local.common_machine_config)]
}

################################################################################
# Machine Configuration Application
################################################################################

resource "talos_machine_configuration_apply" "controlplane" {
  for_each = { for node in var.control_plane_nodes : node.hostname => node }

  client_configuration        = talos_machine_secrets.this.client_configuration
  machine_configuration_input = data.talos_machine_configuration.controlplane.machine_configuration
  node = each.value.ip
  config_patches = [
    yamlencode({
      machine = {
        install = {
          disk = var.install_disk
        }
        certSANs = [
          each.value.ip,
          each.value.hostname
        ]
      }
    })
  ]
}

resource "talos_machine_configuration_apply" "worker" {
  for_each = { for node in var.worker_nodes : node.hostname => node }

  client_configuration        = talos_machine_secrets.this.client_configuration
  machine_configuration_input = data.talos_machine_configuration.worker.machine_configuration
  node                        = each.value.ip
  config_patches = [
    yamlencode({
      machine = {
        install = {
          disk = var.install_disk
        }
        certSANs = [
          each.value.ip,
          each.value.hostname
        ]
      }
    })
  ]
}

################################################################################
# Cluster Bootstrap & Kubeconfig
################################################################################

resource "talos_machine_bootstrap" "this" {
  depends_on           = [talos_machine_configuration_apply.controlplane]
  client_configuration = talos_machine_secrets.this.client_configuration
  node                 = var.control_plane_nodes[0].ip
  endpoint             = var.control_plane_nodes[0].ip
}

resource "talos_cluster_kubeconfig" "this" {
  depends_on           = [talos_machine_bootstrap.this]
  client_configuration = talos_machine_secrets.this.client_configuration
  node                 = var.control_plane_nodes[0].ip
  endpoint             = var.control_plane_nodes[0].ip
  timeouts = {
    read = "10m"
  }
}

data "talos_cluster_health" "this" {
  depends_on           = [talos_cluster_kubeconfig.this, talos_machine_configuration_apply.worker]
  client_configuration = talos_machine_secrets.this.client_configuration
  control_plane_nodes  = [for node in var.control_plane_nodes : node.ip]
  worker_nodes         = [for node in var.worker_nodes : node.ip]
  endpoints            = [for node in var.control_plane_nodes : node.ip]
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
  value     = talos_machine_secrets.this.client_configuration
  sensitive = true
}
