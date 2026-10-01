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

function Get-EnvValue {
    param(
        [hashtable]$Map,
        [string]$Name,
        [string]$DefaultValue
    )

    if ($Map.ContainsKey($Name) -and $null -ne $Map[$Name] -and $Map[$Name] -ne '') {
        return $Map[$Name]
    }

    return $DefaultValue
}

$values = [ordered]@{
    AzureWebJobsStorage              = 'UseDevelopmentStorage=true'
    FUNCTIONS_WORKER_RUNTIME         = 'python'

    AZURE_FUNCTIONS_AGENTS_PROVIDER  = 'foundry'
    FOUNDRY_PROJECT_ENDPOINT         = $envVars['FOUNDRY_PROJECT_ENDPOINT']
    FOUNDRY_MODEL                    = $envVars['FOUNDRY_MODEL']

    MAILBOX_OWNER_EMAIL              = (Get-EnvValue -Map $envVars -Name 'MAILBOX_OWNER_EMAIL' -DefaultValue '<your-mailbox@example.com>')
    OUTLOOK_MCP_ENDPOINT             = (Get-EnvValue -Map $envVars -Name 'OUTLOOK_MCP_ENDPOINT' -DefaultValue '')
    TEAMS_MCP_ENDPOINT               = (Get-EnvValue -Map $envVars -Name 'TEAMS_MCP_ENDPOINT' -DefaultValue '')
    TEAMS_TEAM_ID                    = (Get-EnvValue -Map $envVars -Name 'TEAMS_TEAM_ID' -DefaultValue '')
    TEAMS_CHANNEL_ID                 = (Get-EnvValue -Map $envVars -Name 'TEAMS_CHANNEL_ID' -DefaultValue '')
}

# Windows: also set the Python worker path so func picks the venv Python, not the Microsoft Store Python stub
if ($IsWindows -or [System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform([System.Runtime.InteropServices.OSPlatform]::Windows)) {
    $venvPython = Join-Path $PSScriptRoot "..\..\.venv\Scripts\python.exe" -Resolve -ErrorAction SilentlyContinue
    if ($venvPython -and (Test-Path $venvPython)) {
        $values['languageWorkers__python__defaultExecutablePath'] = $venvPython
    }
}

$settings = [ordered]@{
    IsEncrypted = $false
    Values = $values
}

$settings | ConvertTo-Json -Depth 5 | Set-Content -Path local.settings.json -Encoding UTF8
Write-Host "Wrote local.settings.json -- provider=foundry, model=$($envVars['FOUNDRY_MODEL'])"
Write-Host ""
Write-Host "Next: run these in two separate terminals from the project root:"
Write-Host "  func5 run                  # terminal A (v5 auto-starts Azurite)"
Write-Host "  uv run python chat.py      # terminal B"
