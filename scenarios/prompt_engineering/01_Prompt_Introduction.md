# Introduction to Prompt Engineering
### What is a prompt?
![image](https://www.closerscopy.com/img/blinking-cursor-v2.gif)

We've all seen the blinking cursor. Waiting expectantly for us to act; denoting our chance to provide input...

One way to think of a prompt is as a piece of text that is used to initiate or provide context for the generation of output, primarily natural language in our use-cases, by the language model. This could be an input sentence, question, or topic to generate a response from the language model.

### What is prompt engineering?
Prompt engineering is a relatively [new discipline](https://www.businessinsider.com/prompt-engineering-ai-chatgpt-jobs-explained-2023-3) for developing and optimizing prompts to efficiently use language models (LMs) across a wide variety of business applications. Prompt engineering skills help to better understand the capabilities and limitations of large language models (LLMs) and refine the completions (outputs) of LLMs. Prompt engineering is used to improve the capacity of LLMs on a wide range of common and complex tasks such as question answering and arithmetic reasoning. Developers use prompt engineering to design robust and effective prompting techniques that interface with LLMs and other tools.

This guide covers the basics of standard prompts to provide a rough idea on how to interact with and instruct the LLMs found on [Azure OpenAI Studio's Playground](https://oai.azure.com/portal/playground). 

### Note about example prompts
All examples are tested with `text-davinci-003` model unless otherwise specified. Each of the `Examples` scenarios (shown in the red box labeled as '1' in the picture below) has pre-set `Parameters` (e.g. `temperature=0.7` and `top_p=1` as shown in the red box labled as '2'). The examples will use those pre-sets unless otherwise noted in a specific prompt scenario.

<img width="900" alt="Screenshot 2023-03-02 121725" src="https://user-images.githubusercontent.com/106187595/222518636-237fc5dc-8288-4498-9818-82a44af33f16.png">
