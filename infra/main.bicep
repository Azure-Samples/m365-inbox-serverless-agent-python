targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment used to generate a short unique hash for resource names.')
param environmentName string

@minLength(1)
@description('Primary location for all resources and the Flex Consumption Function App.')
@metadata({
  azd: {
    type: 'location'
  }
})
param location string

#disable-next-line no-unused-params
param vnetEnabled bool = false
param apiServiceName string = ''
param apiUserAssignedIdentityName string = ''
param applicationInsightsName string = ''
param appServicePlanName string = ''
param logAnalyticsName string = ''
param resourceGroupName string = ''
param storageAccountName string = ''

@description('Optional: Your Microsoft Entra user/service principal object ID for development access. Leave empty for production. Local development should use azd up, which sets this automatically.')
param principalId string = ''

@description('Recipient email address for inbox triage notifications. Override before deployment.')
param toEmail string = '<recipient@example.com>'

@description('Enable Connector Gateway, managed connections, and managed MCP server endpoints.')
param enableConnectors bool = true

@description('Enable Microsoft Teams connection and managed MCP server endpoint. Requires enableConnectors to be true.')
param enableTeamsConnector bool = true

@description('Connector Gateway location. Preview connector resources may have limited regional availability.')
@allowed([
  'centralus'
  'eastus'
  'eastus2'
  'northcentralus'
  'southcentralus'
  'westcentralus'
  'westus'
])
param connectorGatewayLocation string = 'westcentralus'

@description('Friendly name for your Azure AI project.')
param aiProjectFriendlyName string = 'M365 Inbox Agent Project'

@description('Description of your Azure AI project displayed in Azure AI Foundry.')
param aiProjectDescription string = 'An opinionated Microsoft 365 inbox triage agent running on Azure Functions.'

@description('Enable Azure AI Search for vector store and search capabilities.')
param enableAzureSearch bool = false

@description('Name of the Azure AI Search account.')
param aiSearchName string = 'agent-ai-search'

@description('Enable Cosmos DB for agent thread storage.')
param enableCosmosDb bool = false

@description('Name for account-level capability host.')
param accountCapabilityHostName string = 'caphostacc'

@description('Name for project-level capability host.')
param projectCapabilityHostName string = 'caphostproj'

@description('Name of the Azure AI Services account.')
param aiServicesName string = 'agent-ai-services'

@description('Model name for deployment.')
param modelName string = 'gpt-5-mini'

@description('Model format for deployment.')
param modelFormat string = 'OpenAI'

@description('Model version for deployment.')
param modelVersion string = '2025-08-07'

@description('Model deployment SKU name.')
param modelSkuName string = 'GlobalStandard'

@description('Model deployment capacity.')
param modelCapacity int = 50

@description('Name for the model deployment in Azure AI Services.')
param modelDeploymentName string = 'chat'

@description('Name of the Cosmos DB account for agent thread storage.')
param cosmosDbName string = 'agent-ai-cosmos'

@description('The AI Service Account full ARM Resource ID. If not provided, a resource is created.')
param aiServiceAccountResourceId string = ''

@description('The AI Search Service full ARM Resource ID. If not provided, a resource is created when Azure Search is enabled.')
param aiSearchServiceResourceId string = ''

@description('The AI Storage Account full ARM Resource ID. If not provided, a resource is created.')
param aiStorageAccountResourceId string = ''

