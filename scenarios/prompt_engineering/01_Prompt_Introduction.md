# Introduction to Prompt Engineering
### What is a prompt?
![image](https://www.closerscopy.com/img/blinking-cursor-v2.gif)

We've all seen the blinking cursor. Waiting expectantly for us to act; denoting our chance to provide input...

One way to think of a prompt is as piece of text that is used to initiate or provide context for the generation of output, primarily natural language in our use-cases, by the language model. This could be an input sentence, question, or topic to generate a response from the language model.

### What is prompt engineering?
Prompt engineering is a relatively [new discipline](https://www.businessinsider.com/prompt-engineering-ai-chatgpt-jobs-explained-2023-3) for developing and optimizing prompts to efficiently use language models (LMs) across a wide variety of business applications. Prompt engineering skills help to better understand the capabilities and limitations of large language models (LLMs). Researchers use prompt engineering to improve the capacity of LLMs on a wide range of common and complex tasks such as question answering and arithmetic reasoning. Developers use prompt engineering to design robust and effective prompting techniques that interface with LLMs and other tools.

This guide covers the basics of standard prompts to provide a rough idea on how to use prompts to interact and instruct LLMs. 

All examples are tested with `text-davinci-003` (using OpenAI's playground) unless otherwise specified. It uses the default configurations, e.g., `temperature=0.7` and `top-p=1`.
