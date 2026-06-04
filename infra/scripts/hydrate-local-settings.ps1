#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Hydrate local.settings.json from `azd env get-values`.

.DESCRIPTION
  Run AFTER `azd provision` so the Foundry endpoint + model deployment exist.
  Auth uses your `az login` identity via DefaultAzureCredential -- no keys.

  Invoke with `pwsh -File ./scripts/hydrate-local-settings.ps1` to avoid the
  Windows ExecutionPolicy prompt (no policy change needed).
#>
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

if (-not (Get-Command azd -ErrorAction SilentlyContinue)) {
    throw "azd not found. Install: https://aka.ms/azd-install"
}

# Parse `azd env get-values` (KEY="value" per line) into a hashtable
$envVars = @{}
foreach ($line in (azd env get-values)) {
    if ($line -match '^([^=]+)="(.*)"$') {
        $envVars[$Matches[1]] = $Matches[2]
    }
}

if (-not $envVars['FOUNDRY_PROJECT_ENDPOINT']) {
    throw "FOUNDRY_PROJECT_ENDPOINT missing in azd env -- did 'azd provision' succeed?"
}
if (-not $envVars['FOUNDRY_MODEL']) {
    throw "FOUNDRY_MODEL missing in azd env"
}

$settings = [ordered]@{
    IsEncrypted = $false
    Values = [ordered]@{
        AzureWebJobsStorage              = 'UseDevelopmentStorage=true'
        FUNCTIONS_WORKER_RUNTIME         = 'python'

        AZURE_FUNCTIONS_AGENTS_PROVIDER  = 'foundry'
        FOUNDRY_PROJECT_ENDPOINT         = $envVars['FOUNDRY_PROJECT_ENDPOINT']
        FOUNDRY_MODEL                    = $envVars['FOUNDRY_MODEL']

        MAILBOX_OWNER_EMAIL                         = ($envVars['MAILBOX_OWNER_EMAIL']            ?? '<your-mailbox@example.com>')
        OUTLOOK_MCP_ENDPOINT             = ($envVars['OUTLOOK_MCP_ENDPOINT'] ?? '')
        TEAMS_MCP_ENDPOINT               = ($envVars['TEAMS_MCP_ENDPOINT']   ?? '')
        TEAMS_TEAM_ID                    = ($envVars['TEAMS_TEAM_ID']        ?? '')
        TEAMS_CHANNEL_ID                 = ($envVars['TEAMS_CHANNEL_ID']     ?? '')
    }
}

$settings | ConvertTo-Json -Depth 5 | Set-Content -Path local.settings.json -Encoding UTF8
Write-Host "Wrote local.settings.json -- provider=foundry, model=$($envVars['FOUNDRY_MODEL'])"
Write-Host "Run 'func start' to start the host."
