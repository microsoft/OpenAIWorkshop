#! /bin/bash

# This can be run from Azure Cloud Shell
# This script provisions Azure Resources such as 
# Azure Function App,
# Azure Cognitive Search,
# Azure Form Recognizer,
# Azure Storage.
# It also deploys Azure Function App Code and confiures the App Settings to use the provided Open AI Endpoint and Open AI Key.
# It also enables Semantic Search on Azure Cognitive Search.
#


printf "This utility provisions Azure Resources such as \nAzure Function App, \nAzure Cognitive Search,  \
\nAzure Form Recognizer, \nAzure Storage. \nIt also deploys Azure Function App Code and confiures the App Settings to use the provided Open AI Endpoint, \
and Open AI Key.\n"
read -p "Press enter to continue...."



RESOURCE_GROUP_NAME=$1
REGION=$2
OPENAI_EP=$3
OPENAI_KEY=$4
OPENAI_DEPLOYMENT_NAME=$5
FUNC_APP_NAME=$6

while [ -z "${RESOURCE_GROUP_NAME}" ]
do
    echo "Please provide resource group name:"
    read RESOURCE_GROUP_NAME
done

while [ -z "${REGION}" ]
do
    echo "Please provide region as in westus, eastus, etc:"
    read REGION
done


while [ -z "${OPENAI_EP}" ]
do
    echo "Please provide Azure Open AI Endpoint:"
    read OPENAI_EP
done


while [ -z "${OPENAI_KEY}" ]
do
    echo "Please provide Azure Open AI Key:"
    read OPENAI_KEY
done

while [ -z "${OPENAI_DEPLOYMENT_NAME}" ]
do
    echo "Please provide Azure Open AI Deployment Name:"
    read OPENAI_DEPLOYMENT_NAME
done


