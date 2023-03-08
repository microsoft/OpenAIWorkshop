# Create a single database and configure a firewall rule

$location="East US"
$resourceGroup="<RESOURCE GROUP NAME>"
$tag="create-and-configure-database"
$server="<SQL SERVER NAME>"
$database="<SQL DATABASE NAME>"
$login="azureuser"
$password="<PASSWORD>"
$subscription="<SUBSCRIPTION ID>" # add subscription here
$tenantid="<TENANT ID>"
az account set -s $subscription # ...or use 'az login'
# Specify appropriate IP address values for your environment
# to limit access to the SQL Database server
$startIp="0.0.0.0"
$endIp="255.255.255.255"

az login --tenant $tenantid
az account set -s $subscription
echo "Using resource group $resourceGroup with login: $login, password: $password..."
echo "Creating $resourceGroup in $location..."

az group create --name $resourceGroup --location "$location" --tags $tag
echo "Creating $server in $location..."
az sql server create --name $server --resource-group $resourceGroup --location "$location" --admin-user $login --admin-password $password
echo "Configuring firewall..."
az sql server firewall-rule create --resource-group $resourceGroup --server $server -n AllowYourIp --start-ip-address $startIp --end-ip-address $endIp
echo "Creating $database on $server..."
az sql db create --resource-group $resourceGroup --server $server --name $database --sample-name AdventureWorksLT --edition GeneralPurpose --family Gen5 --capacity 2 --zone-redundant true # zone redundancy is only supported on premium and business critical service tiers