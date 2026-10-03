# GPU node pool for vLLM, added to Project A's AKS cluster. It scales to zero: with no vLLM pod
# pending, the cluster autoscaler removes the node and the pool costs nothing but its (empty) VM
# scale set.
data "azurerm_kubernetes_cluster" "a" {
  name                = var.cluster_name
  resource_group_name = var.cluster_resource_group
}

resource "azurerm_kubernetes_cluster_node_pool" "gpu" {
  name                  = "gpu"
  kubernetes_cluster_id = data.azurerm_kubernetes_cluster.a.id
  vm_size               = var.gpu_vm_size
  vnet_subnet_id        = data.azurerm_kubernetes_cluster.a.agent_pool_profile[0].vnet_subnet_id
  os_disk_type          = "Managed"

  # Scale to zero when idle. The autoscaler adds a node when a pod requesting nvidia.com/gpu is
  # pending and removes it after the pool's scale-down delay with nothing scheduled.
  auto_scaling_enabled = true
  min_count            = 0
  max_count            = var.gpu_max_nodes
  node_count           = 0

  priority        = var.spot ? "Spot" : "Regular"
  eviction_policy = var.spot ? "Delete" : null
  spot_max_price  = var.spot ? var.spot_max_price : null

  # AKS installs the NVIDIA driver on GPU pools; the device plugin (deploy/gpu) advertises
  # nvidia.com/gpu. Only pods that tolerate the taint (vLLM) land here.
  gpu_driver  = "Install"
  node_labels = { "workload" = "llm" }
  node_taints = concat(
    ["nvidia.com/gpu=present:NoSchedule"],
    # AKS adds this taint to spot pools itself; declaring it keeps plans clean.
    var.spot ? ["kubernetes.azure.com/scalesetpriority=spot:NoSchedule"] : [],
  )

  tags = var.tags
}
