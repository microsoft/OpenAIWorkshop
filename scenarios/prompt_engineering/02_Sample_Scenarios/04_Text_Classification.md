# Text Classification

## Topics

  - [Classification with Prompt Engineering Directives](#classification-with-prompt-engineering-directives)
  - [Classification using One Shot or Few Shot Learning](#classification-using-one-shot-or-few-shot-learning)

---

## Classification with Prompt Engineering Directives

Quite a few use cases will fall under this category when the input isn't closely related to a business domain specificity. For example, classifying a news article into a category, classifying a product review into a sentiment, classifying a customer support ticket into a category, etc.

*Prompt:*
```
Classify the following news article into 1 of the following categories: categories: [Business, Tech, Politics, Sport, Entertainment]

news article: Donna Steffensen Is Cooking Up a New Kind of Perfection. The Internet’s most beloved cooking guru has a buzzy new book and a fresh new perspective:
```

*Output:*
```
Entertainment
```

---
## Classification using One Shot or Few Shot Learning

This topic will be covered in the next section [Advanced Concepts](./03_Advanced_Concepts.md), but it's worth mentioning here as well. One shot or few shot learning is a technique that allows you to train a model on a small amount of data and then use that model to classify new data. This is useful when you have a small amount of data, but you want to be able to classify new data that you haven't seen before.

*Prompt:*
```
Review: This is a great product. I love it.
Star Rating: 5

Review: This is a terrible product. I hate it.
Star Rating: 1

Review: I like the product overall design, but it's not very comfortable.
Star Rating: 3

Review: The product was amazing while it lasts. It broke after 2 weeks.
Star Rating:
```

*Output:*
```
2
```

You've tought the model to rank between 1 and 5 stars based on the review. You can then use this model to classify new reviews.

---

[Previous Section (Question Answering)](./03_Question_Answering.md)

[Next Section (Conversation)](./05_Conversation.md)