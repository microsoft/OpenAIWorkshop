# Text Summarization

## Topics

- [Unstructured Text Summarization](#unstructured-text-summarization)
- [Semi-Structured Text Summarization](#semi-structured-text-summarization)

---

## Unstructured Text Summarization

Let's look at a simple example to summarize a text. Remember that you can always control the output of a prompt via instructions, some typical controls are around:
- length of the summary
- target audience of the summary

*Prompt:*
```
Summarize this for a second-grade student:

Jupiter is the fifth planet from the Sun and the largest in the Solar System. It is a gas giant with a mass one-thousandth that of the Sun, but two-and-a-half times that of all the other planets in the Solar System combined. Jupiter is one of the brightest objects visible to the naked eye in the night sky, and has been known to ancient civilizations since before recorded history. It is named after the Roman god Jupiter. When viewed from Earth, Jupiter can be bright enough for its reflected light to cast visible shadows, and is on average the third-brightest natural object in the night sky after the Moon and Venus.
```

*Output:*
```
Jupiter is the fifth planet from the Sun and is very big and bright. It can be seen with our eyes in the night sky and it has been known since ancient times. Its name comes from the Roman god Jupiter. It is usually the third brightest object in the night sky after the Moon and Venus.
```

Let's change the prompt to specify the length of the summary to be 3 sentences.

*Prompt:*
```
Summarize this for a second-grade student in 3 sentences:

Jupiter is the fifth planet from the Sun and the largest in the Solar System. It is a gas giant with a mass one-thousandth that of the Sun, but two-and-a-half times that of all the other planets in the Solar System combined. Jupiter is one of the brightest objects visible to the naked eye in the night sky, and has been known to ancient civilizations since before recorded history. It is named after the Roman god Jupiter. When viewed from Earth, Jupiter can be bright enough for its reflected light to cast visible shadows, and is on average the third-brightest natural object in the night sky after the Moon and Venus.
```

*Output:*
```
Jupiter is the fifth planet from the Sun and the biggest in the Solar System. It is very bright and can be seen in the night sky. It is named after the Roman god Jupiter.
```

Let's now change the prompt to specify the target audience of the summary to be a physicist.

*Prompt:*
```
Summarize this for a physicist in 3 sentences:

Jupiter is the fifth planet from the Sun and the largest in the Solar System. It is a gas giant with a mass one-thousandth that of the Sun, but two-and-a-half times that of all the other planets in the Solar System combined. Jupiter is one of the brightest objects visible to the naked eye in the night sky, and has been known to ancient civilizations since before recorded history. It is named after the Roman god Jupiter. When viewed from Earth, Jupiter can be bright enough for its reflected light to cast visible shadows, and is on average the third-brightest natural object in the night sky after the Moon and Venus.
```

*Output:*
```
Jupiter is the fifth planet from the Sun and the largest in the Solar System. It is a gas giant with a mass two-and-a-half times that of all the other planets combined. It is visible to the naked eye in the night sky and has been known since before recorded history, being named after the Roman god Jupiter.
```

## Semi-Structured Text Summarization

You can easily control the format of the summarization as well to fit into desired formats. Let's summarize the same text in a bullet point format.

*Prompt:*
```
Summarize this for a second-grade student in 3 sentences in bullet points:

Jupiter is the fifth planet from the Sun and the largest in the Solar System. It is a gas giant with a mass one-thousandth that of the Sun, but two-and-a-half times that of all the other planets in the Solar System combined. Jupiter is one of the brightest objects visible to the naked eye in the night sky, and has been known to ancient civilizations since before recorded history. It is named after the Roman god Jupiter. When viewed from Earth, Jupiter can be bright enough for its reflected light to cast visible shadows, and is on average the third-brightest natural object in the night sky after the Moon and Venus.
```

*Output:*
```
- Jupiter is the fifth planet from the Sun and the largest in the Solar System.
- It is a gas giant and is very bright in the night sky.
- It is named after the Roman god Jupiter.
```

*Prompt:*
```
Summarize this for a second-grade student as a title and a one sentence abstract:

Jupiter is the fifth planet from the Sun and the largest in the Solar System. It is a gas giant with a mass one-thousandth that of the Sun, but two-and-a-half times that of all the other planets in the Solar System combined. Jupiter is one of the brightest objects visible to the naked eye in the night sky, and has been known to ancient civilizations since before recorded history. It is named after the Roman god Jupiter. When viewed from Earth, Jupiter can be bright enough for its reflected light to cast visible shadows, and is on average the third-brightest natural object in the night sky after the Moon and Venus.
```

*Output:*
```
Title: Jupiter, the Brightest Planet
Abstract: Jupiter is the fifth planet from the Sun and is the brightest object in the night sky, visible to the naked eye and known since before recorded history.
```

---

[Previous Section (Introduction to Prompt Engineering)](../01_Prompt_Introduction.md)

[Next Section (Information Extraction)](./02_Information_Extraction.md)