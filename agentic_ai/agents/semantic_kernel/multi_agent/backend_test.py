import requests

# Backend URL (adjust if using a different port)
url = "http://localhost:7000/chat"

# Prepare your payload with session_id and user prompt
data = {
    "session_id": "test_session_1",
    "prompt": "what was my last subscription for customer ID 103?"
}

# Make the POST request to the backend
response = requests.post(url, json=data)

# Print the response
print("Response:", response.json())
