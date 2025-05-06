#!/bin/bash  
  
# Variables (change as needed)  
RESOURCE_GROUP="rg-openaiworkshop"  
LOCATION="westus" # Choose your preferred Azure region  
CONTAINER_REGISTRY="mcpbackendregistry"  
CONTAINER_ENVIRONMENT="mcp-backend-env"  
IMAGE_NAME="mcp-backend:latest"  
APP_NAME="mcp-backend-service"  
APP_PORT=8000  
  
# Create resource group  
az group create --name $RESOURCE_GROUP --location $LOCATION  
  
# Create container registry  
az acr create --resource-group $RESOURCE_GROUP --name $CONTAINER_REGISTRY --sku Basic  
  
# Enable admin rights for the registry  
az acr update -n $CONTAINER_REGISTRY --admin-enabled true  
  
# Login to the container registry  
az acr login --name $CONTAINER_REGISTRY  
  
# Build and push the Docker image to ACR  
az acr build --registry $CONTAINER_REGISTRY --image $IMAGE_NAME --file ./Dockerfile.mcp .  
  
# Create the Container App environment  
az containerapp env create --name $CONTAINER_ENVIRONMENT --resource-group $RESOURCE_GROUP --location $LOCATION  
  
# Deploy the Container App and get its public URL  
app_service_output=$(az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $CONTAINER_ENVIRONMENT \
  --image $CONTAINER_REGISTRY.azurecr.io/$IMAGE_NAME \
  --min-replicas 1 --max-replicas 1 \
  --target-port $APP_PORT \
  --ingress external \
  --registry-server $CONTAINER_REGISTRY.azurecr.io \
  --query properties.configuration.ingress.fqdn \
  --output tsv)
  
if [ -z "$app_service_output" ]; then  
  echo "Failed to retrieve the URL of the $APP_NAME service."  
  exit 1  
else  
  echo "Successfully deployed $APP_NAME with URL: https://$app_service_output"  
fi  