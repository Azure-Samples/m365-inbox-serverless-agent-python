// Creates Azure dependent resources for Azure AI studio

@description('Azure region of the deployment')
param location string = resourceGroup().location

@description('Tags to add to the resources')
param tags object = {}

@description('AI services name')
param aiServicesName string

@description('The name of the AI Search resource')
param aiSearchName string

@description('Enable Azure AI Search resource creation')
param enableAzureSearch bool = false

@description('The name of the Cosmos DB account')
param cosmosDbName string

@description('Enable Cosmos DB resource creation')
param enableCosmosDb bool = false

@description('Name of the storage account')
param storageName string

@description('Model name for deployment')
param modelName string 

@description('Model format for deployment')
param modelFormat string 

@description('Model version for deployment')
param modelVersion string 

@description('Model deployment SKU name')
param modelSkuName string 

@description('Model deployment capacity')
param modelCapacity int 

@description('Name for the model deployment in Azure AI Services')
param modelDeploymentName string = 'chat'

@description('Model/AI Resource deployment location')
param modelLocation string 

@description('The AI Service Account full ARM Resource ID. This is an optional field, and if not provided, the resource will be created.')
param aiServiceAccountResourceId string

@description('The AI Search Service full ARM Resource ID. This is an optional field, and if not provided, the resource will be created.')
param aiSearchServiceResourceId string 

@description('The AI Storage Account full ARM Resource ID. This is an optional field, and if not provided, the resource will be created.')
param aiStorageAccountResourceId string 

@description('The AI Cosmos DB Account full ARM Resource ID. This is an optional field, and if not provided, the resource will be created.')
param aiCosmosDbAccountResourceId string

var aiServiceExists = aiServiceAccountResourceId != ''
var skipAzureSearchCreation = aiSearchServiceResourceId != '' || !enableAzureSearch
var aiStorageExists = aiStorageAccountResourceId != ''
var skipCosmosDbCreation = aiCosmosDbAccountResourceId != '' || !enableCosmosDb

resource aiServices 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' = if(!aiServiceExists) {
  name: aiServicesName
  location: modelLocation
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    allowProjectManagement: true
    customSubDomainName: toLower('${(aiServicesName)}')
    networkAcls: {
      defaultAction: 'Allow'
      virtualNetworkRules: []
      ipRules: []
    }    
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true
  }
}
resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-04-01-preview'= if(!aiServiceExists){
  parent: aiServices
  name: modelDeploymentName
  sku : {
    capacity: modelCapacity
    name: modelSkuName
  }
  properties: {
    model:{
      name: modelName
      format: modelFormat
      version: modelVersion
    }
  }
}

resource aiSearch 'Microsoft.Search/searchServices@2024-06-01-preview' = if(!skipAzureSearchCreation) {
  name: aiSearchName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    disableLocalAuth: true
    encryptionWithCmk: {
      enforcement: 'Unspecified'
    }
    hostingMode: 'default'
    partitionCount: 1
    publicNetworkAccess: 'enabled'
    replicaCount: 1
    semanticSearch: 'disabled'
  }
  sku: {
    name: 'standard'
  }
}

param sku string = 'Standard_LRS'

resource storage 'Microsoft.Storage/storageAccounts@2022-05-01' = if(!aiStorageExists) {
  name: storageName
  location: location
  kind: 'StorageV2'
  sku: {
    name: sku
  }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Allow'
      virtualNetworkRules: []
    }
    allowSharedKeyAccess: false
  }
}

var canaryRegions = ['eastus2euap', 'centraluseuap']
var cosmosDbRegion = contains(canaryRegions, location) ? 'eastus2' : location
resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' = if(!skipCosmosDbCreation) {
  name: cosmosDbName
  location: cosmosDbRegion
  kind: 'GlobalDocumentDB'
  properties: {
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    disableLocalAuth: true
    enableAutomaticFailover: false
    enableMultipleWriteLocations: false
    enableFreeTier: false
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    databaseAccountOfferType: 'Standard'
  }
}

// Outputs

output aiServicesName string = aiServicesName
output aiservicesID string = aiServices.id
output aiServiceAccountResourceGroupName string = resourceGroup().name
output aiServiceAccountSubscriptionId string = subscription().subscriptionId 

output aiSearchName string = aiSearchName  
output aisearchID string = !skipAzureSearchCreation ? aiSearch.id : aiSearchServiceResourceId
output aiSearchServiceResourceGroupName string = !skipAzureSearchCreation ? resourceGroup().name : ''
output aiSearchServiceSubscriptionId string = !skipAzureSearchCreation ? subscription().subscriptionId : ''

output storageAccountName string = storageName
output storageId string = !aiStorageExists ? storage.id : aiStorageAccountResourceId
output storageAccountResourceGroupName string = !aiStorageExists ? resourceGroup().name : ''
output storageAccountSubscriptionId string = !aiStorageExists ? subscription().subscriptionId : ''

output cosmosDbAccountName string = cosmosDbName
output cosmosDbAccountId string = !skipCosmosDbCreation ? cosmosDbAccount.id : aiCosmosDbAccountResourceId
output cosmosDbAccountResourceGroupName string = !skipCosmosDbCreation ? resourceGroup().name : ''
output cosmosDbAccountSubscriptionId string = !skipCosmosDbCreation ? subscription().subscriptionId : ''
