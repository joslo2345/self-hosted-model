output "gpu_pool" {
  value = {
    name     = azurerm_kubernetes_cluster_node_pool.gpu.name
    vm_size  = azurerm_kubernetes_cluster_node_pool.gpu.vm_size
    priority = azurerm_kubernetes_cluster_node_pool.gpu.priority
  }
}
