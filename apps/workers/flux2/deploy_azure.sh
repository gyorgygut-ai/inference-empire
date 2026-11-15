#!/usr/bin/env bash
set -euo pipefail

: "${SECRET_HUGGINGFACE_TOKEN:?SECRET_HUGGINGFACE_TOKEN is required}"
: "${SECRET_R2_ACCESS_KEY:?SECRET_R2_ACCESS_KEY is required}"
: "${SECRET_R2_SECRET_KEY:?SECRET_R2_SECRET_KEY is required}"
: "${SECRET_R2_ENDPOINT:?SECRET_R2_ENDPOINT is required}"
: "${SECRET_R2_BUCKET:?SECRET_R2_BUCKET is required}"

command -v az >/dev/null || { echo "Azure CLI (az) is required" >&2; exit 1; }
az account show >/dev/null

resource_group="worker-flux2"
location="eastus"
environment="worker-flux2-env"
app="worker-flux2"
subscription_id="$(az account show --query id -o tsv | tr -d '-')"
suffix="${subscription_id:0:12}"
registry="wflux2${suffix}"
storage="wflux2cache${suffix}"
share="flux2-model-cache"
registry_server="${registry}.azurecr.io"
image="${registry_server}/${app}:latest"

az group create --name "$resource_group" --location "$location" --output none
az acr create --resource-group "$resource_group" --name "$registry" --sku Basic --admin-enabled true --output none
az storage account create \
  --resource-group "$resource_group" \
  --name "$storage" \
  --location "$location" \
  --sku Standard_LRS \
  --kind StorageV2 \
  --output none

storage_key="$(az storage account keys list --resource-group "$resource_group" --account-name "$storage" --query '[0].value' -o tsv)"
az storage share create --account-name "$storage" --account-key "$storage_key" --name "$share" --output none

if ! az containerapp env show --resource-group "$resource_group" --name "$environment" >/dev/null 2>&1; then
  az containerapp env create \
    --resource-group "$resource_group" \
    --name "$environment" \
    --location "$location" \
    --output none
fi

profile_count="$(az containerapp env workload-profile list \
  --resource-group "$resource_group" \
  --name "$environment" \
  --query "[?name=='NC8as-T4'] | length(@)" -o tsv)"
if [[ "$profile_count" == "0" ]]; then
  az containerapp env workload-profile add \
    --resource-group "$resource_group" \
    --name "$environment" \
    --workload-profile-name NC8as-T4 \
    --workload-profile-type Consumption-GPU-NC8as-T4 \
    --min-nodes 0 \
    --max-nodes 1 \
    --output none
fi

az containerapp env storage set \
  --resource-group "$resource_group" \
  --name "$environment" \
  --storage-name flux2modelcache \
  --storage-type AzureFile \
  --azure-file-account-name "$storage" \
  --azure-file-account-key "$storage_key" \
  --azure-file-share-name "$share" \
  --access-mode ReadWrite \
  --output none

az acr build --registry "$registry" --image "$image" --file Dockerfile .

registry_user="$(az acr credential show --name "$registry" --query username -o tsv)"
registry_password="$(az acr credential show --name "$registry" --query 'passwords[0].value' -o tsv)"
environment_id="$(az containerapp env show --resource-group "$resource_group" --name "$environment" --query id -o tsv)"
manifest="$(mktemp)"
trap 'rm -f "$manifest"' EXIT
chmod 600 "$manifest"
MANIFEST_PATH="$manifest" \
ENVIRONMENT_ID="$environment_id" \
REGISTRY_SERVER="$registry_server" \
REGISTRY_USER="$registry_user" \
REGISTRY_PASSWORD="$registry_password" \
IMAGE="$image" \
python3 - <<'PY'
import json
import os

manifest = {
    "properties": {
        "managedEnvironmentId": os.environ["ENVIRONMENT_ID"],
        "configuration": {
            "activeRevisionsMode": "Single",
            "ingress": {"external": True, "targetPort": 8080, "transport": "auto"},
            "registries": [{
                "server": os.environ["REGISTRY_SERVER"],
                "username": os.environ["REGISTRY_USER"],
                "passwordSecretRef": "registry-password",
            }],
            "secrets": [
                {"name": "registry-password", "value": os.environ["REGISTRY_PASSWORD"]},
                {"name": "huggingface-token", "value": os.environ["SECRET_HUGGINGFACE_TOKEN"]},
                {"name": "r2-access-key", "value": os.environ["SECRET_R2_ACCESS_KEY"]},
                {"name": "r2-secret-key", "value": os.environ["SECRET_R2_SECRET_KEY"]},
                {"name": "r2-endpoint", "value": os.environ["SECRET_R2_ENDPOINT"]},
                {"name": "r2-bucket", "value": os.environ["SECRET_R2_BUCKET"]},
            ],
        },
        "template": {
            "containers": [{
                "name": "worker-flux2",
                "image": os.environ["IMAGE"],
                "resources": {"cpu": 8, "memory": "56Gi"},
                "env": [
                    {"name": "SECRET_HUGGINGFACE_TOKEN", "secretRef": "huggingface-token"},
                    {"name": "SECRET_R2_ACCESS_KEY", "secretRef": "r2-access-key"},
                    {"name": "SECRET_R2_SECRET_KEY", "secretRef": "r2-secret-key"},
                    {"name": "SECRET_R2_ENDPOINT", "secretRef": "r2-endpoint"},
                    {"name": "SECRET_R2_BUCKET", "secretRef": "r2-bucket"},
                    {"name": "FLUX2_MODEL_CACHE_DIR", "value": "/mnt/flux2-cache"},
                ],
                "volumeMounts": [{"volumeName": "flux2-cache", "mountPath": "/mnt/flux2-cache"}],
            }],
            "scale": {
                "minReplicas": 0,
                "maxReplicas": 1,
                "rules": [{"name": "http-requests", "http": {"metadata": {"concurrentRequests": "1"}}}],
            },
            "volumes": [{"name": "flux2-cache", "storageType": "AzureFile", "storageName": "flux2modelcache"}],
        },
    }
}
with open(os.environ["MANIFEST_PATH"], "w", encoding="utf-8") as output:
    json.dump(manifest, output)
PY

if az containerapp show --resource-group "$resource_group" --name "$app" >/dev/null 2>&1; then
  az containerapp update --resource-group "$resource_group" --name "$app" --yaml "$manifest" --workload-profile-name NC8as-T4 --output none
else
  az containerapp create --resource-group "$resource_group" --name "$app" --yaml "$manifest" --workload-profile-name NC8as-T4 --output none
fi

fqdn="$(az containerapp show --resource-group "$resource_group" --name "$app" --query properties.configuration.ingress.fqdn -o tsv)"
printf 'Deployed %s at https://%s/generate\n' "$app" "$fqdn"
