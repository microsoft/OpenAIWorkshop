
# Table of Contents

## 1. [Introduction](#introduction)

## 2. [Overview of the Chat Completion API](#overview-of-the-chat-completion-api)

## 3. [Example ChatCompletion.create() Calls](#example-chatcompletioncreate-calls)

---

## Introduction

---

The ChatGPT and GPT-4 models are optimized for conversational interfaces and work differently than the older GPT-3 models. They are conversation-in and message-out, and require input formatted in a specific chat-like transcript format. Azure OpenAI provides two different options for interacting with these models: Chat Completion API and Completion API with Chat Markup Language (ChatML).

The Chat Completion API is the preferred method for accessing these models, while ChatML provides lower level access but requires additional input validation and only supports ChatGPT models. It's important to use the techniques described in the article to get the best results from the new models.

This notebook will cover the aspects of the Chat Completion Python API with conversation, roles (system, assistant, user) and examples of different usage scenarios.

---

## Overview of the Chat Completion API

> **Note:** The following parameters aren't available with the new ChatGPT and GPT-4 models: **logprobs**, **best_of**, and **echo**. If you set any of these parameters, you'll get an error. gpt-35-turbo is equivalent to the gpt-3.5-turbo model from OpenAI.

### ChatCompletion.create()

OpenAI trained the ChatGPT and GPT-4 models to accept input formatted as a conversation. The messages parameter takes an array of dictionaries with a conversation organized by role. The three types of roles are:

* system
* assistant
* user

A sample input containing a simple system message, a one-shot example of a user and assistant interacting, and the final "actual" user-supplied prompt is shown below:

```json
{"role": "system", "content": "Provide some context and/or instructions to the model."},
{"role": "user", "content": "Example question goes here."}
{"role": "assistant", "content": "Example answer goes here."}
{"role": "user", "content": "First question/message for the model to actually respond to."}
```

Let's dive deeper into our 3 possible roles types of system, user, and assistant.

### **System Role**

The system role, also known as the system message, is included at the beginning of the array. This message provides the initial instructions to the model. You can provide various information in the system role including:

* A brief description of the assistant
* Personality traits of the assistant
* Instructions or rules you would like the assistant to follow
* Data or information needed for the model, such as relevant questions from an FAQ

You can customize the system role for your use case or just include basic instructions. The system role/message is optional, but it's recommended to at least include a basic one to get the best results.

> **Note:** The system role message is counted in the sum of the tokens and needs to be accounted for accordingly.

### **Assistant Role**

The assistant role is that of OpenAI or your assistant. You can omit this role in an intial ChatCompletion.create() call if desired, though it is required if you are going to pass a one-shot or few-shot example through the messages parameter. 

Let's take a look at some examples of the Chat Completion API in action.

### **User Role**

The user role is the message that the user sends to the assistant. This is the message that the model will respond to. The user role is required for the model to respond.

> **Note:** To trigger a response from the model, you should end with a user message indicating that it's the assistant's turn to respond.

---

## **Example ChatCompletion.create() Calls**

For a more comprehensive overview of the ChatCompletions.create() method, please see the [ChatCompletions.ipynb notebook](https://github.com/microsoft/OpenAIWorkshop/blob/main/scenarios/powerapp_and_python/python/ChatCompletions.ipynb) within the [power_app_and_python](https://github.com/microsoft/OpenAIWorkshop/tree/main/scenarios/powerapp_and_python) scenario.
