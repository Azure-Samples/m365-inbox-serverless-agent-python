param aiProjectPrincipalId string
param aiProjectPrincipalType string = 'ServicePrincipal'
param userPrincipalId string = ''
param allowUserIdentityPrincipal bool = true

param aiServicesName string
param aiSearchName string
param aiCosmosDbName string
param aiStorageAccountName string

param integrationStorageAccountName string

param functionAppManagedIdentityPrincipalId string = ''
param allowFunctionAppIdentityPrincipal bool = true

param enableAzureSearch bool = false
param enableCosmosDb bool = false

// Assignments for AI Services

resource aiServices 'Microsoft.CognitiveServices/accounts@2024-06-01-preview' existing = {
  name: aiServicesName
}

var cognitiveServicesContributorRoleDefinitionId = '25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68'

resource cognitiveServicesContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01'= {
  scope: aiServices
  name: guid(aiServices.id, cognitiveServicesContributorRoleDefinitionId, aiProjectPrincipalId)
  properties: {  
    principalId: aiProjectPrincipalId
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesContributorRoleDefinitionId)
    principalType: aiProjectPrincipalType
  }
}

var cognitiveServicesOpenAIUserRoleDefinitionId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource cognitiveServicesOpenAIUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: aiServices
  name: guid(aiProjectPrincipalId, cognitiveServicesOpenAIUserRoleDefinitionId, aiServices.id)
  properties: {
    principalId: aiProjectPrincipalId
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleDefinitionId)
    principalType: aiProjectPrincipalType
  }
}

var cognitiveServicesUserRoleDefinitionId = 'a97b65f3-24c7-4388-baec-2e87135dc908'

resource cognitiveServicesUserRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: aiServices
  name: guid(aiProjectPrincipalId, cognitiveServicesUserRoleDefinitionId, aiServices.id)
  properties: {
    principalId: aiProjectPrincipalId
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUserRoleDefinitionId)
    principalType: aiProjectPrincipalType
  }
}

resource cognitiveServicesContributorAssignmentUser 'Microsoft.Authorization/roleAssignments@2022-04-01'= if (allowUserIdentityPrincipal && !empty(userPrincipalId)) {
  scope: aiServices
  name: guid(aiServices.id, cognitiveServicesContributorRoleDefinitionId, userPrincipalId)
  properties: {  
    principalId: userPrincipalId
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesContributorRoleDefinitionId)
    principalType: 'User'
  }
}

resource cognitiveServicesOpenAIUserRoleAssignmentUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (allowUserIdentityPrincipal && !empty(userPrincipalId)){
  scope: aiServices
  name: guid(userPrincipalId, cognitiveServicesOpenAIUserRoleDefinitionId, aiServices.id)
  properties: {
    principalId: userPrincipalId
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleDefinitionId)
    principalType: 'User'
  }
}

resource cognitiveServicesUserRoleAssignmentUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (allowUserIdentityPrincipal && !empty(userPrincipalId)){
  scope: aiServices
  name: guid(userPrincipalId, cognitiveServicesUserRoleDefinitionId, aiServices.id)
  properties: {
    principalId: userPrincipalId
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUserRoleDefinitionId)
    principalType: 'User'
  }
}

// Assignments for AI Search Service

resource aiSearchService 'Microsoft.Search/searchServices@2024-06-01-preview' existing = if (enableAzureSearch) {
  name: aiSearchName
}

var searchIndexDataContributorRoleDefinitionId = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
var searchServiceContributorRoleDefinitionId = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'

resource searchIndexDataContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableAzureSearch) {
  scope: aiSearchService
  name: guid(aiProjectPrincipalId, searchIndexDataContributorRoleDefinitionId, aiSearchService.id)
  properties: {
    principalId: aiProjectPrincipalId
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataContributorRoleDefinitionId)
    principalType: aiProjectPrincipalType
  }
}

resource searchServiceContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableAzureSearch) {
  scope: aiSearchService
  name: guid(aiProjectPrincipalId, searchServiceContributorRoleDefinitionId, aiSearchService.id)
  properties: {
    principalId: aiProjectPrincipalId
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', searchServiceContributorRoleDefinitionId)
    principalType: aiProjectPrincipalType
  }
}

