param connectorGatewayName string
param outlookConnectionName string = 'office365-outlook'
param teamsConnectionName string = 'microsoft-teams'
param outlookMcpServerConfigName string = 'outlook-inbox-agent'
param teamsMcpServerConfigName string = 'teams-inbox-agent'
param location string = resourceGroup().location
param tags object = {}
param managedIdentityPrincipalId string
param deployerPrincipalId string = ''
param tenantId string
param enableTeamsConnector bool = true

resource connectorGateway 'Microsoft.Web/connectorGateways@2026-05-01-preview' = {
  name: connectorGatewayName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {}
}

resource outlookConnection 'Microsoft.Web/connectorGateways/connections@2026-05-01-preview' = {
  parent: connectorGateway
  name: outlookConnectionName
  properties: {
    connectorName: 'office365'
    displayName: 'Office 365 Outlook Connection'
  }
}

resource teamsConnection 'Microsoft.Web/connectorGateways/connections@2026-05-01-preview' = if (enableTeamsConnector) {
  parent: connectorGateway
  name: teamsConnectionName
  properties: {
    connectorName: 'teams'
    displayName: 'Microsoft Teams Connection'
  }
}

resource outlookConnectionAccessPolicy 'Microsoft.Web/connectorGateways/connections/accessPolicies@2026-05-01-preview' = {
  parent: outlookConnection
  name: managedIdentityPrincipalId
  properties: {
    principal: {
      type: 'ActiveDirectory'
      identity: {
        objectId: managedIdentityPrincipalId
        tenantId: tenantId
      }
    }
  }
}

resource outlookConnectionDeployerAccessPolicy 'Microsoft.Web/connectorGateways/connections/accessPolicies@2026-05-01-preview' = if (!empty(deployerPrincipalId)) {
  parent: outlookConnection
  name: deployerPrincipalId
  properties: {
    principal: {
      type: 'ActiveDirectory'
      identity: {
        objectId: deployerPrincipalId
        tenantId: tenantId
      }
    }
  }
}

resource teamsConnectionAccessPolicy 'Microsoft.Web/connectorGateways/connections/accessPolicies@2026-05-01-preview' = if (enableTeamsConnector) {
  parent: teamsConnection
  name: managedIdentityPrincipalId
  properties: {
    principal: {
      type: 'ActiveDirectory'
      identity: {
        objectId: managedIdentityPrincipalId
        tenantId: tenantId
      }
    }
  }
}

resource teamsConnectionDeployerAccessPolicy 'Microsoft.Web/connectorGateways/connections/accessPolicies@2026-05-01-preview' = if (enableTeamsConnector && !empty(deployerPrincipalId)) {
  parent: teamsConnection
  name: deployerPrincipalId
  properties: {
    principal: {
      type: 'ActiveDirectory'
      identity: {
        objectId: deployerPrincipalId
        tenantId: tenantId
      }
    }
  }
}

resource outlookMcpServerConfig 'Microsoft.Web/connectorGateways/mcpserverconfigs@2026-05-01-preview' = {
  parent: connectorGateway
  name: outlookMcpServerConfigName
  properties: {
    state: 'Enabled'
    description: 'Office 365 Outlook actions for the Microsoft 365 inbox triage agent.'
    connectors: [
      {
        name: 'office365'
        connectionName: outlookConnection.name
        displayName: 'Office 365 Outlook'
        description: 'Send triage summaries and follow-ups from Outlook.'
        operations: [
          {
            name: 'SendEmailV2'
            displayName: 'Send an email'
            description: 'Sends an email message.'
            userParameters: []
            agentParameters: [
              {
                name: 'emailMessage'
                schema: {
                  type: 'object'
                  properties: {
                    To: {
                      type: 'string'
                      format: 'email'
                      description: 'Email recipient addresses separated by semicolons.'
                      required: true
                    }
                    Subject: {
                      type: 'string'
                      description: 'Email subject.'
                      required: true
                    }
                    Body: {
                      type: 'string'
                      format: 'html'
                      description: 'Email body as HTML.'
                      required: true
                    }
                  }
                }
              }
            ]
          }
        ]
      }
    ]
    policies: []
    settings: {
      textOnlyContent: true
    }
  }
}

resource teamsMcpServerConfig 'Microsoft.Web/connectorGateways/mcpserverconfigs@2026-05-01-preview' = if (enableTeamsConnector) {
  parent: connectorGateway
  name: teamsMcpServerConfigName
  properties: {
    state: 'Enabled'
    description: 'Microsoft Teams actions for the Microsoft 365 inbox triage agent.'
    connectors: [
      {
        name: 'teams'
        connectionName: teamsConnection.name
        displayName: 'Microsoft Teams'
        description: 'Post triage summaries to a selected Teams channel.'
        operations: [
          {
            name: 'PostMessageToConversation'
            displayName: 'Post message in a chat or channel'
            description: 'Posts a message to a Microsoft Teams chat or channel.'
            userParameters: []
            agentParameters: [
              {
                name: 'message'
                schema: {
                  type: 'object'
                  properties: {
                    poster: {
                      type: 'string'
                      description: 'Who posts the message. Use Flow bot unless you intentionally use another supported value.'
                      required: true
                    }
                    location: {
                      type: 'string'
                      description: 'Message destination type, such as Channel.'
                      required: true
                    }
                    body: {
                      type: 'object'
                      description: 'Teams message payload including recipient and content.'
                      required: true
                    }
                  }
                }
              }
            ]
          }
        ]
      }
    ]
    policies: []
    settings: {
      textOnlyContent: true
    }
  }
}

output connectorGatewayName string = connectorGateway.name
output outlookConnectionId string = outlookConnection.id
output teamsConnectionId string = enableTeamsConnector ? teamsConnection.id : ''
output outlookMcpEndpoint string = outlookMcpServerConfig.properties.mcpEndpointUrl
output teamsMcpEndpoint string = enableTeamsConnector ? teamsMcpServerConfig!.properties.mcpEndpointUrl : ''
output outlookConnectionAccessPolicyId string = outlookConnectionAccessPolicy.id
output teamsConnectionAccessPolicyId string = enableTeamsConnector ? teamsConnectionAccessPolicy.id : ''