while [ -z "${FUNC_APP_NAME}" ] || [ ${#FUNC_APP_NAME} -gt 14 ]
do
    echo "Please provide Azure Function App Name. max length 14 characters:"
    read FUNC_APP_NAME

    if [ ${#FUNC_APP_NAME} -gt 14 ]
    then
        echo "Function App Name should be less than 14 characters"
        FUNC_APP_NAME=""
    fi
done

RG_EXISTS=$(az group exists -g $RESOURCE_GROUP_NAME | jq -r '.') 

func_prefix="func-search-"

if [ $RG_EXISTS = "true" ]
then
    printf "\nResource Group $RESOURCE_GROUP_NAME already exists.\n"
    while [ -z "${DELETE_RG}" ]
    do
        printf "Delete and recreate the resource group if you want to deploy again.\n \
        y - yes, delete resource group \n \
        n - no, do not delete resource group and exit \n \
        c - continue, provision resources in this $RESOURCE_GROUP_NAME resource group \n - y/n/c?"
        read DELETE_RG
    done

    if [ $DELETE_RG == "y" ]
    then
        printf "\nDeleting Resource Group..." 
        az group delete -n $RESOURCE_GROUP_NAME -y
    elif [ $DELETE_RG == "n" ]
    then
        printf "\nExiting...\n"
        exit 0
    elif [ $DELETE_RG == "c" ]
    then
        printf "\nContinuing...\n"
    else
        printf "\nInvalid input. Exiting...\n"
        exit 1
    fi    
fi

RG_EXISTS=$(az group exists -g $RESOURCE_GROUP_NAME | jq -r '.') 

if [ $RG_EXISTS = "false" ]
then
    printf "\nCreating Resource Group...\n" 
    az group create -n $RESOURCE_GROUP_NAME -l $REGION
fi

if [ $? -ne 0 ]
then
    printf "\nError creating resource group. Exiting...\n"
    exit 1
fi


FUNC_NAME=$func_prefix$FUNC_APP_NAME

#function_name=$(az resource list -g $RESOURCE_GROUP_NAME | jq -r --arg func_prefix $func_prefix '.[] | select(.type == "Microsoft.Web/sites") | select(.name | startswith($func_prefix)) | .name')

function_name=$(az resource list -g $RESOURCE_GROUP_NAME | jq -r --arg FUNC_NAME $FUNC_NAME '.[] | select(.type == "Microsoft.Web/sites") | select(.name = $FUNC_NAME) | .name')

if [[ $function_name = $FUNC_NAME ]]
then
    printf "\nFunction App $function_name already exists.\n"
    printf "\nPlease delete resource group to deploy again. Re-run this script.\n"
    printf "\nContinuing with scenario steps...\n"
else
    printf "\nDeploying Resources...\n"
    az deployment group create -g $RESOURCE_GROUP_NAME --template-file ./azure-deploy-resources.json --parameters \
        OPENAI_RESOURCE_ENDPOINT=$OPENAI_EP \
        OPENAI_API_KEY=$OPENAI_KEY \
        OPENAI_Model_Deployment_Name=$OPENAI_DEPLOYMENT_NAME \
        functionAppName=$FUNC_NAME
fi

if [ $? -ne 0 ]
then
    printf "\nError deploying resources. Exiting...\n"
    exit 1
fi

printf "\nAdding cors settings to Azure Function App...\n"
az functionapp cors add -g $RESOURCE_GROUP_NAME -n $FUNC_NAME --allowed-origins https://portal.azure.com https://ms.portal.azure.com

printf "\nDeploying Azure Function App Code...\n"
cd ../orchestrator
func azure functionapp publish $FUNC_NAME --force --python


printf "\nRetrieving additional details like subscriptionId, accessToken etc...\n"
subscriptionId=$(az account show | jq -r .id)
accesstoken=$(az account get-access-token | jq -r .accessToken)
location=$(az group show  -g $RESOURCE_GROUP_NAME | jq -r .location)

printf "\nRetrieving Azure Cognitive Search Admin Keys...\n"
search_prefix="search-"
search_service_name=$(az resource list -g $RESOURCE_GROUP_NAME | jq -r --arg search_prefix $search_prefix '.[] | select(.type == "Microsoft.Search/searchServices") | select(.name | startswith($search_prefix)) | .name')
azsearch_api_key=$(az search admin-key show -g $RESOURCE_GROUP_NAME --service-name $search_service_name  | jq -r .primaryKey)


printf "\nEnabling Semantic Search on Azure Cognitive Search...\n"

url="https://management.azure.com/subscriptions/$subscriptionId/resourcegroups/$RESOURCE_GROUP_NAME/providers/Microsoft.Search/searchServices/$search_service_name?api-version=2021-04-01-Preview"
curl --location --request PUT \
-d "{\"location\": \"$location\",\"sku\": {\"name\": \"standard\"},\"properties\": {\"semanticSearch\": \"free\"}}" \
"$url" \
--header 'Content-Type: application/json' \
--header "Authorization: Bearer $accesstoken" 


azsearch_ep="https://$search_service_name.search.windows.net/"

printf "\nRetrieving Azure Form Recognizer Endpoint and API Keys...\n"
afr_prefix="afr-cognitive-"
afr_service_name=$(az resource list -g $RESOURCE_GROUP_NAME | jq -r --arg afr_prefix $afr_prefix '.[] | select(.type == "Microsoft.CognitiveServices/accounts") | select(.name | startswith($afr_prefix)) | .name')
afr_api_key=$(az cognitiveservices account keys list --name $afr_service_name   --resource-group $RESOURCE_GROUP_NAME | jq -r .key1)
afr_ep="https://$location.api.cognitive.microsoft.com/"



printf "\nInstall pip packages...\n"
pip install -r requirements.txt

printf "\nCreating secrets.env file...\n"
echo "" > ../ingest/secrets.env
echo "AZSEARCH_EP=$azsearch_ep" >> ../ingest/secrets.env
echo "AZSEARCH_KEY=$azsearch_api_key" >> ../ingest/secrets.env
echo "INDEX_NAME=azure-ml-docs" >> ../ingest/secrets.env
echo "AFR_ENDPOINT=$afr_ep" >> ../ingest/secrets.env
echo "AFR_API_KEY=$afr_api_key" >> ../ingest/secrets.env

printf "\nIngesting data into Azure Cognitive Search...\n"
cd ../ingest
python search-indexer.py


printf "\nYou can test the function url by running the following command:\n"

func_code=$(az functionapp keys list -g $RESOURCE_GROUP_NAME --name $FUNC_NAME | jq -r .functionKeys.default)
func_url="$(az functionapp function show --function-name orchestrator-func-app  --name $FUNC_NAME --resource-group $RESOURCE_GROUP_NAME | jq -r .invokeUrlTemplate)"$"?code=$func_code&num_search_result=5"

printf "\nCopy and paste the following command to test the function url:\n"

printf "\n"
echo "curl -X POST '$func_url' -d '@test_prompt.json'"
printf "\n"


