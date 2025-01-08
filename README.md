# Azure Function Redirector

Acts as a proxy to redirect requests to a target URL (i.e C2 server).

## Prerequisites

- Azure CLI
- Azure Functions Core Tools
- Terraform
- Python 3.11+
- Azure Subscription

## Usage

1. Configure Azure CLI:

```bash
az login
az account set --subscription <subscription_id>
```

2. Initialize Terraform:

```bash
cd terraform
terraform init
```

3. Create a `terraform.tfvars` file:

```hcl
subscription_id = "<subscription_id>"
# URIs in C2 profile should match the Azure Function URL
teamserver_post_url = "https://your-c2-domain.com/api/post"
teamserver_get_url = "https://your-c2-domain.com/api/get"
web_server_url = "http://example.com"
```

4. Update variables in `terraform/variables.tf`:

- `location`: Azure region (default: East US)
- `resource_group_name`: Resource group name
- `function_app_name`: Function app name
- `storage_account_name`: Storage account name

5. Deploy the infrastructure:

```bash
terraform plan
terraform apply
```

6. Deploy the function code:

```bash
cd ../function
func azure functionapp publish <function_app_name> --build remote
```

## Azure Function Settings

- Authentication Level: Anonymous
- Worker Runtime: Python 3.11
- Service Plan: Linux B1 (Basic)
- HTTPS Only: Enabled
- TLS Version: 1.2 minimum

## Infrastructure

The Terraform configuration creates:

- Resource Group
- Storage Account
- App Service Plan (Consumption)
- Function App
- Function Code Deployment

## **Credits**

- [FunctionalC2](https://github.com/RedSiege/FunctionalC2)
- [Azure Functions with Terraform](https://cloudengineerskills.com/posts/azure-functions-terraform/)
