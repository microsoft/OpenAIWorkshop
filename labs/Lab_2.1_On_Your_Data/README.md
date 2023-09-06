# Azure OpenAI On Your Data Workshop

Welcome to the workshop where you will learn how to use Azure OpenAI Service to chat with and analyze your own data using GPT-35-Turbo and GPT-4.

## What is Azure OpenAI On Your Data?

[Azure OpenAI On Your Data](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/use-your-data) is a feature that lets you run chat models on your data without training or fine-tuning them. This way, you can chat on top of, and analyze your data with more accuracy and speed. You can also get valuable insights that can help you make better decisions, identify trends and patterns, and optimize your operations.

One of the benefits of Azure OpenAI On Your Data is that it can tailor the content of conversational AI based on your data. The model can access and reference specific sources to support its responses, so the answers are not only based on its pretrained knowledge but also on the latest information available in your data source.

## What are the features of Azure OpenAI On Your Data?

Azure OpenAI On Your Data works with GPT-35-Turbo and GPT-4, which are powerful language models from OpenAI. You can access Azure OpenAI On Your Data using a REST API or the web-based interface in the Azure OpenAI Studio.

One of the features of Azure OpenAI On Your Data is that it can retrieve and use data in a way that enhances the model's output. Azure OpenAI On Your Data, together with Azure Cognitive Search, determines what data to retrieve from your data source based on the user input and conversation history. This data is then augmented and resubmitted as a prompt to the OpenAI model.

## What are the goals of this workshop?

The goals of this workshop are:

- To introduce you to Azure OpenAI On Your Data
- To show you how to connect your data source using Azure OpenAI Studio
- To demonstrate how to chat with and analyze your data using OpenAI models
- To provide you with hands-on exercises and challenges

## How does this workshop apply to you?

This workshop is for education and research customers who want to use Azure OpenAI Service to chat with and analyze their own data. Whether you are a student, a teacher, a researcher, or an administrator, you can benefit from Azure OpenAI On Your Data in various ways. For example, you can:

- Chat with your course materials, lecture notes, textbooks, or research papers
- Chat with your assignments, projects, or publications
- Chat with your datasets, surveys, or experiments
- Chat with institutional documents

By using Azure OpenAI On Your Data, you can enhance your learning, teaching, research, and administration experience with conversational AI.

## How to deploy the solution?

Once you're satisfied with the experience in Azure OpenAI Studio, you can deploy the solution directly from the Studio by selecting the **Deploy to** button. This gives you the option to either deploy the model as a standalone [Azure Web App](https://azure.microsoft.com/en-us/products/app-service/web), or [Power Virtual Agents](https://powervirtualagents.microsoft.com/en-us/) if you're using your own data on the model .

A web application is a simple way to interact with your model through a browser. You can customize the look and feel of the web app, as well as add additional features such as authentication and logging.

Power Virtual Agents is a platform that allows you to create powerful chatbots for various scenarios. You can integrate your model with Power Virtual Agents to provide a rich conversational experience for your users. You can also connect your chatbot to different channels such as Teams, Facebook Messenger, or Slack.

## Prerequisites
1. An Azure Subscription with Owner or Contributor access
1. An Azure OpenAI resource deployed in **East US**


---

**Warning:** The resources deployed in this lab are not free and will incur charges if you do not delete them after completing the lab. To avoid unwanted charges, please follow the instructions in the [cleanup section](cleanup.md) to delete the resources when you are done.

---


## [Proceed to lab](lab.md)