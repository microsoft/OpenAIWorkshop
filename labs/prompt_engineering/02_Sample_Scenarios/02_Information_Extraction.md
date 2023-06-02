# Information Extraction

## Topics

- [Entity Extractions from Unstructured Data](#entity-extractions-from-unstructured-data)
- [Entity Extractions from Unstructured Data (Structured Output)](#entity-extractions-from-unstructured-data-structured-output)

---

## Entity Extractions from Unstructured Data

The OpenAI GPT models are capable of extracting entities from text. Let's look at a simple example to extract entities from a text. Remember that you can always control the output of a prompt via instructions.

*Prompt:*
```
Extract entities from this accident report:

Accident Report

Date: March 3, 2023 Time: 10:15 AM Location: Intersection of Hollywood Boulevard and Highland Avenue, Los Angeles, CA Involved parties: John Smith (truck driver) and Jane Doe (cyclist) Witnesses: Mark Lee (pedestrian) and Lisa Kim (store owner)

Summary:

John Smith was driving a white truck eastbound on Hollywood Boulevard, approaching the intersection with Highland Avenue. He had a green light and was traveling at about 25 mph. Jane Doe was riding a red bicycle northbound on Highland Avenue, crossing Hollywood Boulevard. She had a red light and was traveling at about 15 mph. She did not stop at the intersection and entered the path of the truck. John Smith applied his brakes but could not avoid hitting Jane Doe. Jane Doe was thrown off her bicycle and landed on the pavement. Mark Lee and Lisa Kim witnessed the accident from opposite corners of the intersection. They called 911 and rushed to help Jane Doe.

Injuries:

Jane Doe suffered a concussion, a broken arm, and several bruises and abrasions. She was conscious but disoriented at the scene. She was transported by ambulance to Cedars-Sinai Medical Center for treatment. John Smith was not injured but was shaken by the accident.

Damage:

The truck sustained minor damage to its front bumper and hood. The bicycle was severely damaged and rendered unusable.

Fault:

According to the traffic laws of California, Jane Doe was at fault for running a red light and failing to yield the right-of-way to John Smith. John Smith was not at fault for the accident.
```

*Output:*
```
Entities:

John Smith, Jane Doe, Mark Lee, Lisa Kim, white truck, red bicycle, Cedars-Sinai Medical Center, California, traffic laws.
```

---
## Entity Extractions from Unstructured Data (Structured Output)

Consider the potential to generate a structured output using the entities extracted from the text. For example, we can generate a structured output in the form of a JSON object.

*Prompt:*
```
Extract entities from this accident report as a well formed JSON document:

Accident Report

Date: March 3, 2023 Time: 10:15 AM Location: Intersection of Hollywood Boulevard and Highland Avenue, Los Angeles, CA Involved parties: John Smith (truck driver) and Jane Doe (cyclist) Witnesses: Mark Lee (pedestrian) and Lisa Kim (store owner)

Summary:

John Smith was driving a white truck eastbound on Hollywood Boulevard, approaching the intersection with Highland Avenue. He had a green light and was traveling at about 25 mph. Jane Doe was riding a red bicycle northbound on Highland Avenue, crossing Hollywood Boulevard. She had a red light and was traveling at about 15 mph. She did not stop at the intersection and entered the path of the truck. John Smith applied his brakes but could not avoid hitting Jane Doe. Jane Doe was thrown off her bicycle and landed on the pavement. Mark Lee and Lisa Kim witnessed the accident from opposite corners of the intersection. They called 911 and rushed to help Jane Doe.

Injuries:

Jane Doe suffered a concussion, a broken arm, and several bruises and abrasions. She was conscious but disoriented at the scene. She was transported by ambulance to Cedars-Sinai Medical Center for treatment. John Smith was not injured but was shaken by the accident.

Damage:

The truck sustained minor damage to its front bumper and hood. The bicycle was severely damaged and rendered unusable.

Fault:

According to the traffic laws of California, Jane Doe was at fault for running a red light and failing to yield the right-of-way to John Smith. John Smith was not at fault for the accident.
```

*Output:*
```
{
  "accidentReport": {
    "date": "March 3, 2023",
    "time": "10:15 AM",
    "location": {
      "street": "Intersection of Hollywood Boulevard and Highland Avenue",
      "city": "Los Angeles",
      "state": "CA"
    },
    "involvedParties": [
      {
        "name": "John Smith",
        "role": "truck driver"
      },
      {
        "name": "Jane Doe",
        "role": "cyclist"
      }
    ],
    "witnesses": [
      {
        "name": "Mark Lee",
        "role": "pedestrian"
      },
      {
        "name": "Lisa Kim",
        "role": "store owner"
      }
    ],
    "summary": "John Smith was driving a white truck eastbound on Hollywood Boulevard, approaching the intersection with Highland Avenue. He had a green light and was traveling at about 25 mph. Jane Doe was riding a red bicycle northbound on Highland Avenue, crossing Hollywood Boulevard. She had a red light and was traveling at about 15 mph. She did not stop at the intersection and entered the path of the truck. John Smith applied his brakes but could not avoid hitting Jane Doe. Jane Doe was thrown off her bicycle and landed on the pavement. Mark Lee and Lisa Kim witnessed the accident from opposite corners of the intersection. They called 911 and rushed to help Jane Doe.",
    "injuries": {
      "victim": {
        "name": "Jane Doe",
        "injuries": "concussion, broken arm, bruises and abrasions"
      },
      "other": {
        "name": "John Smith",
        "injuries": "none"
      }
    },
    "damage": {
      "truck": "minor damage to front bumper and hood",
      "bicycle": "severely damaged and rendered unusable"
    },
    "fault": "Jane Doe was at fault for running a red light and failing to yield the right-of-way to John Smith. John Smith was not at fault for the accident."
  }
}
```

**IMPORTANT NOTE**: You may have to increase the 'Max length (tokens)' parameter if the output gets cut off (you'll probably need to increase it to 500+ tokens).

Please note how comprehensive the output is. You'll most likely want to control the format of the output to fit your needs and existing systems. For this, One Shot or Few Shots learning are great techniques to consider. See [Advanced Concepts](../03_Advanced_Concepts.md) for more information.

---

[Previous Section (Text Summarization)](./01_Text_Summarization.md)

[Next Section (Question Answering)](./03_Question_Answering.md)
