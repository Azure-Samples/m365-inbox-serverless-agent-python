#!/bin/bash
set -euo pipefail

if [ ! -f "./local.settings.json" ]; then
    output=$(azd env get-values)

    AIProjectEndpoint=""
    StorageConnectionQueue=""
    ModelDeploymentName=""
    AzureOpenAIEndpoint=""
    MailboxOwnerEmail=""
    OutlookMcpEndpoint=""
    TeamsMcpEndpoint=""

    while IFS= read -r line; do
        case "$line" in
            PROJECT_ENDPOINT*) AIProjectEndpoint=$(echo "$line" | cut -d '=' -f 2- | tr -d '"') ;;
            STORAGE_CONNECTION__queueServiceUri*) StorageConnectionQueue=$(echo "$line" | cut -d '=' -f 2- | tr -d '"') ;;
            MODEL_DEPLOYMENT_NAME*) ModelDeploymentName=$(echo "$line" | cut -d '=' -f 2- | tr -d '"') ;;
            AZURE_OPENAI_ENDPOINT*) AzureOpenAIEndpoint=$(echo "$line" | cut -d '=' -f 2- | tr -d '"') ;;
            MAILBOX_OWNER_EMAIL*) MailboxOwnerEmail=$(echo "$line" | cut -d '=' -f 2- | tr -d '"') ;;
            OUTLOOK_MCP_ENDPOINT*) OutlookMcpEndpoint=$(echo "$line" | cut -d '=' -f 2- | tr -d '"') ;;
            TEAMS_MCP_ENDPOINT*) TeamsMcpEndpoint=$(echo "$line" | cut -d '=' -f 2- | tr -d '"') ;;
        esac
    done <<< "$output"

    cat <<EOF_SETTINGS > ./local.settings.json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AZURE_FUNCTIONS_AGENTS_PROVIDER": "foundry",
    "AZURE_AI_PROJECT_ENDPOINT": "$AIProjectEndpoint",
    "FOUNDRY_PROJECT_ENDPOINT": "$AIProjectEndpoint",
    "MODEL_DEPLOYMENT_NAME": "$ModelDeploymentName",
    "AZURE_AI_MODEL_DEPLOYMENT_NAME": "$ModelDeploymentName",
    "AZURE_OPENAI_ENDPOINT": "$AzureOpenAIEndpoint",
    "AZURE_OPENAI_DEPLOYMENT_NAME": "$ModelDeploymentName",
    "STORAGE_CONNECTION__queueServiceUri": "$StorageConnectionQueue",
    "MAILBOX_OWNER_EMAIL": "$MailboxOwnerEmail",
    "OUTLOOK_MCP_ENDPOINT": "$OutlookMcpEndpoint",
    "TEAMS_MCP_ENDPOINT": "$TeamsMcpEndpoint"
  }
}
EOF_SETTINGS
fi