@description('The Cosmos DB Account full ARM Resource ID. If not provided, a resource is created when Cosmos DB is enabled.')
param aiCosmosDbAccountResourceId string = ''

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }
var functionAppName = !empty(apiServiceName) ? apiServiceName : '${abbrs.webSitesFunctions}api-${resourceToken}'
var deploymentStorageContainerName = 'app-package-${take(functionAppName, 32)}-${take(toLower(uniqueString(functionAppName, resourceToken)), 7)}'
var uniqueSuffix = toLower(uniqueString(subscription().id, environmentName, location))
var projectName = toLower('${environmentName}${uniqueSuffix}')
var connectorGatewayName = 'cg-${resourceToken}'
var outlookConnectionName = 'office365-outlook'
var teamsConnectionName = 'teams-connection'
var outlookMcpServerConfigName = 'outlook-inbox-agent'
var teamsMcpServerConfigName = 'teams-inbox-agent'
var effectiveTeamsConnectorEnabled = enableConnectors && enableTeamsConnector
var deployerPrincipalId = !empty(principalId) ? principalId : deployer().objectId

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: !empty(resourceGroupName) ? resourceGroupName : '${abbrs.resourcesResourceGroups}${environmentName}'
  location: location
  tags: tags
}

module apiUserAssignedIdentity 'br/public:avm/res/managed-identity/user-assigned-identity:0.4.1' = {
  name: 'apiUserAssignedIdentity'
  scope: rg
  params: {
    location: location
    tags: tags
    name: !empty(apiUserAssignedIdentityName) ? apiUserAssignedIdentityName : '${abbrs.managedIdentityUserAssignedIdentities}api-${resourceToken}'
  }
}

module appServicePlan 'br/public:avm/res/web/serverfarm:0.1.1' = {
  name: 'appserviceplan'
  scope: rg
  params: {
    name: !empty(appServicePlanName) ? appServicePlanName : '${abbrs.webServerFarms}${resourceToken}'
    location: location
    tags: tags
    kind: 'FunctionApp'
    sku: {
      tier: 'FlexConsumption'
      name: 'FC1'
    }
    reserved: true
  }
}

module storage 'br/public:avm/res/storage/storage-account:0.14.3' = {
  name: 'storage'
  scope: rg
  params: {
    name: !empty(storageAccountName) ? storageAccountName : '${abbrs.storageStorageAccounts}${resourceToken}'
    location: location
    tags: tags
    kind: 'StorageV2'
    skuName: 'Standard_LRS'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
    }
    blobServices: {
      containers: [
        { name: deploymentStorageContainerName }
      ]
    }
  }
}

module monitoring 'br/public:avm/ptn/azd/monitoring:0.1.0' = {
  name: 'monitoring'
  scope: rg
  params: {
    logAnalyticsName: !empty(logAnalyticsName) ? logAnalyticsName : '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
    applicationInsightsName: !empty(applicationInsightsName) ? applicationInsightsName : '${abbrs.insightsComponents}${resourceToken}'
    applicationInsightsDashboardName: ''
    location: location
    tags: tags
  }
}

module connectors './app/connectors.bicep' = if (enableConnectors) {
  name: 'connectors'
  scope: rg
  params: {
    connectorGatewayName: connectorGatewayName
    outlookConnectionName: outlookConnectionName
    teamsConnectionName: teamsConnectionName
    outlookMcpServerConfigName: outlookMcpServerConfigName
    teamsMcpServerConfigName: teamsMcpServerConfigName
    location: connectorGatewayLocation
    tags: tags
    managedIdentityPrincipalId: apiUserAssignedIdentity.outputs.principalId
    deployerPrincipalId: deployerPrincipalId
    tenantId: tenant().tenantId
    enableTeamsConnector: enableTeamsConnector
  }
}

module api './app/api.bicep' = {
  name: 'api'
  scope: rg
  params: {
    name: functionAppName
    location: location
    tags: tags
    applicationInsightsName: monitoring.outputs.applicationInsightsName
    appServicePlanId: appServicePlan.outputs.resourceId
    runtimeName: 'python'
    runtimeVersion: '3.11'
    storageAccountName: storage.outputs.name
    deploymentStorageContainerName: deploymentStorageContainerName
    identityId: apiUserAssignedIdentity.outputs.resourceId
    identityClientId: apiUserAssignedIdentity.outputs.clientId
    enableBlob: true
    enableQueue: true
    appSettings: {
      AZURE_FUNCTIONS_AGENTS_PROVIDER: 'foundry'
      AZURE_CLIENT_ID: apiUserAssignedIdentity.outputs.clientId
      FOUNDRY_PROJECT_ENDPOINT: aiProject.outputs.projectEndpoint
      FOUNDRY_MODEL: modelDeploymentName
      TO_EMAIL: toEmail
      OUTLOOK_MCP_ENDPOINT: enableConnectors ? connectors!.outputs.outlookMcpEndpoint : ''
      TEAMS_MCP_ENDPOINT: effectiveTeamsConnectorEnabled ? connectors!.outputs.teamsMcpEndpoint : ''
    }
  }
}

