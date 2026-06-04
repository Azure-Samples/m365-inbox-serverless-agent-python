$ErrorActionPreference = "Stop"

if (-not (Test-Path ".\local.settings.json")) {
    $output = azd env get-values

    foreach ($line in $output) {
        if ($line -match "^PROJECT_ENDPOINT") { $AIProjectEndpoint = ($line -split "=", 2)[1] -replace '"','' }
        if ($line -match "^STORAGE_CONNECTION__queueServiceUri") { $StorageConnectionQueue = ($line -split "=", 2)[1] -replace '"','' }
        if ($line -match "^MODEL_DEPLOYMENT_NAME") { $ModelDeploymentName = ($line -split "=", 2)[1] -replace '"','' }
        if ($line -match "^AZURE_OPENAI_ENDPOINT") { $AzureOpenAIEndpoint = ($line -split "=", 2)[1] -replace '"','' }
        if ($line -match "^MAILBOX_OWNER_EMAIL") { $MailboxOwnerEmail = ($line -split "=", 2)[1] -replace '"','' }
        if ($line -match "^OUTLOOK_MCP_ENDPOINT") { $OutlookMcpEndpoint = ($line -split "=", 2)[1] -replace '"','' }
        if ($line -match "^TEAMS_MCP_ENDPOINT") { $TeamsMcpEndpoint = ($line -split "=", 2)[1] -replace '"','' }
    }

    @{
        IsEncrypted = $false
        Values = @{
            AzureWebJobsStorage = "UseDevelopmentStorage=true"
            FUNCTIONS_WORKER_RUNTIME = "python"
            AZURE_FUNCTIONS_AGENTS_PROVIDER = "foundry"
            AZURE_AI_PROJECT_ENDPOINT = "$AIProjectEndpoint"
            FOUNDRY_PROJECT_ENDPOINT = "$AIProjectEndpoint"
            MODEL_DEPLOYMENT_NAME = "$ModelDeploymentName"
            AZURE_AI_MODEL_DEPLOYMENT_NAME = "$ModelDeploymentName"
            AZURE_OPENAI_ENDPOINT = "$AzureOpenAIEndpoint"
            AZURE_OPENAI_DEPLOYMENT_NAME = "$ModelDeploymentName"
            STORAGE_CONNECTION__queueServiceUri = "$StorageConnectionQueue"
            MAILBOX_OWNER_EMAIL = "$MailboxOwnerEmail"
            OUTLOOK_MCP_ENDPOINT = "$OutlookMcpEndpoint"
            TEAMS_MCP_ENDPOINT = "$TeamsMcpEndpoint"
        }
    } | ConvertTo-Json | Out-File -FilePath ".\local.settings.json" -Encoding ascii
}
