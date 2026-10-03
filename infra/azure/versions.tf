terraform {
  required_version = ">= 1.9"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 5.8" } # same as Project A
  }
  # Separate state from Project A: this stack only adds a node pool to A's cluster, so it can be
  # destroyed on its own without touching A. Configure with -backend-config at init.
  backend "azurerm" {}
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}
