variable "control_plane_nodes" {
  description = "Configuration for control plane nodes"
  type = list(object({
    hostname = string
    pve_node = string
    ip = string
    mac = string
  }))
  default = [
    { hostname = "cp1", pve_node = "pve-node1", ip="130.246.55.77", mac="C6:54:62:02:BC:F6" },
    { hostname = "cp2", pve_node = "pve-node2", ip="130.246.55.45", mac="C8:C6:36:CA:F0:EB" },
    { hostname = "cp3", pve_node = "pve-node1", ip="130.246.55.68", mac="C4:71:17:D2:C2:34" }
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
    { hostname = "w1", pve_node = "pve-node2", ip="130.246.55.57", mac="9E:DF:AA:00:65:FB" },
    { hostname = "w2", pve_node = "pve-node1", ip="130.246.55.51", mac="C8:EA:BA:8F:03:0D" },
    { hostname = "w3", pve_node = "pve-node2", ip="130.246.55.67", mac="CA:AB:06:1A:69:AC" }
  ]
}

variable "cluster_name" {
  description = "The name of the Talos cluster"
  type        = string
  default     = "test"
}

variable "install_disk" {
  description = "The disk to install Talos on"
  type        = string
  default     = "/dev/sda"
}

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
  description = "The URL for the Talos ISO, has siderolabs/qemu-guest-agent, siderolabs/iscsi-tools, and siderolabs/util-linux-tools extensions installed."
  type        = string
  default     = "https://factory.talos.dev/image/ce4c980550dd2ab1b17bbf2b08801c7eb59418eafe8f279833297925d67c7515/v1.13.8/nocloud-amd64.iso"
}

variable "machine_type" {
  description = "The machine type for the VMs (pinned to 10.1 to avoid VirtIO regression, that breaks networking between nodes)"
  type        = string
  default     = "pc-q35-10.1"
}
