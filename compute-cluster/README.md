# Description
This dir contains prototypes for the various compute cluster possibilities, namely deploying a Talos Linux/Kubernetes cluster, and a ubuntu based node k3s setup. Lastly we have a gitops dir that would be our prototype deployment for the content of the compute cluster.

# Proxmox Node Setup
- Aquire a proxmox VE ISO image from: https://www.proxmox.com/en/downloads/proxmox-virtual-environment
- Login to each idrac instance using admin credentials.
- Use the virtual mount feature to mount the ISO, then reboot the managed system.
- Proceed with generic proxmox install, give it an appropriate name such as pve-node1, pve-node2 etc... and ensure that the correct IP is assigned according to the values expected in the ansible/terraform for whichever version you are installing.
- Create a proxmox cluster if this is the first node, else join the node to the cluster using the join information.
- Continue to setting up all other nodes and join it to the cluster.

After cluster is made, you can proceed to running the appropriate terraform/ansible to setup the cluster.