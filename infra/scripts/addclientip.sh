#!/bin/bash
set -euo pipefail

output=$(azd env get-values)

StorageAccount=""
ResourceGroup=""
while IFS= read -r line; do
    if [[ $line == STORAGE_ACCOUNT_NAME* ]]; then
        StorageAccount=$(echo "$line" | cut -d'=' -f2- | tr -d '"')
    elif [[ $line == RESOURCE_GROUP* ]]; then
        ResourceGroup=$(echo "$line" | cut -d'=' -f2- | tr -d '"')
    fi
done <<< "$output"

ConfigFolder=$(echo "$ResourceGroup" | cut -d'-' -f2-)
configFile=".azure/$ConfigFolder/config.json"

vnetDisabled=false
if [[ -f "$configFile" ]]; then
    jsonContent=$(cat "$configFile")
    if echo "$jsonContent" | grep -q '"skipVnet"'; then
        skipVnet=$(echo "$jsonContent" | grep '"skipVnet"' | sed 's/.*"skipVnet":\s*\([^,}]*\).*/\1/' | tr -d ' ')
        if echo "$skipVnet" | grep -iq "true"; then
            vnetDisabled=true
        fi
    elif echo "$jsonContent" | grep -q '"vnetEnabled"'; then
        vnetEnabled=$(echo "$jsonContent" | grep '"vnetEnabled"' | sed 's/.*"vnetEnabled":\s*\([^,}]*\).*/\1/' | tr -d ' ')
        if echo "$vnetEnabled" | grep -iq "false"; then
            vnetDisabled=true
        fi
    fi
else
    echo "Config file $configFile not found. Assuming VNet is not enabled."
    vnetDisabled=true
fi

if [ "$vnetDisabled" = true ]; then
    echo "VNet is not enabled. Skipping adding the client IP to the network rule of the Azure Functions storage account."
else
    echo "VNet is enabled. Adding the client IP to the network rule of the Azure Functions storage account."
    ClientIP=$(curl -s https://api.ipify.org)
    az storage account update --name "$StorageAccount" --resource-group "$ResourceGroup" --public-network-access Enabled > /dev/null
    az storage account network-rule add --resource-group "$ResourceGroup" --account-name "$StorageAccount" --ip-address "$ClientIP" > /dev/null
    echo "Client IP $ClientIP added to the network rule of the Azure Functions storage account."
fi
