# Virtual Network for Container Apps and Private Endpoints
resource "azurerm_virtual_network" "vnet" {
  count               = var.enable_networking ? 1 : 0
  name                = "vnet-${local.web_app_name_prefix}"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  address_space       = [var.vnet_address_prefix]

  tags = local.common_tags
}

# Subnet for Container Apps infrastructure
# Note: For workload profiles-based Container Apps Environment, do NOT use delegation
resource "azurerm_subnet" "container_apps" {
  count                = var.enable_networking ? 1 : 0
  name                 = "containerapps-infra"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet[0].name
  address_prefixes     = [var.container_apps_subnet_prefix]

  # Container App Environments require the infrastructure subnet to be
  # delegated to Microsoft.App/environments, otherwise creation fails with
  # ManagedEnvironmentSubnetDelegationError (400).
  delegation {
    name = "Microsoft.App.environments"
    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

# Subnet for Private Endpoints
resource "azurerm_subnet" "private_endpoints" {
  count                             = var.enable_networking ? 1 : 0
  name                              = "private-endpoints"
  resource_group_name               = azurerm_resource_group.rg.name
  virtual_network_name              = azurerm_virtual_network.vnet[0].name
  address_prefixes                  = [var.private_endpoint_subnet_prefix]
  private_endpoint_network_policies = "Disabled"
}

# ============================================================================
# Private DNS Zone for Cosmos DB
# ============================================================================

resource "azurerm_private_dns_zone" "cosmos" {
  count               = var.enable_private_endpoint ? 1 : 0
  name                = "privatelink.documents.azure.com"
  resource_group_name = azurerm_resource_group.rg.name

  tags = local.common_tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "cosmos" {
  count                 = var.enable_private_endpoint ? 1 : 0
  name                  = "cosmos-dns-link"
  resource_group_name   = azurerm_resource_group.rg.name
  private_dns_zone_name = azurerm_private_dns_zone.cosmos[0].name
  virtual_network_id    = azurerm_virtual_network.vnet[0].id
  registration_enabled  = false

  tags = local.common_tags
}

# ============================================================================
# Private Endpoint for Cosmos DB
# ============================================================================

resource "azurerm_private_endpoint" "cosmos" {
  count               = var.enable_private_endpoint ? 1 : 0
  name                = "pe-cosmos-${local.web_app_name_prefix}"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.private_endpoints[0].id

  private_service_connection {
    name                           = "cosmos-privateserviceconnection"
    private_connection_resource_id = azurerm_cosmosdb_account.main.id
    is_manual_connection           = false
    subresource_names              = ["Sql"]
  }

  private_dns_zone_group {
    name                 = "cosmos-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.cosmos[0].id]
  }

  tags = local.common_tags
}

# ============================================================================
# Private DNS Zone for Azure OpenAI
# ============================================================================

resource "azurerm_private_dns_zone" "openai" {
  count               = var.enable_private_endpoint ? 1 : 0
  name                = "privatelink.openai.azure.com"
  resource_group_name = azurerm_resource_group.rg.name

  tags = local.common_tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "openai" {
  count                 = var.enable_private_endpoint ? 1 : 0
  name                  = "openai-dns-link"
  resource_group_name   = azurerm_resource_group.rg.name
  private_dns_zone_name = azurerm_private_dns_zone.openai[0].name
  virtual_network_id    = azurerm_virtual_network.vnet[0].id
  registration_enabled  = false

  tags = local.common_tags
}

# ============================================================================
# Private Endpoint for Azure OpenAI
# ============================================================================

resource "azurerm_private_endpoint" "openai" {
  count               = var.enable_private_endpoint ? 1 : 0
  name                = "pe-openai-${local.web_app_name_prefix}"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  subnet_id           = azurerm_subnet.private_endpoints[0].id

  private_service_connection {
    name                           = "openai-privateserviceconnection"
    private_connection_resource_id = azurerm_ai_services.ai_hub.id
    is_manual_connection           = false
    subresource_names              = ["account"]
  }

  private_dns_zone_group {
    name                 = "openai-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.openai[0].id]
  }

  tags = local.common_tags
}