// Assignments for AI Storage Account

resource aiStorageAccount 'Microsoft.Storage/storageAccounts@2024-01-01' existing = {
  name: aiStorageAccountName 
}

var storageBlobDataContributorRoleDefinitionId = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'

resource storageBlobDataContributorRoleAssignmentProject 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: aiStorageAccount
  name: guid(aiProjectPrincipalId, storageBlobDataContributorRoleDefinitionId, aiStorageAccount.id)
  properties: {
    principalId: aiProjectPrincipalId
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRoleDefinitionId)
    principalType: aiProjectPrincipalType
  }
}

// Assignments for Cosmos DB

resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2024-12-01-preview' existing = if (enableCosmosDb) {
  name: aiCosmosDbName
}

var cosmosDbOperatorRoleDefinitionId = '230815da-be43-4aae-9cb4-875f7bd000aa'

resource cosmosDbOperatorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (enableCosmosDb) {
  scope: cosmosDbAccount
  name: guid(aiProjectPrincipalId, cosmosDbOperatorRoleDefinitionId, cosmosDbAccount.id)
  properties: {
    principalId: aiProjectPrincipalId
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', cosmosDbOperatorRoleDefinitionId)
    principalType: aiProjectPrincipalType
  }
}

// Assignments for Integration Storage Account

resource integrationStorageAccount 'Microsoft.Storage/storageAccounts@2024-01-01' existing = {
  name: integrationStorageAccountName 
}

var storageQueueDataContributorRoleDefinitionId  = '974c5e8b-45b9-4653-ba55-5f855dd0fb88'

resource storageQueueDataContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(integrationStorageAccount.id, aiProjectPrincipalId, storageQueueDataContributorRoleDefinitionId)
  scope: integrationStorageAccount
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', storageQueueDataContributorRoleDefinitionId)
    principalId: aiProjectPrincipalId
    principalType: aiProjectPrincipalType
  }
}

resource storageQueueDataContributorRoleAssignmentUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (allowUserIdentityPrincipal && !empty(userPrincipalId)) {
  name: guid(integrationStorageAccount.id, userPrincipalId, storageQueueDataContributorRoleDefinitionId)
  scope: integrationStorageAccount
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', storageQueueDataContributorRoleDefinitionId)
    principalId: userPrincipalId
    principalType: 'User'
  }
}

// Function App Managed Identity assignments

resource cognitiveServicesContributorAssignmentFunctionApp 'Microsoft.Authorization/roleAssignments@2022-04-01'= if (allowFunctionAppIdentityPrincipal && !empty(functionAppManagedIdentityPrincipalId)) {
  scope: aiServices
  name: guid(aiServices.id, cognitiveServicesContributorRoleDefinitionId, functionAppManagedIdentityPrincipalId)
  properties: {  
    principalId: functionAppManagedIdentityPrincipalId
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesContributorRoleDefinitionId)
    principalType: 'ServicePrincipal'
  }
}

resource cognitiveServicesOpenAIUserRoleAssignmentFunctionApp 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (allowFunctionAppIdentityPrincipal && !empty(functionAppManagedIdentityPrincipalId)) {
  scope: aiServices
  name: guid(functionAppManagedIdentityPrincipalId, cognitiveServicesOpenAIUserRoleDefinitionId, aiServices.id)
  properties: {
    principalId: functionAppManagedIdentityPrincipalId
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAIUserRoleDefinitionId)
    principalType: 'ServicePrincipal'
  }
}

resource cognitiveServicesUserRoleAssignmentFunctionApp 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (allowFunctionAppIdentityPrincipal && !empty(functionAppManagedIdentityPrincipalId)) {
  scope: aiServices
  name: guid(functionAppManagedIdentityPrincipalId, cognitiveServicesUserRoleDefinitionId, aiServices.id)
  properties: {
    principalId: functionAppManagedIdentityPrincipalId
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesUserRoleDefinitionId)
    principalType: 'ServicePrincipal'
  }
}
