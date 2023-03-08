# Code Generation

## Topics

- [Overview of Code Generation](#overview-of-code-generation)
- [Parameters Setup](#parameters-setup)
- [Python Code Generation](#python-code-generation)
- [Code Translation](#code-translation)
- [SQL Code Generation](#sql-code-generation)

---

## Overview of Code Generation

You probably have heard already of [GitHub Copilot](https://github.com/features/copilot), a new AI-powered code completion tool that can write code for you.

Code generation is the process of creating executable code from natural language, comments, or other forms of input.

The OpenAI Davinci codex (code-davinci-002 for instance) is a powerful AI model that can understand and generate code in various programming languages. It is based on a large-scale neural network trained on billions of lines of public code and natural language data.

This codex can be used for a variety of tasks such as completing code snippets, explaining code functionality, converting code between languages, and creating web applications. It can also interact with users through natural language queries and provide feedback and suggestions.

## Parameters Setup

**Note:** Switch your Deployments to a 'code-davinci-002' model.

**Note:** Increase the Max Length (tokens) variable slider to 1,200 tokens to allow for longer code outputs to be generated for your use cases.

**Note**: Please setup a "stop sequences" item in the prompt to let the model know when to stop generating code. For example, you can add the following to the prompt: "#" (type # and then press 'tab' to enable that stop sequence). The model will look at your prompt to complete the prompt but will not try to continue to generate more output based on the prompt 'context'.

## Python Code Generation

*Prompt:*
```
# write a python function which adds all days between 2010-01-01 and the current date
# the function should take no input, and evaluate the current date when called
```

*Output:*
```
def days_since_2010():
    today = datetime.date.today()
    day_2010 = datetime.date(2010, 1, 1)
    return (today - day_2010).days
```

Feel free to test removing the Stop Sequence to understand its impact on the output and the problems it's causing.

## Code Translation

You can also leverage the coding capabilities of the codex to translate code from one language to another. For example, you can translate Python code to C++.

*Prompt:*
```
# Translate the following python code to C++
def days_since_2010():
    today = datetime.date.today()
    day_2010 = datetime.date(2010, 1, 1)
    return (today - day_2010).days
#

public 
```

*Output:*
```
public int days_since_2010() {
    Date today = new Date();
    Date day_2010 = new Date(2010, 1, 1);
    return (today - day_2010).days;
}
```


## SQL Code Generation

Writing proper SQL code does require knowledge of a schema, so part of the context provided to the prompt should include the necessary table definitions.

*Prompt:*
```
# MySQL tables, with their properties:
# Table customers, columns = [CustomerId, FirstName, LastName, Company, Address, City, State, Country, PostalCode, Phone, Fax, Email, SupportRepId]
# Create a MySQL query for all customers in Texas named Jane

SELECT 
```

*Output:*
```
SELECT * FROM customers WHERE State = 'Texas' AND FirstName = 'Jane'
```

*Prompt:*
```
# Table albums, columns = [AlbumId, Title, ArtistId]
# Table artists, columns = [ArtistId, Name]
# Table media_types, columns = [MediaTypeId, Name]
# Table playlists, columns = [PlaylistId, Name]
# Table playlist_track, columns = [PlaylistId, TrackId]
# Table tracks, columns = [TrackId, Name, AlbumId, MediaTypeId, GenreId, Composer, Milliseconds, Bytes, UnitPrice]

# Create a query for all albums with more than 10 tracks.

SELECT 
```

*Output:*
```
SELECT a.Title AS Album, COUNT(t.TrackId) AS Tracks
FROM albums a
INNER JOIN tracks t ON a.AlbumId = t.AlbumId
GROUP BY a.Title
HAVING COUNT(t.TrackId) > 10
```

You can leverage the power of this codex for more advanced scenarios like helping you refactor code, document code, create unit tests and more. Remember that you can provide as much context as needed to the prompt to help the codex generate the code you need.

**Note:** Switch your 'Deployments' back to a 'text-davinci-002' or 'text-davinci-003' model for the rest of the scenarios.

---

[Previous Section (Conversation)](./05_Conversation.md)

[Next Section (Data Generation)](./07_Data_Generation.md)