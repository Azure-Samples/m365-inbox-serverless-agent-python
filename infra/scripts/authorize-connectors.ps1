# One-time OAuth consent for the Office 365 Outlook (and optional Teams) MCP
# connections created by `azd provision`. Opens a browser tab for each
# connection and polls until the connector namespace reports `Connected`.
#
# Safe to re-run: already-authorized connections are skipped.
# Works without a deployed function app. Runs against the connector namespace
# directly so local `uv run func start` can call real MCP tools.
#
# Prereq: the `connector-namespace` Azure CLI extension. Install once with:
#   az extension add --source <connector_namespace-*.whl URL from
#                              https://github.com/Azure/Connectors/releases>

$ErrorActionPreference = "Stop"

$outputs = azd env get-values --output json | ConvertFrom-Json
$resourceGroup     = $outputs.RESOURCE_GROUP
$connectorGateway  = $outputs.CONNECTOR_GATEWAY_NAME
$outlookConnection = $outputs.OUTLOOK_CONNECTION_NAME
$teamsConnection   = $outputs.TEAMS_CONNECTION_NAME

if (-not $resourceGroup -or -not $connectorGateway -or -not $outlookConnection) {
    Write-Host "ERROR: required azd outputs missing. Run 'azd provision' first." -ForegroundColor Red
    exit 1
}

$ext = az extension show --name connector-namespace --query name -o tsv 2>$null
if (-not $ext) {
    Write-Host "ERROR: 'connector-namespace' Azure CLI extension is not installed." -ForegroundColor Red
    Write-Host "       Download the latest 'connector_namespace-*.whl' from"          -ForegroundColor Red
    Write-Host "       https://github.com/Azure/Connectors/releases and run:"          -ForegroundColor Red
    Write-Host "         az extension add --source <wheel-url-or-path>"                -ForegroundColor Red
    exit 2
}

function Authorize-Connection {
    param([string]$ConnectionName, [string]$Description)

    Write-Host "-> Authorizing $Description ($ConnectionName)..." -ForegroundColor Cyan
    $status = az connector-namespace connection show -g $resourceGroup --namespace $connectorGateway -n $ConnectionName --query "properties.overallStatus" -o tsv 2>$null
    if ($status -and $status.ToLower() -eq "connected") {
        Write-Host "   already Connected; skipping consent." -ForegroundColor Green
        return
    }

    $params = '[{"parameterName":"token","redirectUrl":"https://portal.azure.com"}]'
    $paramsFile = New-TemporaryFile
    Set-Content -Path $paramsFile -Value $params -Encoding ascii
    try {
        $consentJson = az connector-namespace connection list-consent-links -g $resourceGroup --namespace $connectorGateway --connection-name $ConnectionName --parameters "@$($paramsFile.FullName)" -o json 2>$null | ConvertFrom-Json
    } finally {
        Remove-Item $paramsFile -ErrorAction SilentlyContinue
    }
    $link = $consentJson.value[0].link
    if (-not $link) {
        Write-Host "   could not get consent link; skipping." -ForegroundColor Red
        return
    }
    Write-Host "   opening browser for OAuth consent..." -ForegroundColor Cyan
    Write-Host "   (if no tab opens, paste this URL manually)" -ForegroundColor Cyan
    Write-Host "   $link" -ForegroundColor Cyan
    Start-Process $link

    $deadline = (Get-Date).AddSeconds(300)
    $last = ""
    while ((Get-Date) -lt $deadline) {
        $status = az connector-namespace connection show -g $resourceGroup --namespace $connectorGateway -n $ConnectionName --query "properties.overallStatus" -o tsv 2>$null
        if ($status -ne $last) {
            Write-Host "   status: $status" -ForegroundColor Cyan
            $last = $status
        }
        if ($status -and $status.ToLower() -eq "connected") {
            Write-Host "   ✓ $ConnectionName authenticated" -ForegroundColor Green
            return
        }
        Start-Sleep -Seconds 3
    }
    Write-Host "   timed out (5 min). Re-run: ./infra/scripts/authorize-connectors.ps1" -ForegroundColor Yellow
}

Authorize-Connection -ConnectionName $outlookConnection -Description "Office 365 Outlook"
if ($teamsConnection) {
    Authorize-Connection -ConnectionName $teamsConnection -Description "Microsoft Teams"
}

Write-Host ""
Write-Host "✅ Connectors authorized." -ForegroundColor Green
Write-Host "You can now run all three agents locally via 'uv run python chat.py'." -ForegroundColor Cyan
