provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

# Resource Group
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
}

# Storage Account
resource "azurerm_storage_account" "storage" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

# App Service Plan
resource "azurerm_service_plan" "plan" {
  name                = var.app_service_plan_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  os_type             = "Linux"
  sku_name            = "B1"
  worker_count        = 3
}

# Function App
resource "azurerm_linux_function_app" "function" {
  depends_on = [azurerm_storage_account.storage]

  name                       = var.function_app_name
  resource_group_name        = azurerm_resource_group.rg.name
  location                   = azurerm_resource_group.rg.location
  service_plan_id            = azurerm_service_plan.plan.id
  storage_account_name       = azurerm_storage_account.storage.name
  storage_account_access_key = azurerm_storage_account.storage.primary_access_key
  https_only                 = true

  site_config {
    application_stack {
      python_version = "3.11"
    }

    minimum_tls_version      = "1.2"
    ftps_state               = "Disabled"
    elastic_instance_minimum = 3
    http2_enabled            = true
    always_on                = true
  }

  app_settings = {
    "AzureWebJobsStorage"                       = azurerm_storage_account.storage.primary_connection_string
    "FUNCTIONS_WORKER_RUNTIME"                  = "python"
    "CUSTOM_SETTING"                            = var.custom_setting
    "WEBSITE_RUN_FROM_PACKAGE"                  = "1"
    "WEBSITE_MAX_DYNAMIC_APPLICATION_SCALE_OUT" = "3"
    "FUNCTIONS_EXTENSION_VERSION"               = "~4"
    "TEAMSERVER_POST_URL"                       = var.teamserver_post_url
    "TEAMSERVER_GET_URL"                        = var.teamserver_get_url
    "WEB_SERVER_URL"                            = var.web_server_url
    "TEAMSERVER_GET_ROUTE"                      = var.teamserver_get_route
    "TEAMSERVER_POST_ROUTE"                     = var.teamserver_post_route
    "WEB_ROUTE_BASE"                            = var.web_route_base
  }
}
