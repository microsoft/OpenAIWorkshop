# Recommendations

## Topics
- [Overview of Recommendations](#overview-of-recommendations)

---
## Overview of Recommendations
Recommendations are something we are all familiar with in that every website we visit has some sort of recommendations engine. The goal of a recommendations engine is to provide users with a list of items that they are likely to be interested in. This is a very broad definition, but it is a good starting point. How can we extract recommendations from a user's input? 

First, let's recall our earlier lessons around prompt engineering. We learned that we can use headings like `---Background---` and `---Preferences---` sections to present information about a user's background and preferences to the model, which can then make recomendations to a user based on the supplied context. Please feel free to take the supplied prompt and change characteristics in the `---Background---` and `---Preferences---` sections to see how the model's recommendations change.

> **Note:** You may wish to change the `Max length (tokens)` parameter to a number higher than the default in order to see more of the model's recommendations and text in a single output.

*Prompt:*
```
Given a peson's background labeled in the ---Background--- section and preference, labeled in the ---Preferences--- section, provide hourly recommendations for a 3-day itinerary in San Francisco. Show lodging options from Hotel Azure Tahoe, Hotel San Mateo and Hotel Foster City. 
---Background---
- I am a wealthy individual.
---Preferences---
- I don't like seafood.
- I like fine dining.
- I don't like public transportation.
```

*Output:*
```
Day 1:
- 9am: Check-in to Hotel Azure Tahoe.
- 10am: Visit the San Francisco Museum of Modern Art.
- 12pm: Stop for lunch at the R & G Lounge for some Chinese cuisine.
- 2pm: Take a cable car ride around the city.
- 4pm: Visit the San Francisco Botanical Garden.
- 6pm: Enjoy dinner at a fine dining restaurant, such as Gary Danko.

Day 2:
- 9am: Visit the Exploratorium. 
- 11am: Stop for lunch at the Golden Gate Park.
- 1pm: Visit the Palace of Fine Arts.
- 3pm: Head to the Aquarium of the Bay.
- 5pm: Enjoy dinner at a fine dining restaurant, such as Scoma's.
- 7pm: Check-in to Hotel San Mateo.

Day 3:
- 9am: Visit the Golden Gate Bridge.
- 11am: Stop for lunch at the Ferry Building Marketplace.
- 1pm: Visit the California Academy of Sciences.
- 3pm: Take a boat tour around the bay.
- 5pm: Enjoy dinner at a fine dining restaurant, such as The Rotunda.
- 7pm: Check-in to Hotel Foster City.
```
In the above example, we can see that the model has recommended a 3-day itinerary, with events noted out by hour of the day, for a wealthy individual who doesn't like seafood, or public transportation, but does prefer fine dining. The model has also recommended lodging options from Hotel Azure Tahoe, Hotel San Mateo, and Hotel Foster City as per requested.

Another possible scenario for utilizing a recommendation prompt is to provide a user with a list of items that they are likely to be interested in. For example, if a user is looking to purchase a new car, we can provide the model with a list of cars that the user is interested in, and the model can then provide a list of cars that the user is likely to be interested in. 

*Prompt:*
```
Provide a recommended car from the ---Possible Cars--- section based on the ---Previously Owned--- and the ---Customer Attributes--- section.
---Customer Attributes---
* Two adults as primary drivers
* Has two kids
* Owns an SUV
* Has a dog
* Takes road trips
---Previously Owned---
* Subaru Outback
* Nissan Altima
* Honda Accord
* Chrysler 300
---Possible Cars---
* Chevrolet Corvette
* Tesla Model X
* Toyota Sienna
* Jeep Grand Cherokee
```

*Output:*
```
Based on the customer attributes and previously owned vehicles, a recommended car from the Possible Cars section is the Toyota Sienna. It is an 8-passenger minivan with plenty of room for adults, children, a dog, and luggage for road trips. It has a good safety rating and plenty of features for a comfortable ride.
```
Given clearly defined parameters, the model is able to provide not only a recommendation, but also a justification for the recommendation.

---
[Previous Section (Data Generation)](./07_Data_Generation.md)

[Next Section (Advanced Concepts)](../03_Advanced_Concepts.md)