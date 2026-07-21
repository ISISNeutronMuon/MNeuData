all:
  vars:
    ansible_connection: local
  children:
    control_plane:
      hosts:
%{ for node in control_plane_nodes ~}
        ${node.hostname}:
          ansible_host: ${node.ip}
%{ endfor ~}
    worker:
      hosts:
%{ for node in worker_nodes ~}
        ${node.hostname}:
          ansible_host: ${node.ip}
%{ endfor ~}
