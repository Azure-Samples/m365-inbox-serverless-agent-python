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

$connectionDetails  = @{ connectorName = "office365"; connectionName = $outlookConnection } | ConvertTo-Json -Compress
$notificationDetails = @{ callbackUrl = $callbackUrl; httpMethod = "Post" } | ConvertTo-Json -Compress
$parameters = '[{"name":"folderPath","value":"Inbox"}]'

Write-Host "Creating trigger '$triggerName' for $operationName -> $functionName..." -ForegroundColor Yellow
az connector-namespace trigger delete -g $resourceGroup --namespace $connectorGateway -n $triggerName --yes 2>$null | Out-Null

$connectionDetailsFile  = New-TemporaryFile
$notificationDetailsFile = New-TemporaryFile
$parametersFile = New-TemporaryFile
try {
    Set-Content -Path $connectionDetailsFile -Value $connectionDetails -Encoding ascii
    Set-Content -Path $notificationDetailsFile -Value $notificationDetails -Encoding ascii
    Set-Content -Path $parametersFile -Value $parameters -Encoding ascii

    az connector-namespace trigger create `
        -g $resourceGroup `
        --namespace $connectorGateway `
        -n $triggerName `
        --connection-details "@$($connectionDetailsFile.FullName)" `
        --operation-name $operationName `
        --parameters "@$($parametersFile.FullName)" `
        --notification-details "@$($notificationDetailsFile.FullName)" `
        --state "Enabled" `
        --description "Office 365 OnNewEmailV3 -> inbox_triage" | Out-Null

    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
} finally {
    Remove-Item $connectionDetailsFile, $notificationDetailsFile, $parametersFile -ErrorAction SilentlyContinue
}

Write-Host "✅ Trigger config created." -ForegroundColor Green
Write-Host ""
Write-Host "Authorizing connector connections so the trigger can fire..." -ForegroundColor Cyan
& "$PSScriptRoot/authorize-connectors.ps1"
Write-Host ""
Write-Host "Send yourself an email to trigger the Inbox Triage agent." -ForegroundColor Cyan
