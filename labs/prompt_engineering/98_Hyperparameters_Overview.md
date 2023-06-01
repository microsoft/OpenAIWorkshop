# Basic Overview of Azure OpenAI Service Hyperparameters
## Quick Note on adjusting Hyperparameters

When working with prompts, you will be interacting with the LLM via an API or directly. You can configure a few parameters to get different results for your prompts.

**Temperature** - In short, the lower the temperature the more deterministic the results in the sense that the highest probable next token is always picked. Increasing temperature could lead to more randomness encouraging more diverse or creative outputs. We are essentially increasing the weights of the other possible tokens. In terms of application, we might want to use lower temperature for something like fact-based QA to encourage more factual and concise responses. For poem generation or other creative tasks it might be beneficial to increase temperature.

**Top_p** - Similarly, with top_p, a sampling technique with temperature called nucleus sampling, you can control how deterministic the model is at generating a response. If you are looking for exact and factual answers keep this low. If you are looking for more diverse responses, increase to a higher value.

The general recommendation is to alter one not both.

### text-davinci-003 model

**temperature**
```
Controls randomness: Lowering results in less random completions. 
As the temperature approaches zero, the model will become deterministic and repetitive.
```

**max_tokens**
```
Set a limit on the number of tokens to generate in a response. 
The system supports a maximum of 2048 tokens shared between a given prompt and response completion. 
(One token is roughly 4 characters for typical English text.)
```

**top_p***
```
Control which tokens the model will consider when generating a response via nucleus sampling. 
Setting this to 0.9 will consider the top 90% most likely of all possible tokens. 
This will avoid using tokens that are clearly incorrect while still maintaining variety
when the model has low confidence in the highest-scoring tokens.
```

**frequency_penalty**
```
Reduce the chance of repeating a token proportionally based on how often it has appeared in the text so far.
This decreases the likelihood of repeating the exact same text in a response.
```

**presence_penalty**
```
Reduce the chance of repeating any token that has appeared in the text at all so far. 
This increases the likelihood of introducing new topics in a response.
```

**best_of**
```
Generate multiple responses, and display only the one with the best total probability across all its tokens. 
The unused candidates will still incur usage costs, so use this parameter carefully and make sure to set the
parameters for max response length and ending triggers as well. Note that streaming will only work when this is set to 1.
```

**stop**
```
Make responses stop at a desired point, such as the end of a sentence or list.
Specify up to four sequences where the model will stop generating further tokens
in a response. The returned text will not contain the stop sequence.
```
