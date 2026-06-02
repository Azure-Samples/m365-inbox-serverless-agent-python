$ErrorActionPreference = "Stop"

$output = azd env get-values
foreach ($line in $output) {
    if ($line -match "^STORAGE_ACCOUNT_NAME") { $StorageAccount = ($line -split "=", 2)[1] -replace '"','' }
    if ($line -match "^RESOURCE_GROUP") { $ResourceGroup = ($line -split "=", 2)[1] -replace '"','' }
}

$ConfigFolder = ($ResourceGroup -split '-' | Select-Object -Skip 1) -join '-'
$configFile = ".azure\$ConfigFolder\config.json"
$vnetDisabled = $true

if (Test-Path $configFile) {
    $jsonContent = Get-Content -Path $configFile -Raw | ConvertFrom-Json
    if ($jsonContent.infra.parameters.PSObject.Properties.Name -contains "skipVnet") {
        $vnetDisabled = $jsonContent.infra.parameters.skipVnet -eq $true
    } elseif ($jsonContent.infra.parameters.PSObject.Properties.Name -contains "vnetEnabled") {
        $vnetDisabled = $jsonContent.infra.parameters.vnetEnabled -eq $false
    }
} else {
    Write-Output "Config file $configFile not found. Assuming VNet is not enabled."
}

if ($vnetDisabled) {
    Write-Output "VNet is not enabled. Skipping adding the client IP to the network rule of the Azure Functions storage account."
} else {
    Write-Output "VNet is enabled. Adding the client IP to the network rule of the Azure Functions storage account."
    $ClientIP = Invoke-RestMethod -Uri 'https://api.ipify.org'
    az storage account update --name $StorageAccount --resource-group $ResourceGroup --public-network-access Enabled | Out-Null
    az storage account network-rule add --resource-group $ResourceGroup --account-name $StorageAccount --ip-address $ClientIP | Out-Null
    Write-Output "Client IP $ClientIP added to the network rule of the Azure Functions storage account."
}
