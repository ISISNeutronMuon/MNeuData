variable "hostname" {
  type = string
}

variable "pve_node" {
  type = string
}

variable "ip" {
  type = string
}

variable "mac" {
  type = string
}

variable "gateway" {
  type    = string
  default = "130.246.52.254"
}

variable "cpu_cores" {
  type    = number
  default = 4
}

variable "memory_dedicated" {
  type    = number
  default = 16384
}

variable "iso_id" {
  type = string
}

variable "install_disk" {
  type    = string
  default = "/dev/sda"
}

variable "client_configuration" {
  type = any
}

variable "machine_configuration_input" {
  type = string
}

variable "machine_type" {
  description = "The machine type for the VM"
  type        = string
  default     = "pc-q35-10.1"
}

variable "disk_size" {
  type    = number
  default = 32
}
