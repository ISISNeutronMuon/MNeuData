# resource "helm_release" "cilium" {
#   name       = "cilium"
#   repository = "https://helm.cilium.io"
#   chart      = "cilium"
#   namespace  = "cilium"
#   version    = "1.19.5"
#
#   depends_on = [talos_cluster_kubeconfig.this, data.talos_cluster_health.this]
#
#   # Please ensure these values are in line with argo-cd in the gitops
#   values = [
#     yamlencode({
#       ipam = {
#         mode = "kubernetes"
#       }
#       kubeProxyReplacement = true
#       k8sServiceHost       = "localhost"
#       k8sServicePort       = 7445
#       securityContext = {
#         capabilities = {
#           ciliumAgent      = ["CHOWN", "KILL", "NET_ADMIN", "NET_RAW", "IPC_LOCK", "SYS_ADMIN", "SYS_RESOURCE", "DAC_OVERRIDE", "FOWNER", "SETGID", "SETUID"]
#           cleanCiliumState = ["NET_ADMIN", "SYS_ADMIN", "SYS_RESOURCE"]
#         }
#       }
#       cgroup = {
#         autoMount = {
#           enabled = false
#         }
#         hostRoot = "/sys/fs/cgroup"
#       }
#       gatewayAPI = {
#         enabled = true
#         externalTrafficPolicy = "Cluster"
#       }
#     })
#   ]
# }
