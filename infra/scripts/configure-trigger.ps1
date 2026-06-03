# Post-deployment: create Office 365 OnNewEmail connector trigger configuration
# pointing at the Inbox Triage agent function, then walk the operator through
# OAuth consent for the Office 365 Outlook connection.
#
# Prereq: the `connector-namespace` Azure CLI extension. Install once with:
#   az extension add --source <connector_namespace-*.whl URL from
#                              https://github.com/Azure/Connectors/releases>

$ErrorActionPreference = "Stop"

Write-Host "Configuring Office 365 connector trigger..." -ForegroundColor Yellow

$outputs = azd env get-values --output json | ConvertFrom-Json
$resourceGroup    = $outputs.RESOURCE_GROUP
$functionAppName  = $outputs.AZURE_FUNCTION_APP_NAME
$connectorGateway = $outputs.CONNECTOR_GATEWAY_NAME
$outlookConnection = $outputs.OUTLOOK_CONNECTION_NAME
$teamsConnection   = $outputs.TEAMS_CONNECTION_NAME

if (-not $resourceGroup -or -not $functionAppName -or -not $connectorGateway -or -not $outlookConnection) {
    Write-Host "ERROR: required azd outputs missing. Run 'azd provision' first." -ForegroundColor Red
    exit 1
}

$ext = az extension show --name connector-namespace --query name -o tsv 2>$null
if (-not $ext) {
    Write-Host "ERROR: 'connector-namespace' Azure CLI extension is not installed." -ForegroundColor Red
    Write-Host "       Download the latest 'connector_namespace-*.whl' from"          -ForegroundColor Red
    Write-Host "       https://github.com/Azure/Connectors/releases and run:"          -ForegroundColor Red
    Write-Host "         az extension add --source <wheel-url-or-path>"                -ForegroundColor Red
    Write-Host "       Then re-run: azd hooks run postdeploy"                          -ForegroundColor Red
    exit 2
}

Write-Host "Fetching connector_extension system key for $functionAppName..." -ForegroundColor Cyan
$connectorKey = az functionapp keys list -g $resourceGroup -n $functionAppName --query "systemKeys.connector_extension" -o tsv
if (-not $connectorKey) {
    Write-Host "ERROR: connector_extension system key not found on $functionAppName." -ForegroundColor Red
    Write-Host "       The function host must start once with the connector-triggered agent before the key is created." -ForegroundColor Red
    Write-Host "       Wait for first deployment to start the host, then re-run: azd hooks run postdeploy" -ForegroundColor Red
    exit 3
}

$functionName  = "inbox_triage"
$operationName = "OnNewEmailV3"
$triggerName   = "$outlookConnection-onnewemail"
$callbackUrl   = "https://$functionAppName.azurewebsites.net/runtime/webhooks/connector?functionName=$functionName&code=$connectorKey"

$connectionDetails  = (@{ connectorName = "office365"; connectionName = $outlookConnection } | ConvertTo-Json -Compress)
$notificationDetails = (@{ callbackUrl = $callbackUrl; httpMethod = "Post" } | ConvertTo-Json -Compress)
$parameters = '[{"name":"folderPath","value":"Inbox"}]'

Write-Host "Creating trigger '$triggerName' for $operationName -> $functionName..." -ForegroundColor Yellow
az connector-namespace trigger delete -g $resourceGroup --namespace $connectorGateway -n $triggerName --yes 2>$null | Out-Null

az connector-namespace trigger create `
    -g $resourceGroup `
    --namespace $connectorGateway `
    -n $triggerName `
    --connection-details $connectionDetails `
    --operation-name $operationName `
    --parameters $parameters `
    --notification-details $notificationDetails `
    --state "Enabled" `
    --description "Office 365 OnNewEmailV3 -> inbox_triage" | Out-Null

Write-Host "✅ Trigger config created." -ForegroundColor Green

function Authorize-Connection {
    param([string]$ConnectionName, [string]$Description)

    Write-Host "-> Authorizing $Description ($ConnectionName)..." -ForegroundColor Cyan
    $status = az connector-namespace connection show -g $resourceGroup --namespace $connectorGateway -n $ConnectionName --query "properties.overallStatus" -o tsv 2>$null
    if ($status -and $status.ToLower() -eq "connected") {
        Write-Host "   already Connected; skipping consent." -ForegroundColor Green
        return
    }

    $params = '[{"parameterName":"token","redirectUrl":"https://portal.azure.com"}]'
    $consentJson = az connector-namespace connection list-consent-links -g $resourceGroup --namespace $connectorGateway --connection-name $ConnectionName --parameters $params -o json 2>$null | ConvertFrom-Json
    $link = $consentJson.value[0].link
    if (-not $link) {
        Write-Host "   could not get consent link; skipping." -ForegroundColor Red
        return
    }
    Write-Host "   opening browser for OAuth consent..." -ForegroundColor Cyan
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
    Write-Host "   timed out (5 min). Re-run: azd hooks run postdeploy" -ForegroundColor Yellow
}

Authorize-Connection -ConnectionName $outlookConnection -Description "Office 365 Outlook"
if ($teamsConnection) {
    Authorize-Connection -ConnectionName $teamsConnection -Description "Microsoft Teams"
}

Write-Host ""
Write-Host "✅ Connector trigger configuration complete." -ForegroundColor Green
Write-Host "Send yourself an email to trigger the Inbox Triage agent." -ForegroundColor Cyan