module aiDependencies './agent/standard-dependent-resources.bicep' = {
  name: 'aiDeps'
  scope: rg
  params: {
    location: location
    tags: tags
    storageName: 'ai${abbrs.storageStorageAccounts}${resourceToken}'
    aiServicesName: '${aiServicesName}${uniqueSuffix}'
    aiSearchName: '${aiSearchName}${uniqueSuffix}'
    cosmosDbName: '${cosmosDbName}${uniqueSuffix}'
    enableAzureSearch: enableAzureSearch
    enableCosmosDb: enableCosmosDb
    modelName: modelName
    modelFormat: modelFormat
    modelVersion: modelVersion
    modelSkuName: modelSkuName
    modelCapacity: modelCapacity
    modelDeploymentName: modelDeploymentName
    modelLocation: location
    aiServiceAccountResourceId: aiServiceAccountResourceId
    aiSearchServiceResourceId: aiSearchServiceResourceId
    aiStorageAccountResourceId: aiStorageAccountResourceId
    aiCosmosDbAccountResourceId: aiCosmosDbAccountResourceId
  }
}

module aiProject './agent/standard-ai-project.bicep' = {
  name: 'aiProject'
  scope: rg
  params: {
    location: location
    tags: tags
    aiServicesAccountName: aiDependencies.outputs.aiServicesName
    aiProjectName: projectName
    aiProjectFriendlyName: aiProjectFriendlyName
    aiProjectDescription: aiProjectDescription
    enableAzureSearch: enableAzureSearch
    enableCosmosDb: enableCosmosDb
    cosmosDbAccountName: aiDependencies.outputs.cosmosDbAccountName
    cosmosDbAccountSubscriptionId: aiDependencies.outputs.cosmosDbAccountSubscriptionId
    cosmosDbAccountResourceGroupName: aiDependencies.outputs.cosmosDbAccountResourceGroupName
    storageAccountName: aiDependencies.outputs.storageAccountName
    storageAccountSubscriptionId: aiDependencies.outputs.storageAccountSubscriptionId
    storageAccountResourceGroupName: aiDependencies.outputs.storageAccountResourceGroupName
    aiSearchName: aiDependencies.outputs.aiSearchName
    aiSearchSubscriptionId: aiDependencies.outputs.aiSearchServiceSubscriptionId
    aiSearchResourceGroupName: aiDependencies.outputs.aiSearchServiceResourceGroupName
  }
}

module projectRoleAssignments './agent/standard-ai-project-role-assignments.bicep' = {
  name: 'aiRbac'
  scope: rg
  params: {
    aiProjectPrincipalId: aiProject.outputs.aiProjectPrincipalId
    userPrincipalId: principalId
    allowUserIdentityPrincipal: !empty(principalId)
    aiServicesName: aiDependencies.outputs.aiServicesName
    aiSearchName: aiDependencies.outputs.aiSearchName
    aiCosmosDbName: aiDependencies.outputs.cosmosDbAccountName
    aiStorageAccountName: aiDependencies.outputs.storageAccountName
    integrationStorageAccountName: storage.outputs.name
    functionAppManagedIdentityPrincipalId: apiUserAssignedIdentity.outputs.principalId
    allowFunctionAppIdentityPrincipal: true
    enableAzureSearch: enableAzureSearch
    enableCosmosDb: enableCosmosDb
  }
}

