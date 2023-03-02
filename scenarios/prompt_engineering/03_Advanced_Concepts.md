# Advanced Concepts

At this point you have experienced the power and flexibility of prompts. Tuning prompts to get the desired results is the idea behind prompt engineering.

We will now cover some more advanced topics to tune our outputs without introducing fine-tuning of our GPT models.

Let's take a simple classification example:

Prompt:
```
Classify the sentiment of the text below.

Text: I think this movie was terrible. What a waste of time.
```

Output:
```
Negative
```

The output seems to be correct, but we could improve it by providing more information to the model if we wanted a more granular classification. Let's do this via a Zero-Shot prompt.

## Zero-Shot Prompts

The GPT LLMs are trained on such large amount of data that they are capable of understanding complex instructions to lead to the desired output in most cases. This is called 'Zero-Shot' prompt.

We could refine the example below by being more descriptive about our instructions.

Prompt:
```
Classify the sentiment of the text below into very negative, negative, neutral, positive, very positive.

Text: I think this movie was terrible. What a waste of time.
```

Output:
```
Very Negative
```

This is called Zero-Shot. A precise instruction leading to the desired output without any example.

## One-Shot Prompts

Sometimes it may be easier to provide an example to the model to learn from. This is called 'One-Shot' prompt.

First, a Zero-Shot Prompt:
```
Tell me in which city a university is located.

University: UCLA
```

Output:
```
City: Los Angeles, California
```

Let's say you wanted to have a specific output for this prompt. You could provide an example to the model to learn from.

One-Shot Prompt variation:
```
Tell me in which city a university is located.

University: UCLA
City: Los Angeles, CA, USA

University: MIT
```

Output:
```
City: Cambridge, MA, USA
```

Note that you could have used Zero-Shot prompt for this example as well. But, One-Shot prompts are more flexible and can be used to fine-tune the model to your needs.

Zero-Shot Prompt equivalent:
```
Tell me in which city a university is located. Provide the city name, state code and country, comma separated as one line.

University: UCLA
```

Output:
```
City: Los Angeles, CA, USA
```

## Few-Shot Prompts

Few-Shot prompts enable you to provide multiple examples to the model to learn from. This is useful when you want to fine-tune the output for more complex scenarios where the output may vary based on the input. It may also be a simpler way to define a task than providing detailed natural language instructions of what you expect.

Here's an example of entity extractions which is well fitted to Few-Shot prompts.

Let's try it first with a Zero-Shot prompt.

Prompt (Zero Shot):
```
Generate a JSON document which provides Name, position and company from the text below.

Text: Fred is a serial entrepreneur. Co-founder and CEO of Platform.sh, he previously co-founded Commerce Guys, a leading Drupal ecommerce provider. His mission is to guarantee that as we continue on an ambitious journey to profoundly transform how cloud computing is used and perceived, we keep our feet well on the ground continuing the rapid growth we have enjoyed up until now.
```

Output:
```
{
  "Name": "Fred",
  "Position": "Co-founder and CEO",
  "Company": "Platform.sh, Commerce Guys"
}
```

Not exactly what we expect (only 'Platform.sh' should come back in 'Company'), and it may be difficult to express that in a Zero-Shot prompt. Let's try a Few-Shot prompt. Note that we're going to drop the instructions and just provide the desired output.

Prompt (One Shot):
```
Text: Fred is a serial entrepreneur. Co-founder and CEO of Platform.sh, he previously co-founded Commerce Guys, a leading Drupal ecommerce provider. His mission is to guarantee that as we continue on an ambitious journey to profoundly transform how cloud computing is used and perceived, we keep our feet well on the ground continuing the rapid growth we have enjoyed up until now.

JSON:
{
  "Name": "Fred",
  "Position": "Co-founder and CEO",
  "Company": "Platform.sh"
}

Text: Microsoft (the word being a portmanteau of "microcomputer software") was founded by Bill Gates on April 4, 1975, to develop and sell BASIC interpreters for the Altair 8800. Steve Ballmer replaced Gates as CEO in 2000, and later envisioned a "devices and services" strategy.

JSON:
```

Output:
```
{
  "Name": "Microsoft",
  "Founder": "Bill Gates",
  "Founded": "April 4, 1975",
  "CEO": "Steve Ballmer",
  "Strategy": "Devices and Services"
}
```

Note that the output is not what we want here, but there hasn't been enough example to understand if the goal is to extract key entities or certain entities only. A few shots prompt will clarify this.


Prompt (Few Shots):
```
Text: Fred is a serial entrepreneur. Co-founder and CEO of Platform.sh, he previously co-founded Commerce Guys, a leading Drupal ecommerce provider. His mission is to guarantee that as we continue on an ambitious journey to profoundly transform how cloud computing is used and perceived, we keep our feet well on the ground continuing the rapid growth we have enjoyed up until now.

JSON:
{
  "Name": "Fred",
  "Position": "Co-founder and CEO",
  "Company": "Platform.sh"
}

Text: Microsoft (the word being a portmanteau of "microcomputer software") was founded by Bill Gates on April 4, 1975, to develop and sell BASIC interpreters for the Altair 8800. Steve Ballmer replaced Gates as CEO in 2000, and later envisioned a "devices and services" strategy.

JSON:
{
  "Name": "Bill Gates",
  "Position": "Co-founder and CEO",
  "Company": "Microsoft"
}

Text: Franck Riboud was born on 7 November 1955 in Lyon. He is the son of Antoine Riboud, the previous CEO, who transformed the former European glassmaker BSN Group into a leading player in the food industry. He is the CEO at Danone.

JSON:
```

Output:
```
{
  "Name": "Franck Riboud",
  "Position": "CEO",
  "Company": "Danone"
}
```
Now we can see that the model clearly understands that we want to only extract 3 entities from the text and nothing else.