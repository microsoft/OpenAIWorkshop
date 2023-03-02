# Introduction to Prompt Engineering
## What is a prompt?
![image](https://www.closerscopy.com/img/blinking-cursor-v2.gif)

We've all seen the blinking cursor. Waiting expectantly for us to act; denoting our chance to provide input...

One way to think of a prompt is as a piece of text that is used to initiate or provide context for the generation of output, primarily natural language in our use-cases, by the language model. This could be an input sentence, question, or topic to generate a response from the language model.

## What is prompt engineering?
Prompt engineering is a relatively [new discipline](https://www.businessinsider.com/prompt-engineering-ai-chatgpt-jobs-explained-2023-3) for developing and optimizing prompts to efficiently use language models (LMs) across a wide variety of business applications. Prompt engineering skills help to better understand the capabilities and limitations of large language models (LLMs) and refine the completions (outputs) of LLMs. Prompt engineering is used to improve the capacity of LLMs on a wide range of common and complex tasks such as question answering and arithmetic reasoning. Developers use prompt engineering to design robust and effective prompting techniques that interface with LLMs and other tools.

This guide covers the basics of standard prompts to provide a rough idea on how to interact with and instruct the LLMs found on [Azure OpenAI Studio's Playground](https://oai.azure.com/portal/playground). 

### Note about example prompts
> **Note:** All examples are tested with `text-davinci-003` model unless otherwise specified. Each of the `Examples` scenarios (shown in the red box labeled as '1' in the picture below) has pre-set `Parameters` (e.g. `temperature=0.7` and `top_p=1` as shown in the red box labled as '2'). The examples will use those pre-sets unless otherwise noted in a specific prompt scenario.

<img width="900" alt="Screenshot 2023-03-02 121725" src="https://user-images.githubusercontent.com/106187595/222518636-237fc5dc-8288-4498-9818-82a44af33f16.png">

# Basic Prompt Examples
> **Note:** Please feel free to enter anything listed in the `Prompt:` box into a `text-davinci-003` model in the [Azure OpenAI Studio's Playground](https://oai.azure.com/portal/playground) to follow along with these prompt examples. Be aware that you may receive different outputs than what is listed in the `Output:` box given the nature of generative models

You can achieve a lot with prompts, but the quality of results depends on how much information you provide in the prompt without being overly descriptive. A prompt can contain information like the instructions or questions. As we will learn later with more advanced prompts, we can also supply examples of required outputs as well as context for our instructions.

Here is a basic example of a simple prompt:

*Prompt:*
```
GPT-3 is
```
*Output:*
```
 an autoregressive language model which was developed by OpenAI. It stands for Generative Pre-trained Transformer 3.
 It is a large-scale language model which uses deep learning techniques to generate human-like text. GPT-3 uses a
 transformer-based architecture to generate text with context
```
> **Note:**  The `Output` in our example ends abruptly because our **Max length (tokens)** variable is set to `=60`. **Max Length (tokens)** sets a limit on the number of tokens to generate in a response. The `text_davinci-003` model supports a maximum of 2048 tokens shared between a given prompt and response completion. (One token is roughly 4 characters for typical English text.)

The `Output:` is a series of strings that make sense given the context provided by our prompt of `"GPT3-3 is"`. However, the output may be unwanted or unexpected based on our use-case. How can we refine our prompt in order to achieve our desired output?

The first thing we can do is provide _context_ to our prompt. In our case, we can provide explicit instructions as to what we want the model to do with our previous prompt.

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






