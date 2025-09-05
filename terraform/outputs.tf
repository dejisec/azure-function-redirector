output "function_app_name" {
  description = "The name of the Function App"
  value       = azurerm_linux_function_app.function.name
}

output "function_default_hostname" {
  description = "Default hostname of the Function App"
  value       = azurerm_linux_function_app.function.default_hostname
}

output "resource_group_name" {
  description = "Resource group of the Function App"
  value       = azurerm_resource_group.rg.name
}

output "location" {
  description = "Azure region of the deployment"
  value       = azurerm_resource_group.rg.location
}

