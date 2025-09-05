TF_DIR=terraform
FUNC_DIR=function

.PHONY: prepare init plan apply output publish destroy all info hostname routes storage-website set-route-prefix

prepare:
	cd $(TF_DIR) && [ -f terraform.tfvars ] || cp terraform.tfvars.example terraform.tfvars

init:
	cd $(TF_DIR) && terraform init

plan:
	cd $(TF_DIR) && terraform plan

apply:
	cd $(TF_DIR) && terraform apply -auto-approve

output:
	cd $(TF_DIR) && terraform output

publish:
	cd $(TF_DIR) && FUNCTION_APP_NAME=$$(terraform output -raw function_app_name) && \
	if [ -n "$(ROUTE_PREFIX)" ]; then \
	  TMP_FILE=$$(mktemp) && \
	  jq '.extensions.http.routePrefix = "$(ROUTE_PREFIX)"' ../$(FUNC_DIR)/host.json > $$TMP_FILE && \
	  mv $$TMP_FILE ../$(FUNC_DIR)/host.json; \
	fi && \
	cd ../$(FUNC_DIR) && func azure functionapp publish $$FUNCTION_APP_NAME --build remote --no-interactive | cat

destroy:
	cd $(TF_DIR) && terraform destroy -auto-approve

all: prepare init plan apply publish output

# -------- Post-deploy helpers --------
info:
	cd $(TF_DIR) && \
	APP=$$(terraform output -raw function_app_name) && \
	RG=$$(terraform output -raw resource_group_name) && \
	az functionapp show --name $$APP --resource-group $$RG --query "possibleOutboundIpAddresses" -o tsv | cat

hostname:
	cd $(TF_DIR) && \
	APP=$$(terraform output -raw function_app_name) && \
	RG=$$(terraform output -raw resource_group_name) && \
	az functionapp show --name $$APP --resource-group $$RG --query "defaultHostName" -o tsv | cat

routes:
	cd $(TF_DIR) && \
	APP=$$(terraform output -raw function_app_name) && \
	RG=$$(terraform output -raw resource_group_name) && \
	ROUTE_PREFIX=$$(jq -r .extensions.http.routePrefix ../$(FUNC_DIR)/host.json) && \
	HOSTNAME=$$(az functionapp show --name $$APP --resource-group $$RG --query defaultHostName -o tsv) && \
	az functionapp function list --name $$APP --resource-group $$RG --query "[?config.bindings[?type=='httpTrigger']].{name:name, route:config.bindings[?type=='httpTrigger'].route | [0]}" -o tsv | \
	while IFS=$$'\t' read -r name route; do \
	  if [ -z "$$route" ]; then route="$$name"; fi; \
	  echo "Function: $$name"; \
	  echo "Route: $$route"; \
	  echo "URL: https://$$HOSTNAME/$$ROUTE_PREFIX/$$route"; \
	  echo; \
	done | cat

storage-website:
	cd $(TF_DIR) && \
	RG=$$(terraform output -raw resource_group_name) && \
	LOC=$$(terraform output -raw location) && \
	STORAGE_NAME="$(STORAGE_NAME)"; \
	if [ -z "$$STORAGE_NAME" ]; then STORAGE_NAME="static$$(openssl rand -hex 4)"; fi; \
	az storage account create --name "$$STORAGE_NAME" --resource-group "$$RG" --location "$$LOC" --sku Standard_LRS --kind StorageV2 | cat && \
	az storage blob service-properties update --account-name "$$STORAGE_NAME" --static-website | cat && \
	az storage account show --name "$$STORAGE_NAME" --query primaryEndpoints.web -o tsv | cat

set-route-prefix:
	@if [ -z "$(ROUTE_PREFIX)" ]; then echo "ROUTE_PREFIX is required" >&2; exit 1; fi
	TMP_FILE=$$(mktemp) && jq '.extensions.http.routePrefix = "$(ROUTE_PREFIX)"' function/host.json > $$TMP_FILE && mv $$TMP_FILE function/host.json && cat function/host.json | cat

