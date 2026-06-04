#!/bin/bash
# Post-deployment: create Office 365 OnNewEmail connector trigger configuration
# pointing at the Inbox Triage agent function, then walk the operator through
# OAuth consent for the Office 365 Outlook connection.
#
# Prereq: the `connector-namespace` Azure CLI extension. Install once with:
#   az extension add --source <connector_namespace-*.whl URL from
#                              https://github.com/Azure/Connectors/releases>

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}Configuring Office 365 connector trigger...${NC}"

if ! command -v jq >/dev/null 2>&1; then
  echo -e "${RED}Error: jq is required. Please install jq.${NC}" >&2
  exit 1
fi

outputs=$(azd env get-values --output json)
resourceGroup=$(echo "$outputs" | jq -r '.RESOURCE_GROUP')
functionAppName=$(echo "$outputs" | jq -r '.AZURE_FUNCTION_APP_NAME')
connectorGateway=$(echo "$outputs" | jq -r '.CONNECTOR_GATEWAY_NAME')
outlookConnection=$(echo "$outputs" | jq -r '.OUTLOOK_CONNECTION_NAME')

if [[ -z "$resourceGroup" || -z "$functionAppName" || -z "$connectorGateway" || -z "$outlookConnection" ]]; then
  echo -e "${RED}ERROR: required azd outputs missing. Run 'azd provision' first.${NC}" >&2
  exit 1
fi

if ! az extension show --name connector-namespace --query name -o tsv >/dev/null 2>&1; then
  echo -e "${RED}ERROR: 'connector-namespace' Azure CLI extension is not installed.${NC}" >&2
  echo -e "${RED}       Download the latest 'connector_namespace-*.whl' from${NC}" >&2
  echo -e "${RED}       https://github.com/Azure/Connectors/releases and run:${NC}" >&2
  echo -e "${RED}         az extension add --source <wheel-url-or-path>${NC}" >&2
  echo -e "${RED}       Then re-run: azd hooks run postdeploy${NC}" >&2
  exit 2
fi

echo -e "${CYAN}Fetching connector_extension system key for ${functionAppName}...${NC}"
connectorKey=$(az functionapp keys list -g "$resourceGroup" -n "$functionAppName" \
  --query "systemKeys.connector_extension" -o tsv 2>/dev/null || echo "")

if [[ -z "$connectorKey" ]]; then
  echo -e "${RED}ERROR: connector_extension system key not found on ${functionAppName}.${NC}" >&2
  echo -e "${RED}       The function host must start once with the connector-triggered agent before the key is created.${NC}" >&2
  echo -e "${RED}       Wait for first deployment to start the host, then re-run: azd hooks run postdeploy${NC}" >&2
  exit 3
fi

functionName="inbox_triage"
operationName="OnNewEmailV3"
triggerName="${outlookConnection}-onnewemail"
callbackUrl="https://${functionAppName}.azurewebsites.net/runtime/webhooks/connector?functionName=${functionName}&code=${connectorKey}"

connectionDetails=$(jq -nc --arg conn "$outlookConnection" \
  '{connectorName:"office365", connectionName:$conn}')
notificationDetails=$(jq -nc --arg url "$callbackUrl" \
  '{callbackUrl:$url, httpMethod:"Post"}')
parameters='[{"name":"folderPath","value":"Inbox"}]'

echo -e "${YELLOW}Creating trigger '${triggerName}' for ${operationName} -> ${functionName}...${NC}"
az connector-namespace trigger delete \
  -g "$resourceGroup" --namespace "$connectorGateway" \
  -n "$triggerName" --yes >/dev/null 2>&1 || true

az connector-namespace trigger create \
  -g "$resourceGroup" \
  --namespace "$connectorGateway" \
  -n "$triggerName" \
  --connection-details "$connectionDetails" \
  --operation-name "$operationName" \
  --parameters "$parameters" \
  --notification-details "$notificationDetails" \
  --state "Enabled" \
  --description "Office 365 OnNewEmailV3 -> inbox_triage" >/dev/null

echo -e "${GREEN}✅ Trigger config created.${NC}"
echo ""
echo -e "${CYAN}Authorizing connector connections so the trigger can fire...${NC}"
"$(dirname "$0")/authorize-connectors.sh"
echo ""
echo -e "${CYAN}Send yourself an email to trigger the Inbox Triage agent.${NC}"
