terraform {
  required_providers {
    talos = {
      source  = "siderolabs/talos"
      version = "0.11.0"
    }
    proxmox = {
      source  = "bpg/proxmox"
      version = "0.111.0"
    }
  }
}
