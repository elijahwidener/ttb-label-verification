// TTB Label Verification — infrastructure.
// Provisions: Azure Static Web App (Standard), Azure Database for PostgreSQL
// Flexible Server (Burstable B1ms), Azure Blob Storage (quarantine + labels
// containers, lifecycle policies, browser-upload CORS).
//
// Deploy:
//   az group create -n ttb-rg -l centralus
//   az deployment group create -g ttb-rg -f infra/main.bicep \
//     --parameters postgresAdminPassword='<strong-password>'

@description('Region for all resources. SWA supports a limited region set; centralus works for everything here.')
param location string = 'centralus'

@description('Short prefix for resource names.')
param namePrefix string = 'ttb'

@description('PostgreSQL admin login name.')
param postgresAdminLogin string = 'ttbadmin'

@secure()
@description('PostgreSQL admin password.')
param postgresAdminPassword string

@description('Extra origins allowed to PUT directly to blob storage (browser SAS uploads).')
param extraCorsOrigins array = [
  'https://elijahwf.com'
  'https://www.elijahwf.com'
  'http://localhost:5173'
]

var suffix = uniqueString(resourceGroup().id)
var storageAccountName = toLower('${namePrefix}st${suffix}') // <= 24 chars
var swaName = '${namePrefix}-swa-${suffix}'
var pgServerName = '${namePrefix}-pg-${suffix}'

// ---------------------------------------------------------------- Static Web App
resource swa 'Microsoft.Web/staticSites@2023-12-01' = {
  name: swaName
  location: location
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    allowConfigFileUpdates: true
    stagingEnvironmentPolicy: 'Enabled'
  }
}

// ---------------------------------------------------------------- Storage
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    cors: {
      corsRules: [
        {
          // Browser uploads go straight to the quarantine container with a
          // short-lived write-only SAS, so the storage account must allow the
          // page origins (Vercel proxy origin + SWA origin + local dev).
          allowedOrigins: concat(extraCorsOrigins, [ 'https://${swa.properties.defaultHostname}' ])
          allowedMethods: [ 'PUT', 'GET', 'HEAD', 'OPTIONS' ]
          allowedHeaders: [ '*' ]
          exposedHeaders: [ '*' ]
          maxAgeInSeconds: 3600
        }
      ]
    }
  }
}

resource quarantineContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'quarantine'
  properties: {
    publicAccess: 'None'
  }
}

resource labelsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: 'labels'
  properties: {
    publicAccess: 'None'
  }
}

// Lifecycle policies are the belt-and-suspenders backstop. Azure lifecycle
// granularity is daily, so quarantine's "1 hour" TTL from the design is
// enforced primarily by application logic (the API deletes quarantine blobs
// synchronously); the 1-day rule here catches anything orphaned.
resource lifecycle 'Microsoft.Storage/storageAccounts/managementPolicies@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    policy: {
      rules: [
        {
          enabled: true
          name: 'quarantine-ttl'
          type: 'Lifecycle'
          definition: {
            filters: {
              blobTypes: [ 'blockBlob' ]
              prefixMatch: [ 'quarantine/' ]
            }
            actions: {
              baseBlob: {
                delete: {
                  daysAfterModificationGreaterThan: 1
                }
              }
            }
          }
        }
        {
          enabled: true
          name: 'labels-ttl'
          type: 'Lifecycle'
          definition: {
            filters: {
              blobTypes: [ 'blockBlob' ]
              prefixMatch: [ 'labels/' ]
            }
            actions: {
              baseBlob: {
                delete: {
                  daysAfterModificationGreaterThan: 30
                }
              }
            }
          }
        }
      ]
    }
  }
}

// ---------------------------------------------------------------- PostgreSQL
resource pg 'Microsoft.DBforPostgreSQL/flexibleServers@2023-12-01-preview' = {
  name: pgServerName
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: postgresAdminLogin
    administratorLoginPassword: postgresAdminPassword
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

// Allow connections from Azure services (Static Web Apps managed functions
// have no fixed outbound IPs). SSL is still required; password auth only.
resource pgAllowAzure 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-12-01-preview' = {
  parent: pg
  name: 'AllowAllAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource pgDatabase 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-12-01-preview' = {
  parent: pg
  name: 'ttb'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// ---------------------------------------------------------------- Outputs
output staticWebAppName string = swa.name
output staticWebAppHostname string = swa.properties.defaultHostname
output storageAccountName string = storage.name
output postgresServerFqdn string = pg.properties.fullyQualifiedDomainName
output postgresUrlTemplate string = 'postgresql://${postgresAdminLogin}:<PASSWORD>@${pg.properties.fullyQualifiedDomainName}:5432/ttb?sslmode=require'
