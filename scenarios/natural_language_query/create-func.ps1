
$location="East US"
$resourceGroup="<RESOURCE GROUP NAME>"
$storageaccountname="<STORAGE ACCOUNT NAME>"
$functionname="<fUNCTION APP NAME>"

az storage account create --name $storageaccountname --location "eastus" --resource-group $resourceGroup --sku "Standard_LRS"

## create azure func resource
az functionapp create --name $functionname --storage-account $storageaccountname --consumption-plan-location eastus --resource-group $resourceGroup --os-type Linux --runtime python --runtime-version 3.9 --functions-version 4

## need this to enable portal test page
az webapp cors add --resource-group $resourceGroup --name $functionname --allowed-origins 'https://ms.portal.azure.com'

## run this command in natural_language_query\azurefunc\ folder to publish the function
func azure functionapp publish $functionname --python --build remote