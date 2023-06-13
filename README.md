# Azure OpenAI Workshop - Microsoft US Education 
[Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/overview) provides REST API access to OpenAI's powerful language models including the GPT-3, Codex and Embeddings model series. These models can be easily adapted to your specific task including but not limited to content generation, summarization, semantic search, and natural language to code translation. Users can access the service through REST APIs, Python SDK, or our web-based interface in the Azure OpenAI Studio.

![Alt text](documents/images/OpenAI.png)


In this workshop, you will learn how to leverage the Azure OpenAI service to create AI powered solutions. You will get hands-on experience with the latest AI technologies and will also learn how to interact with the Azure OpenAI APIs. 

## General Prerequisites

The following prerequisites must be completed before you start these labs

- WI-FI enabled Laptop
- You must be connected to the internet
- Use either Edge or Chrome when executing the labs.
- Access to an Azure Subscription with Owner or [Contributor Access](https://learn.microsoft.com/en-us/azure/role-based-access-control/role-assignments-steps)
  
- Approved access to Azure OpenAI service in your Azure subscription. You can request access [here](https://customervoice.microsoft.com/Pages/ResponsePage.aspx?id=v4j5cvGGr0GRqy180BHbR7en2Ais5pxKtso_Pz4b1_xUOFA5Qk1UWDRBMjg0WFhPMkIzTzhKQ1dWNyQlQCN0PWcu)


  **IMPORTANT**: 
    - Only use your institutions/organization email. Do not use a personal email address (Example: @gmail.com, hotmail.com, etc.)
    - Authorization can take up to 10 business days.  
  

- [Azure Open AI](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/how-to/create-resource?pivots=web-portal) already provisioned and **text-davinci-003** model deployed.
  For this lab, we recommend **South Central US** region for your Azure Open AI deployment.

- Required Resource Providers [How to Register Azure Services](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/resource-providers-and-types)
  
  - Azure OpenAI
  - Microsoft.Search
  - Microssoft.Functions
  - Microsoft.Authorization
  - Microsoft.CognitiveServices
  - Microsoft.ManagedIdentity
  - Microsoft.KeyVault
  - Microsoft.Storage  
  - Microsoft.Insights 
  - Microsoft.Application
  - Microsoft.LogicApps
  - Microsoft.BotService

- [VS Code](https://code.visualstudio.com/download) installed on your computer.


## Lab-specific pre-reqs:

**Lab 1:​**

No additional pre-reqs

**Lab 2:​**

- [Git](https://git-scm.com/downloads)​

- [Python](https://www.python.org/downloads/) v3.7-v3.10​

- (Optional): [Azure Developer CLI​](https://aka.ms/azure-dev/install)

​

**Lab 3:​**

- Microsoft.Search Resource provider needs to be [registered](https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/resource-providers-and-types#register-resource-provider) in the Azure Subscription.​

- [PostMan Client](https://www.postman.com/downloads/)  installed on your laptop. ​

- Azure Cloud Shell (shell.azure.com)​

- [.Net Core 3.1](https://dotnet.microsoft.com/en-us/download/dotnet/3.1) or later​

- Install [Node.js](https://nodejs.org/en/download)

- [Azure Bot Framework Composer​](https://learn.microsoft.com/en-us/composer/install-composer?tabs=windows)

- [Bot Framework Emulator​](https://github.com/Microsoft/BotFramework-Emulator/releases/tag/v4.14.1)

​

## Agenda


| Activity | Duration |
| --- | --- |
| [Lab 1: Automate Mailbox Responses](/labs/Lab_1_Automate_Mailbox_Responses/README.md) | 45 min |
| [Lab 2: Chat with your database](/labs/Lab_2_Data_Analytics/README.md) | 45 min |
| [Lab 3: Chat with your documents](/labs/Lab_3_chatWithDocuments/README.md) | 60 min |



## Before you begin

  [Retrieve your Azure OpenAI endpoint and keys](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/quickstart?tabs=command-line&pivots=programming-language-python#retrieve-key-and-endpoint) and copy them to notepad for future reference as you will be using them throughout the labs.

## Format

- Instructor will run through an overview of solutions and steps
- Audience will then build the solution in their environment

## Audience

- Power Users
- Software Engineers
- Data Scientists
- Solution Architects

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks 

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft 
trademarks or logos is subject to and must follow 
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
