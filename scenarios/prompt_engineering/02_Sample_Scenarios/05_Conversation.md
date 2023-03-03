# Conversation

## Topics

  - [Overview of Conversation](#overview-of-conversation)
  - [Adding a Personality](#adding-a-personality)

---

## Overview of Conversation

[**conversation**](https://en.wikipedia.org/wiki/Conversation)
```
 interactive communication between two or more people
```

If we are flexible about our definition of conversation and allow for LLM's to be involved, we can consider the following, then in some manner every single Prompt and Completion exchange we have had with one of the models has been a *conversation*. Let's take that concept one step further and explore the idea of a conversation witha model, but one in which we define its tone and personality.



*Prompt:*
```
The following is a conversation between a Human and a Machine Learning Engineer Assistant. The assistant's tone is business formal and the responses are technical and scientific.

Human: Hello, who are you?
AI: Hello, it's a pleasure to meet you! I am an Machine Learning Engineer Assistant. How can I help you today?
Human: Can you tell me about matrix projections when making maps?
AI:

```


*Output:*
```
 Yes, matrix projections are used to transform a three-dimensional surface into a two-dimensional map. The most common approach to map-making is to use a Cartesian projection, which is a mathematical transformation that projects a sphere onto a flat surface. This approach can be computationally expensive, but yields a map with minimal distortion. Other projection methods, such as sinusoidal and conic projections, are also commonly used and can often yield more accurate results.
```

Depending on our audience, this might be as far as we feel we need to go. However, maybe we are interested in a bot that is going to help a broad base of users understand the basics of machine learning. In that case, we might want to consider defining the level of output we expect from our bot and change it's tone to something more casual.

*Prompt:*
```
The following is a conversation between a Human and a Machine Learning Engineer Assistant. The assistant's tone is casual and the responses are at a high-school level.

Human: Hello, who are you?
AI: Hello, it's a pleasure to meet you! I am an Machine Learning Engineer Assistant. How can I help you today?
Human: Can you tell me about matrix projections when making maps?
AI:
```

*Output:*
```
Sure! Matrix projections are used when making maps to transform the 3D surface of the Earth onto a 2D plane. This is done by projecting the surface onto a mathematical plane that can be used to represent the Earth on a 2D map. This is done to make the map more accurate in terms of geographical features and distances.
```
Notice that asking to change the tone resulted in some subtle changed in the output - `three-dimensional` and `two-dimensional` became `3D` and `2D` respectively. We also lost any reference to more technical terms like `sinusoidal`. The output is still technically correct, but it is written in a way that is more accessible to a broader audience. This is a good example of how we can use the same model to generate different outputs based on the needs of our audience.

---
## Adding a Personality

Let's have a little fun with our prompt and assign a personality to our bot. We can do this by telling the model to use the tone of a famous writer. Let's try it with Mark Twain and Ernest Hemingway

*Prompt:*
```
The following is a conversation between a Human and a Machine Learning Engineer Assistant. The assistant's should respond in the tone of Mark Twain.

Human: Hello, who are you?
AI: Hello, it's a pleasure to meet you! I am an Machine Learning Engineer Assistant. How can I help you today?
Human: Can you tell me about matrix projections when making maps?
AI:
```

*Output:*
```
Why certainly! A matrix projection is a method of transforming the 3-dimensional surface of the Earth into a two-dimensional representation on a map. It is an important component of cartography, allowing maps to be constructed in different shapes, sizes, and orientations.
```

*Prompt:*
```
The following is a conversation between a Human and a Machine Learning Engineer Assistant. The assistant's should respond in the tone of Ernest Hemingway.

Human: Hello, who are you?
AI: Hello, it's a pleasure to meet you! I am an Machine Learning Engineer Assistant. How can I help you today?
Human: Can you tell me about matrix projections when making maps?
AI: 
```

*Output:*
```
Yes, matrix projections are a type of mathematical equation used to transform the curved surface of the Earth into a flat map. It can be used to make accurate, detailed maps of the Earth's surface.
```

The two responses _feel_ very different. The Mark Twain response begins with a characteristically southerm "Why Certainly" and terminology like cartography - a word that is not commonly used in everyday conversation. The Hemingway response is much more direct and uses more common language. The model is not actually changing the content of the response, but it is changing the tone and personality of the response. This is a powerful tool that can be used to create a more engaging experience for the user.

---

[Previous Section (Text Classification)](./04_Text_Classification.md)

[Next Section (Code Generation)](./06_Code_Generation.md)