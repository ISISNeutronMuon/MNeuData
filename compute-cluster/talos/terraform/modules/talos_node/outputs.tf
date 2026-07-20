output "vm_id" {
  value = proxmox_virtual_environment_vm.this.id
}

output "node_ip" {
  value = var.ip
}
