# General Variables
variable "location" {
  description = "Azure region where resources will be deployed"
  default     = "East US"
}

variable "resource_group_name" {
  description = "Name of the resource group"
  default     = "functionapp-resources"
}

variable "storage_account_name" {
  description = "Name of the storage account"
  default     = "functionappstorageacct"
}

variable "app_service_plan_name" {
  description = "Name of the App Service Plan"
  default     = "functionapp-service-plan"
}

variable "function_app_name" {
  description = "Name of the Function App"
  default     = "example-function-app"  # must be globally unique
}

variable "subscription_id" {
  description = "The Subscription ID which should be used"
  type        = string
}

# Custom Application Settings
variable "custom_setting" {
  description = "Custom setting for the Function App"
  default     = "value"
}

variable "teamserver_post_url" {
  description = "POST URL for the Team Server"
  type        = string
}

variable "teamserver_get_url" {
  description = "GET URL for the Team Server"
  type        = string
}

variable "web_server_url" {
  description = "URL for the Web Server"
  type        = string
}