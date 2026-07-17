# resource "helm_release" "argocd" {
#   name       = "argocd"
#   repository = "https://argoproj.github.io/argo-helm"
#   chart      = "argo-cd"
#   namespace  = "argocd"
#   version    = "10.1.1"
#
#   depends_on = [talos_cluster_kubeconfig.this, data.talos_cluster_health.this]
#
#   # Please ensure these values are in line with argo-cd in the gitops
#   values = [
#     yamlencode({
#       configs = {
#         params = {
#           "server.insecure" = "true"
#         }
#       }
#       redis-ha = {
#         enabled = "true"
#       }
#       controller = {
#         replicas = 2
#       }
#       server = {
#         autoscaling = {
#           enabled = true
#           minReplicas = 2
#         }
#         httproute = {
#           enabled = true
#           hostnames = ["argocd.isiscluster.isis.cclrc.ac.uk"]
#           parentRefs = [
#             {
#               group = "gateway.networking.k8s.io"
#               kind = "Gateway"
#               name = "cilium-gateway"
#               namespace = "cilium"
#               sectionName = "https-main"
#             }
#           ]
#         }
#         repoServer = {
#           autoscaling = {
#             enabled = true
#             minReplicas = 2
#           }
#         }
#         applicationSet = {
#           replicas = 2
#         }
#       }
#     })
#   ]
# }
