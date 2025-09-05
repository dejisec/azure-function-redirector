# Azure Function Redirector

Acts as a proxy to redirect requests to a target URL (e.g., C2 server).

## Prerequisites

- Azure CLI
- Azure Functions Core Tools
- Terraform
- Python 3.11+
- Azure Subscription

## Deployment

1. Sign in and select your subscription:

    ```bash
    az login
    az account set --subscription <subscription_id>
    ```

2. Prepare variables:

    ```bash
    make prepare
    vi terraform/terraform.tfvars
    ```

3. Deploy infra and publish code:

    ```bash
    make all
    ```

This runs: `terraform init`, `terraform plan`, `terraform apply -auto-approve`, publishes the function app, and prints outputs.

To destroy:

```bash
make destroy
```

### Endpoints

- `GET /api/get` → proxies to `TEAMSERVER_GET_URL`
- `POST /api/post` → proxies to `TEAMSERVER_POST_URL`
- `ANY /api/web` → proxies to `WEB_SERVER_URL`
- `ANY /api/web/{*path}` → proxies to `WEB_SERVER_URL/{path}`

### Configuration

App settings:

- `TEAMSERVER_GET_URL`
- `TEAMSERVER_POST_URL`
- `WEB_SERVER_URL`
- `ALLOW_INSECURE_SSL` ("true" to disable SSL verification for `/api/web`; default "false")
- `TEAMSERVER_GET_ROUTE` (default: `get`)
- `TEAMSERVER_POST_ROUTE` (default: `post`)
- `WEB_ROUTE_BASE` (default: `web`)

### Notes

- Plan: App Service Basic plan (B1). HTTPS-only, TLS 1.2+, HTTP/2.
- The proxy strips hop-by-hop headers and adds `X-Forwarded-For` when a valid client IP is present.

## Helpers

Handy targets after deploy (they use current Terraform outputs):

```bash
# Possible outbound public IPs used by the Function App
make info

# Default hostname of the Function App
make hostname

# List HTTP-triggered functions with constructed URLs
make routes

# Provision a StorageV2 account with static website enabled and print its endpoint
# Optionally pass a name: STORAGE_NAME must be globally unique
make storage-website STORAGE_NAME=mystaticweb123
make storage-website

### Pre-deployment: set route prefix

Override the `routePrefix` in `function/host.json` before publishing:

```bash
# One-off edit
make set-route-prefix ROUTE_PREFIX=myapi

# Or inline during publish
make publish ROUTE_PREFIX=myapi
```

### Credits

- [FunctionalC2](https://github.com/RedSiege/FunctionalC2)
- [Azure Functions with Terraform](https://cloudengineerskills.com/posts/azure-functions-terraform/)
