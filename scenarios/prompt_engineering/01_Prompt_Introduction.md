## Exercise 2: Introduction to Prompt Engineering & Azure OpenAI Studio
## Topics

- [What is a prompt?](#what-is-a-prompt)
- [What is prompt engineering?](#what-is-prompt-engineering)
- [Trying out Prompt Engineering with Azure OpenAI Playground](#Trying-out-Prompt-Engineering-with-Azure-OpenAI-Playground)
- [Basic Prompt Examples](#basic-prompt-examples)
- [Elements of a Prompt](#elements-of-a-prompt)
- [Chat playground parameters](#Chat-playground-parameters)
- [General Tips for Designing Prompts](#general-tips-for-designing-prompts)


## What is a prompt?
![image](https://www.closerscopy.com/img/blinking-cursor-v2.gif)

We've all seen the blinking cursor. Waiting expectantly for us to act, denoting our chance to provide input...

One way to think of a prompt is as a piece of text that is used to initiate or provide context for the generation of output, primarily natural language in our use cases, by the language model. This could be an input sentence, question, or topic to generate a response from the language model.

## What is prompt engineering?
Prompt engineering is a relatively [new discipline](https://www.businessinsider.com/prompt-engineering-ai-chatgpt-jobs-explained-2023-3) for developing and optimizing prompts to efficiently use language models (LMs) across a wide variety of business applications. Prompt engineering skills help to better understand the capabilities and limitations of large language models (LLMs) and refine the completions (outputs) of LLMs. Prompt engineering is used to improve the capacity of LLMs on a wide range of common and complex tasks, such as question answering and arithmetic reasoning. Developers use prompt engineering to design robust and effective prompting techniques that interface with LLMs and other tools.

This guide covers the basics of standard prompts to provide a rough idea of how to interact with and instruct the LLMs found on [Azure OpenAI Studio's Playground](https://oai.azure.com/portal/playground). 

###  Trying out Prompt Engineering with Azure OpenAI Playground
Azure OpenAI Studio provides access to model management, deployment, experimentation, customization, and learning resources. The Chat playground within Azure OpenAI Studio is based on a conversation-in, message-out interface. You can initialize the session with a system message to set up the chat context.

In the Chat playground, you're able to add few-shot examples. The term few-shot refers to providing a few of examples to help the model learn what it needs to do. You can think of it in contrast to zero-shot, which refers to providing no examples.

In the Assistant setup, you can provide few-shot examples of what the user input may be, and what the assistant response should be. The assistant tries to mimic the responses you include here in tone, rules, and format you've defined in your system message.
Let's go ahead and launch the Azure OpenAI playground to learn about prompt engineering. 

1. In the **Azure portal**, search for **OpenAI** and select **Azure OpenAI**.

   ![](../natural_language_query/images/openai8.png)

1. On **Cognitive Services | Azure OpenAI** blade, select **openai-<inject key="DeploymentID" enableCopy="false"/>**

   ![](../natural_language_query/images/openai9.png)

1. In the Azure OpenAI resource pane, click on **Go to Azure OpenAI Studio** it will navigate to **Azure AI Studio**.

   ![](../natural_language_query/images/openai11-1.png)

1. In the **Azure AI Stuido**, click on **Completions** under play **Playground** from the left menu.

1. In the **Completions playground**, from Deployments select **gpt** 

<img width="900" alt="Screenshot 2023-03-02 121725" src="https://user-images.githubusercontent.com/106187595/222518636-237fc5dc-8288-4498-9818-82a44af33f16.png">

---
## Basic Prompt Examples

> **Note:** Please feel free to enter anything listed in the `Prompt:` box into a `text-davinci-003` model in the [Azure OpenAI Studio's Playground](https://oai.azure.com/portal/playground) to follow along with these prompt examples. Be aware that you may receive different outputs than what is listed in the `Output:` box, given the nature of generative models

You can achieve a lot with prompts, but the quality of results depends on how much information you provide in the prompt without being overly descriptive. A prompt can contain information like instructions or questions. As we will learn later with more advanced prompts, we can also supply examples of required outputs as well as context for our instructions.

Here is a basic example of a simple prompt:

*Prompt:*
```
GPT-3 is
```
*Output:*
```
 an autoregressive language model that was developed by OpenAI. It stands for Generative Pre-trained Transformer 3.
 It is a large-scale language model that uses deep learning techniques to generate human-like text. GPT-3 uses a
 transformer-based architecture to generate text with context
```
> **Note:**  The `Output` in our example ends abruptly because our **Max length (tokens)** variable is set to `=60`. **Max Length (tokens)** sets a limit on the number of tokens to generate in a response. The `text_davinci-003` model supports a maximum of 2048 tokens shared between a given prompt and response completion. (One token is roughly 4 characters for typical English text.)

The `Output:` is a series of strings that make sense given the context provided by our prompt of `"GPT3-3 is"`. However, the output may be unwanted or unexpected based on our use-case. How can we refine, or engineer, our prompt in order to achieve our desired output?

The first thing we can do is provide explicit instructions as to what we want the model to do with our previous prompt. This is what is meant by _prompt engineering_: refining the input so as to produce the best output from the LLM.

*Prompt:*
```
Tell me a joke that begins with: GPT-3 is
```

*Output:*
```
GPT-3 is so intelligent that it can tell a joke without a punchline.
```

Did our instructions improve our output? Admittedly, this is not the funniest joke ever told. And unlike supervised learning problems, there is no easy error or loss metric to compare between the two outputs. Let's look at exactly what we asked the model to generate and what we received:
| Requirement | Output Meets Requirement? | 
|-------------|--------|
| Begin with the words, "GPT-3 is" | Yes, the `Output:` began with the words "GPT-3 is" |
| The output be in the form of a joke | An attempt was made |

---
## Standard Prompts

We looked at two very basic prompts above as well as the output they generated. Now that we are familiar with the basic concepts of prompt engineering, let's look at some common formats for prompts. 

### Question Format

```
<Question>?
```
### Question-Answer (QA) Format 
This can be formatted into a QA format, which is standard in a lot of QA datasets, as follows:

```
Q: <Question>?
A: 
```
Another way to think about this, using other common terms, would be:
```
Prompt: <Question>?
Completion: <Answer>
```
### Few-shot Format
Given the standard format above, one popular and effective technique to prompting is referred to as few-shot prompting where we provide multiple examples. Few-shot prompts can be formatted as follows:

```
<Question>?
<Answer>

<Question>?
<Answer>

<Question>?
<Answer>

<Question>?

```

### Few-shot Question-Answer (QA) Format
And you can already guess that its QA format version would look like this:

```
Q: <Question>?
A: <Answer>

Q: <Question>?
A: <Answer>

Q: <Question>?
A: <Answer>

Q: <Question>?
A:
```

Keep in mind that it's not required to use the QA format. The format depends on the task at hand. For instance, you can perform a simple classification task and give examples that demonstrate the task as follows:

*Prompt:*
```
This is awesome! // Positive
This is bad! // Negative
Wow that movie was rad! // Positive
What a horrible show! //
```

*Output:*
```
Negative
```
or
*Prompt*
```
The following is a list of companies and the categories they fall into

Facebook: Social media, Technology
LinkedIn: Social media, Technology, Enterprise, Careers
Uber: Transportation, Technology, Marketplace
Unilever: Conglomerate, Consumer Goods
Mcdonalds: Food, Fast Food, Logistics, Restaurants
FedEx:
```
*Output:*
```
Logistics, Delivery, and Shipping
```
Few-shot prompts enable in-context learning, which is the ability of language models to learn tasks given only a few examples. We will see more of this in action in the upcoming advanced prompt engineering sections.

---


## Elements of a Prompt

As we cover more and more examples and applications that are possible with prompt engineering, you will notice that there are certain elements that make up a prompt. 

A prompt can contain any of the following components:

- **Instruction** - a specific task or instruction you want the model to perform

- **Context** - can involve external information or additional context that can steer the model to better responses

- **Input Data** - is the input or question that we are interested in finding a response for

- **Output Indicator** - indicates the type or format of output.

Not all the components are required for a prompt, and the format depends on the task at hand. We will touch on more concrete examples in our upcoming guides.

---

## Chat playground parameters

There are many parameters that you can adjust to change the performance of your model:

- **Temperature** - Controls randomness. Lowering the temperature means that the model produces more repetitive and deterministic responses. Increasing the temperature results in more unexpected or creative responses. Try adjusting temperature or Top P but not both.

- **Max length (tokens)e** - Set a limit on the number of tokens per model response. The API supports a maximum of 4000 tokens shared between the prompt (including system message, examples, message history, and user query) and the model's response. One token is roughly four characters for typical English text.

- **Stop sequencese** - Make responses stop at a desired point, such as the end of a sentence or list. Specify up to four sequences where the model will stop generating further tokens in a response. The returned text won't contain the stop sequence.

- **Top probabilities (Top P)e** - Similar to temperature, this controls randomness but uses a different method. Lowering Top P narrows the model’s token selection to likelier tokens. Increasing Top P lets the model choose from tokens with both high and low likelihood. Try adjusting temperature or Top P but not both.

- **Frequency penaltye** - Reduces the chance of repeating a token proportionally based on how often it has appeared in the text so far. This decreases the likelihood of repeating the exact same text in a response.

- **Presence penaltye** - Reduce the chance of repeating any token that has appeared in the text at all so far. This increases the likelihood of introducing new topics in a response.

- **Pre-response texte** - Insert text after the user’s input and before the model’s response. This can help prepare the model for a response.

- **Post-response texte** - Insert text after the model’s generated response to encourage further user input, as when modeling a conversation.

- **Max response** - Set a limit on the number of tokens per model response. The API supports a maximum of 4000 tokens shared between the prompt (including system message, examples, message history, and user query) and the model's response. One token is roughly four characters for typical English text.

The Current token count is viewable from the Chat playground. Since the API calls are priced by token and it's possible to set a max response token limit, you'll want to keep an eye out for the current token count to make sure the conversation-in doesn't exceed the max response token count.

## General Tips for Designing Prompts


Here are some tips to keep in mind while you are designing your prompts:

### Start Simple
As you get started with designing prompts, you should keep in mind that it is an iterative process that requires experimentation to get optimal results. Using a simple playground like [Azure's OpenAI Studio's Playground](https://oai.azure.com/portal/playground) will allow you to test out ideas quickly and easily. The model won't be offended if you ask it to do very similar things over and over again!

You can start with simple prompts and keep adding more elements and context as you aim for better results. Versioning your prompt along the way is vital for this reason. As we read the guide, you will see many examples where specificity, simplicity, and conciseness will often give you better results. Begin with a hardcoded prompt and move into more dynamically generated prompts as you refine your results.

### The Instruction
You can design effective prompts for various simple tasks by using commands to instruct the model what you want to achieve, such as "Write", "Classify", "Summarize", "Translate", "Order", "Create", "make," etc.

Keep in mind that you also need to experiment a lot to see what works best. Try different instructions with different keywords, context, and data and see what works best for your particular use case and task. Usually, the more specific and relevant the context is to the task you are trying to perform, the better. 

Others recommend that instructions be placed at the beginning of the prompt. It's also recommended that some clear separators, like "###" be used to separate the instruction and context. 

For instance:

*Prompt:*
```
### Instruction ###
Translate the text below to Spanish:

Text: "hello!"
```

*Output:*
```
¡Hola!
```

### Specificity
Be very specific about the instructions and tasks you want the model to perform. The more descriptive and detailed the prompt is, the better the results. This is particularly important when you have a desired outcome or style of generation you are seeking. There aren't specific tokens or keywords that lead to better results. It's more important to have a good format and a descriptive prompt. Providing examples in the prompt is very effective in getting the desired output in specific formats. 

When designing prompts, you should also keep in mind the length of the prompt, as there are limitations regarding how long this can be. Thinking about how specific and detailed you should be is something to consider. Too many unnecessary details are not necessarily a good approach. The details should be relevant and contribute to the task at hand. This is something you will need to experiment with a lot. We encourage a lot of experimentation and iteration to optimize prompts for your applications.

As an example, let's try a simple prompt to extract specific information from a piece of text.

*Prompt:*
```
There are many fruits that were found on the recently discovered planet Goocrux. There are neoskizzles that grow there.
which are purple and taste like candy. There are also heckles, which are a greyish-blue fruit and are very tart.
a little bit like a lemon. Pounits are a bright green colour and are more savoury than sweet. There are also plenty of
loop novas, which have a neon pink flavour and taste like cotton candy. Finally, there are fruits called glowls, which have
a very sour and bitter taste that is acidic and caustic, and have a pale orange tinge to them.

Please make a table summarizing the fruits from Goocrux
| Fruit | Color | Flavor |
| Neoskizzles | Purple | Sweet |
| Loheckles | Grayish blue | Tart |
```

*Output:*
```
| Pounits | Bright green | Savory |
| Loopnovas | Neon pink | Cotton candy |
| Glowls | Pale orange | Sour and bitter |
```
> **Note:** The instructions are `Please make a table summarizing the fruits from Goocrux`, and then a sample table with column headings and two examples, with the correct elements in their respective columns, are supplied, making this a few-shot prompt.

### Avoid Impreciseness

Given the tips above about being detailed and improving format, it's easy to fall into the trap of wanting to be too clever about prompts and potentially creating imprecise descriptions. It's often better to be specific and direct. The model doesn't mind you being explicit in your instructions; you can't offend it! The analogy here is very similar to effective communication: the more direct, the more effectively the message gets across.

For example, you might be interested in learning the concept of prompt engineering. You might try something like:
*Prompt:*
```
Provide a short explanation of what prompt engineering is in NLP without using technical language
```
*Output:*
```
Prompt engineering in NLP is the process of creating questions or prompts to help a computer understand
natural language. It involves creating questions or statements that can be used to prompt a computer to generate
a response in natural language.
```
It's not clear from the prompt above how many sentences to use, what style we need things output in, or what we intend to take away from the output. You might get passable responses with the above prompt; the better prompt would be very specific, concise, and to the point. Something like:
*Prompt:*
```
Provide a list with five bullet points, one sentence each, describing the benefits of prompt 
engineering when interacting with a large language model using an 8th-grade reading-level comprehension
```
*Output:*
```
• Increases efficiency by reducing the need for user input.
• Improves the user experience by reducing the time spent waiting for a response.
• reduces cognitive load by simplifying language and providing clear instructions.
• enhances accuracy by providing a consistent format for language input.
• Enhances scalability by allowing for the integration of more complex language models.
```

### To do or not to do?
Another common tip when designing prompts is to avoid saying what not to do but say what to do instead. This encourages more specificity and a focus on the details that lead to good responses from the model.

Here is an example of an IT support chatbot failing to uphold our instructions because the instructions are phrased negatively. 

*Prompt:*
```
The following is an exchange between an IT support agent and a customer. The customer is locked out of their account. DO NOT ASK FOR THEIR PASSWORD. DO NOT ASK ABOUT PERSONAL INFORMATION.

Customer: I cannot log into my account.
IT Support Agent:
```

*Output:*
```
Okay, I understand. Can you please tell me the email address you are trying to log in with?
```

Here is a better prompt:

*Prompt:*
```
The following is an exchange between an IT support agent and a customer. The customer is locked out of their account. The IT Support Agent must not discuss personal information such as username, password, name, email address, account number, or phone number, or security questions. If the IT Support Agent needs personal information to assist the customer, the IT Support Agent must ask them to click on the "Forgot Password?" link on the sign-on page and follow the on-screen instructions.

Customer: I cannot log into my account.
IT Support Agent:
```

*Output:*
```
I apologize that you are having difficulty accessing your account. Please click on the "Forgot Password?" link on the sign-on page and follow the on-screen instructions to reset your password and access your account.
```

Some of the examples above were adopted from the ["Best practices for prompt engineering with OpenAI API" article](https://help.openai.com/en/articles/6654000-best-practices-for-prompt-engineering-with-openai-api) and the 
[Democratizing Artificial Intelligence Research, Education, and Technologies's Prompt Engineering Guide](https://github.com/dair-ai/Prompt-Engineering-Guide)

