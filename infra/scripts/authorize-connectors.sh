#!/bin/bash
# One-time OAuth consent for the Office 365 Outlook (and optional Teams) MCP
# connections created by `azd provision`. Opens a browser tab for each
# connection and polls until the connector namespace reports `Connected`.
#
# Safe to re-run: already-authorized connections are skipped.
# Works without a deployed function app. Runs against the connector namespace
# directly so local `uv run func5 start` can call real MCP tools.
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

if ! command -v jq >/dev/null 2>&1; then
  echo -e "${RED}Error: jq is required. Please install jq.${NC}" >&2
  exit 1
fi

outputs=$(azd env get-values --output json)
resourceGroup=$(echo "$outputs" | jq -r '.RESOURCE_GROUP')
connectorGateway=$(echo "$outputs" | jq -r '.CONNECTOR_GATEWAY_NAME')
outlookConnection=$(echo "$outputs" | jq -r '.OUTLOOK_CONNECTION_NAME')
teamsConnection=$(echo "$outputs" | jq -r '.TEAMS_CONNECTION_NAME // ""')

if [[ -z "$resourceGroup" || -z "$connectorGateway" || -z "$outlookConnection" ]]; then
  echo -e "${RED}ERROR: required azd outputs missing. Run 'azd provision' first.${NC}" >&2
  exit 1
fi

if ! az extension show --name connector-namespace --query name -o tsv >/dev/null 2>&1; then
  echo -e "${RED}ERROR: 'connector-namespace' Azure CLI extension is not installed.${NC}" >&2
  echo -e "${RED}       Download the latest 'connector_namespace-*.whl' from${NC}" >&2
  echo -e "${RED}       https://github.com/Azure/Connectors/releases and run:${NC}" >&2
  echo -e "${RED}         az extension add --source <wheel-url-or-path>${NC}" >&2
  exit 2
fi

open_url() {
  local url="$1"
  if command -v open >/dev/null 2>&1; then open "$url" >/dev/null 2>&1 || true
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$url" >/dev/null 2>&1 || true
  elif command -v wslview >/dev/null 2>&1; then wslview "$url" >/dev/null 2>&1 || true
  fi
}

authorize() {
  local connectionName="$1" description="$2"
  echo -e "${CYAN}-> Authorizing ${description} (${connectionName})...${NC}"
  local status
  status=$(az connector-namespace connection show -g "$resourceGroup" \
    --namespace "$connectorGateway" -n "$connectionName" \
    --query "properties.overallStatus" -o tsv 2>/dev/null || echo "")
  if [[ "$(echo "$status" | tr '[:upper:]' '[:lower:]')" == "connected" ]]; then
    echo -e "${GREEN}   already Connected; skipping consent.${NC}"
    return
  fi

  local params consentJson link
  params='[{"parameterName":"token","redirectUrl":"https://portal.azure.com"}]'
  consentJson=$(az connector-namespace connection list-consent-links \
    -g "$resourceGroup" --namespace "$connectorGateway" \
    --connection-name "$connectionName" --parameters "$params" -o json 2>/dev/null || echo "")
  link=$(echo "$consentJson" | jq -r '.value[0].link // empty' 2>/dev/null || echo "")

  if [[ -z "$link" ]]; then
    echo -e "${RED}   could not get consent link; skipping.${NC}" >&2
    return
  fi

  echo -e "${CYAN}   opening browser for OAuth consent...${NC}"
  echo -e "${CYAN}   (if no tab opens, paste this URL manually)${NC}"
  echo -e "${CYAN}   ${link}${NC}"
  open_url "$link"

  local deadline=$(( $(date +%s) + 300 ))
  local last=""
  while [[ $(date +%s) -lt $deadline ]]; do
    status=$(az connector-namespace connection show -g "$resourceGroup" \
      --namespace "$connectorGateway" -n "$connectionName" \
      --query "properties.overallStatus" -o tsv 2>/dev/null || echo "")
    if [[ "$status" != "$last" ]]; then
      echo -e "${CYAN}   status: ${status:-?}${NC}"
      last="$status"
    fi
    if [[ "$(echo "$status" | tr '[:upper:]' '[:lower:]')" == "connected" ]]; then
      echo -e "${GREEN}   ✓ ${connectionName} authenticated${NC}"
      return
    fi
    sleep 3
  done
  echo -e "${YELLOW}   timed out (5 min). Re-run: ./infra/scripts/authorize-connectors.sh${NC}"
}

authorize "$outlookConnection" "Office 365 Outlook"
if [[ -n "$teamsConnection" && "$teamsConnection" != "null" ]]; then
  authorize "$teamsConnection" "Microsoft Teams"
fi

echo ""
echo -e "${GREEN}✅ Connectors authorized.${NC}"
echo -e "${CYAN}You can now run all three agents locally via 'uv run python chat.py'.${NC}"
