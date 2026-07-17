variable "control_plane_nodes" {
  description = "Configuration for control plane nodes"
  type = list(object({
    hostname = string
    pve_node = string
    ip = string
    mac = string
  }))
  default = [
    { hostname = "cp1", pve_node = "pve-node1", ip="", mac="C6:54:62:02:BC:F6" },
    { hostname = "cp2", pve_node = "pve-node2", ip="", mac="C8:C6:36:CA:F0:EB" },
    { hostname = "cp3", pve_node = "pve-node1", ip="", mac="C4:71:17:D2:C2:34" }
  ]
}

variable "worker_nodes" {
  description = "Configuration for worker nodes"
  type = list(object({
    hostname = string
    pve_node = string
        ip = string
    mac = string
  }))
  default = [
    { hostname = "w1", pve_node = "pve-node2", ip="", mac="9E:DF:AA:00:65:FB" },
    { hostname = "w2", pve_node = "pve-node1", ip="", mac="C8:EA:BA:8F:03:0D" },
    { hostname = "w3", pve_node = "pve-node2", ip="", mac="CA:AB:06:1A:69:AC" }
  ]
}

# variable "cluster_name" {
#   description = "The name of the Talos cluster"
#   type        = string
#   default     = "test"
# }

# variable "install_disk" {
#   description = "The disk to install Talos on"
#   type        = string
#   default     = "/dev/sda"
# }

variable "proxmox_endpoint" {
  description = "The Proxmox API endpoint"
  type        = string
  default     = "https://130.246.53.66:8006" # Defaulting to pve-node1
}

variable "proxmox_password" {
  description = "The Proxmox root password"
  type        = string
  sensitive   = true
}

variable "iso_url" {
  description = "The URL for the Talos ISO"
  type        = string
  default     = "https://factory.talos.dev/image/a7bcadbc1b6d03c0e687be3a5d9789ef7113362a6a1a038653dfd16283a92b6b/v1.13.5/nocloud-amd64.iso"
}

# variable "management_interface" {
#   description = "Management network interface for Proxmox VE"
#   type        = string
#   default     = "nic0"
# }
