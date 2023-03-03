# Data Generation

## Topics

  - [Overview of Data Generation](#overview-of-data-generation)
  - [Few-Shot Data Generation](#few-shot-data-generation)
  - [Data Imputation](#data-imputation)
---

## Overview of Data Generation

The broad category of models being used in this workshop are known as Generative Models, in our case [Generative Pre-trained Transformer 3](https://news.microsoft.com/source/features/ai/from-conversation-to-code-microsoft-introduces-its-first-product-features-powered-by-gpt-3/?culture=en-us&country=us). Generative models are models that can generate new data based on a prompt. This is useful for generating new data that can be used for training other models. For example, you can use a generative model to generate new text that can be used to train a text classification model. This is useful when you don't have enough data or need anonymous data that mimics real data to train a model. It can also be useful to impute data in a dataset that is missing data. 

> **Note:** The Max Length (tokens) variable slider has been increased to 1,200 tokens to allow for a longer exchange between the customer and the agent.

*Prompt:*
```
You must create a 2,000 word long document representing an exchange between a customer service agent for the fictitious company Contoso Wireless and their customer. The sentiment of the customer must be {random_sentiment} and the topic of the conversation betweem the agent and customer should center around {random_topic}. The customer must be asking about the product {random_product}. The document should have at least 8 back and forth exchanges between the customer and the agent.'
```

*Output:*
```
Customer: Hi there, I'm considering upgrading my Contoso Wireless cell phone service and wanted to know what my options for that are.

Agent: Hello there! Welcome to Contoso Wireless. Upgrading your service is a great idea. We are sure you will be pleased with our upgraded plans. Can you tell me what device you currently have with us?

Customer: Yes, of course. I have an iPhone 11.

Agent: Okay, great. We have several upgrade plans available for an iPhone 11. Let me just run through your options with you. 

Customer: Sure, that would be great.

Agent: Okay, so our first option is an upgrade to an unlimited data plan. We offer customers unlimited data, unlimited text messaging and unlimited nationwide calling.

Customer: That sounds fantastic! What is the cost for that plan?

Agent: The unlimited data plan for your device costs $79.99 a month. 

Customer: That's a great price! What other options do I have?

Agent: We also offer a plan that includes unlimited talk and text, plus 2 GB of high speed data. It costs $59.99 per month. 

Customer: That's great too. What other options might be available to me?

Agent: In addition to these two plans, we also have a mobile hotspot plan, which provides 5 GB of data for just $39.99 per month.

Customer: That sounds like a good deal too. Can I get more data for any of these plans?

Agent: Absolutely. We are always offering bonus data for customers who sign up for one of our plans. If you sign up for any of the plans I mentioned, you will get an extra 1 GB of data for the first three months. 

Customer: Wow, that's great. I think I'm going to go with the unlimited data plan. How can I go about doing that?

Agent: Wonderful! It's easy to upgrade your plan. All you have to do is visit our website and choose the plan you are interested in. You'll be able to make the switch right away and start enjoying all the benefits. 

Customer: Perfect. Thank you so much for your help.

Agent: You're welcome! We are always happy to help out our customers. Enjoy your new plan!
```
This is a longer exchange than normal, but it's a good example of how you can use a generative model to create data that can be used to train other models. We now have a reasonably long exchange between two individuals that is entirely anonymous. Take note that essentially created a labeled dataset by adding the sentiment (the customer does appear happy in the exchange) and topic of the conversation (upgrading their wireless service) to the prompt. 

Another important consideration is that we can progrmatically feed the model prompts with different values, for instance a different product name and sentiment each time. This is useful when you want to generate a large amount of data that is labeled with different values. For example, you could change the product name being fed into the prompt with each iteration, thereby generating a dataset that is, other than our named products, completely anonymous.

---
## Few-Shot Data Generation

The concepts from the [Introduction to Prompt Engineering](./01_Prompt_Introduction.md) and the [Advanced Concepts](./03_Advanced_Concepts.md) sections can be very informative for generating net-new data. First off, we should be as direct in our requirements as possible and provide examples of our desired output if feasible.

*Prompt:*
```
Instructions: Create 10 new rows of data that match the format listed in the the ---Example--- section.

---Example---
| Product Name | Color | Weight | Perishable |
| Crayons | Mixed | 6 oz | No |
| Carrot | Orange | 12 oz | Yes |
| Potato | Red | 5 lbs | Yes |
| Chair | Black | 25 lbs | No |
```

*Output:*
```
| Watermelon | Green | 10 lbs | Yes |
| Glass | Clear | 3 lbs | No |
| Milk | White | 1 gal | Yes |
| Pencil | Yellow | 8 oz | No |
| Envelope | White | 1 oz | No |
| Bowl | Blue | 4 lbs | No |
| Book | Brown | 15 oz | No |
| Shampoo | Yellow | 32 oz | No |
| Pizza | Red | 2 lbs | Yes |
```

We now have 10 new rows of data mimicing our original dataset. This process can be repeated until we have a large enough dataset to train our model, or fit into a data pipeline to test a process, or used in customer-facing examples where we cannot use live-data.

---
## Data Imputation

We often have data sets that are missing values. With numerical data, we have simple techniques that are quick to implement and cover most use cases. For categorical data, however, that process can be far more cumbersome and problematic. However, we can use a generative model to fill in the missing values in our with relative ease. 

For instance, we can simultaneously generate new rows of data and fill in missing values in our existing data. This is a great way to create a larger dataset that is more representative of the data we have. We will build on the prompt from the previous section and add a new requirement to fill in the missing values in our existing data.

*Prompt:*
```
Instructions: Replace any missing or blank value, denoted as ###, in the existing rows of data in the ---Example--- Section. Create 10 new rows of data that match the format listed in the the ---Example--- section.  

---Example---
| Product Name | Color | Weight | Perishable |
| Crayons | Mixed | 6 oz | No |
| Carrot | Orange | 12 oz | Yes |
| Potato | Red | 5 lbs | ### |
| Chair | Black | 25 lbs | No |
| Watermelon | Green | ### | Yes |
| Glass | Clear | 3 lbs | No |
| Milk | ###  | 1 gal | Yes |
| Pencil | Yellow | 8 oz | No |
| Envelope | ###  | 1 oz | No |
| Bowl | Blue | ###  | No |
| Book | Brown | 15 oz | No |
| Shampoo | Yellow | 32 oz | No |
| Pizza | Red | 2 lbs | Yes |
```

*Output:*
```
| Product Name | Color | Weight | Perishable |
| Crayons | Mixed | 6 oz | No |
| Carrot | Orange | 12 oz | Yes |
| Potato | Red | 5 lbs | Yes |
| Chair | Black | 25 lbs | No |
| Watermelon | Green | 8 lbs | Yes |
| Glass | Clear | 3 lbs | No |
| Milk | White  | 1 gal | Yes |
| Pencil | Yellow | 8 oz | No |
| Envelope | White  | 1 oz | No |
| Bowl | Blue | 32 oz | No |
| Book | Brown | 15 oz | No |
| Shampoo | Yellow | 32 oz | No |
| Pizza | Red | 2 lbs | Yes |
| Cheese | White | 8 oz | Yes |
| Fork | Silver | 3 oz | No | 
| Cake | White | 4 lbs | Yes |
| Toothpaste | White | 32 oz | No |
| Chocolate | Brown | 16 oz | Yes |
| Jerky | Various | 8 oz | Yes |
| Tomato Sauce | Red | 24 oz | No |
| Steak | Red | 16 oz | Yes |
| Coffee | Brown | 8 oz | No |
| Chair | Various | 25 lbs | No |
| Watch | Various | 1 oz | No |
| Pancake Mix | Brown | 24 oz | No |
| Orange | Orange | 12 oz | Yes |
| Apple | Red | 6 oz | Yes |
```
Given sufficient examples and instructions, the model can fill in the missing values in our existing data and generate new rows of data that match the format of our original dataset.

---

[Previous Section (Code Generation)](./06_Code_Generation.md)

[Next Section (Recommendations)](./08_Recommendations.md)