resource "proxmox_virtual_environment_vm" "this" {
  name      = var.hostname
  node_name = var.pve_node

  machine = "q35"
  bios    = "ovmf"

  cpu {
    cores = var.cpu_cores
    type  = "host"
  }

  memory {
    dedicated = var.memory_dedicated
    floating  = 0
  }

  agent {
    enabled = true
    trim    = true
  }

  network_device {
    mac_address = var.mac
    bridge      = "vmbr0"
  }

  initialization {
    ip_config {
      ipv4 {
        address = "${var.ip}/22"
        gateway = var.gateway
      }
    }
  }

  disk {
    datastore_id = var.datastore_id
    file_format  = "raw"
    interface    = "scsi0"
    size         = 32
    discard      = "on"
    ssd          = true
  }

  efi_disk {
    datastore_id = var.datastore_id
  }

  boot_order = ["scsi0", "ide3"]

  cdrom {
    file_id   = var.iso_id
    interface = "ide3"
  }

  operating_system {
    type = "l26"
  }
}

resource "talos_machine_configuration_apply" "this" {
  client_configuration        = var.client_configuration
  machine_configuration_input = var.machine_configuration_input
  node                        = var.ip
  config_patches = [
    yamlencode({
      machine = {
        install = {
          disk = var.install_disk
        }
        certSANs = [
          var.ip,
          var.hostname
        ]
      }
    })
  ]
  depends_on = [proxmox_virtual_environment_vm.this]
}
