// These must be created post-capability host addition because otherwise
// the containers will not yet exist.

param aiProjectPrincipalId string
param aiProjectPrincipalType string = 'ServicePrincipal'
param aiProjectWorkspaceId string

param aiStorageAccountName string
param cosmosDbAccountName string

param enableCosmosDb bool = false

// Assignments for Storage Account containers

resource storage 'Microsoft.Storage/storageAccounts@2022-05-01' existing = {
  name: aiStorageAccountName
}

var storageBlobDataOwnerRoleDefinitionId = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
var conditionStr = '((!(ActionMatches{\'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/tags/read\'})  AND  !(ActionMatches{\'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/filter/action\'}) AND  !(ActionMatches{\'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/tags/write\'}) ) OR (@Resource[Microsoft.Storage/storageAccounts/blobServices/containers:name] StringStartsWithIgnoreCase \'${aiProjectWorkspaceId}\' AND @Resource[Microsoft.Storage/storageAccounts/blobServices/containers:name] StringLikeIgnoreCase \'*-azureml-agent\'))'

resource storageBlobDataOwnerAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: storage
  name: guid(storage.id, aiProjectPrincipalId, storageBlobDataOwnerRoleDefinitionId, aiProjectWorkspaceId)
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataOwnerRoleDefinitionId)
    principalId: aiProjectPrincipalId
    principalType: aiProjectPrincipalType
    conditionVersion: '2.0'
    condition: conditionStr
  }
}

// Assignments for CosmosDB containers

var userThreadName = '${aiProjectWorkspaceId}-thread-message-store'
var systemThreadName = '${aiProjectWorkspaceId}-system-thread-message-store'
var entityStoreName = '${aiProjectWorkspaceId}-agent-entity-store'

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-12-01-preview' existing = if (enableCosmosDb) {
  name: cosmosDbAccountName
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-12-01-preview' existing = if (enableCosmosDb) {
  parent: cosmosAccount
  name: 'enterprise_memory'
}

resource containerUserMessageStore 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-12-01-preview' existing = if (enableCosmosDb) {
  parent: database
  name: userThreadName
}

resource containerSystemMessageStore 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-12-01-preview' existing = if (enableCosmosDb) {
  parent: database
  name: systemThreadName
}

resource containerEntityStore 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-12-01-preview' existing = if (enableCosmosDb) {
  parent: database
  name: entityStoreName
}

var roleDefinitionId = enableCosmosDb ? resourceId(
  'Microsoft.DocumentDB/databaseAccounts/sqlRoleDefinitions',
  cosmosDbAccountName,
  '00000000-0000-0000-0000-000000000002'
) : ''

var scopeSystemContainer = enableCosmosDb ? '${cosmosAccount.id}/dbs/enterprise_memory/colls/${systemThreadName}' : ''
var scopeUserContainer = enableCosmosDb ? '${cosmosAccount.id}/dbs/enterprise_memory/colls/${userThreadName}' : ''
var scopeEntityContainer = enableCosmosDb ? '${cosmosAccount.id}/dbs/enterprise_memory/colls/${entityStoreName}' : ''

resource containerRoleAssignmentUserContainer 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2022-05-15' = if (enableCosmosDb) {
  parent: cosmosAccount
  name: guid(aiProjectWorkspaceId, containerUserMessageStore.id, roleDefinitionId, aiProjectPrincipalId)
  properties: {
    principalId: aiProjectPrincipalId
    roleDefinitionId: roleDefinitionId
    scope: scopeUserContainer
  }
}

resource containerRoleAssignmentSystemContainer 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2022-05-15' = if (enableCosmosDb) {
  parent: cosmosAccount
  name: guid(aiProjectWorkspaceId, containerSystemMessageStore.id, roleDefinitionId, aiProjectPrincipalId)
  properties: {
    principalId: aiProjectPrincipalId
    roleDefinitionId: roleDefinitionId
    scope: scopeSystemContainer
  }
}

resource containerRoleAssignmentEntityContainer 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2022-05-15' = if (enableCosmosDb) {
  parent: cosmosAccount
  name: guid(aiProjectWorkspaceId, containerEntityStore.id, roleDefinitionId, aiProjectPrincipalId)
  properties: {
    principalId: aiProjectPrincipalId
    roleDefinitionId: roleDefinitionId
    scope: scopeEntityContainer
  }
}