module aiProjectCapabilityHost './agent/standard-ai-project-capability-host.bicep' = if (enableAzureSearch && enableCosmosDb) {
  name: 'capabilityHost'
  scope: rg
  params: {
    aiServicesAccountName: aiDependencies.outputs.aiServicesName
    projectName: aiProject.outputs.aiProjectName
    aiSearchConnection: aiProject.outputs.aiSearchConnection
    azureStorageConnection: aiProject.outputs.azureStorageConnection
    cosmosDbConnection: aiProject.outputs.cosmosDbConnection
    accountCapHost: '${accountCapabilityHostName}${uniqueSuffix}'
    projectCapHost: '${projectCapabilityHostName}${uniqueSuffix}'
    enableAzureSearch: enableAzureSearch
    enableCosmosDb: enableCosmosDb
  }
  dependsOn: [projectRoleAssignments]
}

module postCapabilityHostCreationRoleAssignments './agent/post-capability-host-role-assignments.bicep' = if (enableAzureSearch && enableCosmosDb) {
  name: 'postCapabilityHostRbac'
  scope: rg
  params: {
    aiProjectPrincipalId: aiProject.outputs.aiProjectPrincipalId
    aiProjectWorkspaceId: aiProject.outputs.projectWorkspaceId
    aiStorageAccountName: aiDependencies.outputs.storageAccountName
    cosmosDbAccountName: aiDependencies.outputs.cosmosDbAccountName
    enableCosmosDb: enableCosmosDb
  }
  dependsOn: [aiProjectCapabilityHost]
}

var storageEndpointConfig = {
  enableBlob: true
  enableQueue: true
  enableTable: false
  allowUserIdentityPrincipal: !empty(principalId)
}

module rbac 'app/rbac.bicep' = {
  name: 'rbacAssignments'
  scope: rg
  params: {
    storageAccountName: storage.outputs.name
    appInsightsName: monitoring.outputs.applicationInsightsName
    managedIdentityPrincipalId: apiUserAssignedIdentity.outputs.principalId
    userIdentityPrincipalId: principalId
    enableBlob: storageEndpointConfig.enableBlob
    enableQueue: storageEndpointConfig.enableQueue
    enableTable: storageEndpointConfig.enableTable
    allowUserIdentityPrincipal: storageEndpointConfig.allowUserIdentityPrincipal
  }
}

output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitoring.outputs.applicationInsightsConnectionString
output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output SERVICE_API_NAME string = api.outputs.SERVICE_API_NAME
output SERVICE_API_URI string = 'https://${api.outputs.SERVICE_API_NAME}.azurewebsites.net'
output AZURE_FUNCTION_APP_NAME string = api.outputs.SERVICE_API_NAME
output RESOURCE_GROUP string = rg.name
output STORAGE_ACCOUNT_NAME string = storage.outputs.name
output AI_SERVICES_NAME string = aiDependencies.outputs.aiServicesName
output PROJECT_ENDPOINT string = aiProject.outputs.projectEndpoint
output FOUNDRY_PROJECT_ENDPOINT string = aiProject.outputs.projectEndpoint
output FOUNDRY_MODEL string = modelDeploymentName
output AZURE_CLIENT_ID string = apiUserAssignedIdentity.outputs.clientId
output STORAGE_CONNECTION__queueServiceUri string = 'https://${storage.outputs.name}.queue.${environment().suffixes.storage}'
output TO_EMAIL string = toEmail
output OUTLOOK_MCP_ENDPOINT string = enableConnectors ? connectors!.outputs.outlookMcpEndpoint : ''
output TEAMS_MCP_ENDPOINT string = effectiveTeamsConnectorEnabled ? connectors!.outputs.teamsMcpEndpoint : ''
output CONNECTOR_GATEWAY_NAME string = enableConnectors ? connectors!.outputs.connectorGatewayName : ''
