#!/usr/bin/env bash
# Hydrate local.settings.json from `azd env get-values`.
# Run AFTER `azd provision` so the Foundry endpoint + model deployment exist.
# Auth uses your `az login` identity via DefaultAzureCredential — no keys.
set -euo pipefail

if ! command -v azd >/dev/null 2>&1; then
  echo "ERROR: azd not found. Install: https://aka.ms/azd-install" >&2
  exit 1
fi

if ! azd env list --output json | grep -q '"Name"'; then
  echo "ERROR: no azd environment. Run 'azd provision' first." >&2
  exit 1
fi

# Pull all values into shell vars
eval "$(azd env get-values)"

: "${FOUNDRY_PROJECT_ENDPOINT:?FOUNDRY_PROJECT_ENDPOINT missing in azd env — did 'azd provision' succeed?}"
: "${FOUNDRY_MODEL:?FOUNDRY_MODEL missing in azd env}"

cat > local.settings.json << EOF
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",

    "AZURE_FUNCTIONS_AGENTS_PROVIDER": "foundry",
    "FOUNDRY_PROJECT_ENDPOINT": "${FOUNDRY_PROJECT_ENDPOINT}",
    "FOUNDRY_MODEL": "${FOUNDRY_MODEL}",

    "TO_EMAIL": "${TO_EMAIL:-you@example.com}",
    "OUTLOOK_MCP_ENDPOINT": "${OUTLOOK_MCP_ENDPOINT:-}",
    "TEAMS_MCP_ENDPOINT": "${TEAMS_MCP_ENDPOINT:-}",
    "TEAMS_TEAM_ID": "${TEAMS_TEAM_ID:-}",
    "TEAMS_CHANNEL_ID": "${TEAMS_CHANNEL_ID:-}"
  }
}
EOF

chmod 600 local.settings.json
echo "Wrote local.settings.json — provider=foundry, model=${FOUNDRY_MODEL}"
echo "Run 'func5 run' to start the host."
