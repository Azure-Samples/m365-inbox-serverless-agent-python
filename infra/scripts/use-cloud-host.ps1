# Dot-source (do not run) this file:
#   . ./infra/scripts/use-cloud-host.ps1
# It sets $env:AGENT_URL + $env:FUNCTION_KEY so `uv run python chat.py` calls
# the deployed Function App in Azure instead of the local Functions host
# (skips needing `azurite` + `uv run func start` in two extra terminals).

$ErrorActionPreference = "Stop"

$uri = azd env get-value SERVICE_API_URI 2>$null
if (-not $uri) { Write-Error "no azd env — run 'azd up' first"; return }
$rg = azd env get-value RESOURCE_GROUP 2>$null
if (-not $rg) { Write-Error "RESOURCE_GROUP not in azd env"; return }
$app = azd env get-value AZURE_FUNCTION_APP_NAME 2>$null
if (-not $app) { Write-Error "AZURE_FUNCTION_APP_NAME not in azd env"; return }

$key = az functionapp keys list -g $rg -n $app --query functionKeys.default -o tsv 2>$null
if (-not $key) { Write-Error "could not fetch function key — try 'az login'"; return }

$env:AGENT_URL = $uri
$env:FUNCTION_KEY = $key
Write-Host "AGENT_URL=$uri"
$tail = $key.Substring([Math]::Max(0, $key.Length - 4))
Write-Host "FUNCTION_KEY=***$tail"
Write-Host "chat.py will now call the deployed Function App ($app)."
