"""  
Quick sanity check: talks to the A2A wrapper at :9100 and exercises all  
operations.  Requires the underlying Fast-MCP logistics server to be  
running.  
"""  
import asyncio  
import json  
from uuid import uuid4  
  
import httpx  
from a2a.client import A2ACardResolver,A2AClient
from a2a.types import MessageSendParams, SendMessageRequest  
from typing import Any, Dict, List, Optional  
  
BASE_URL = "http://localhost:9100"  
  
  
async def send(client: A2AClient, payload: dict) -> dict:  
    req = SendMessageRequest(  
        id=str(uuid4()),  
        params=MessageSendParams(  
            message={  
                "role": "user",  
                "parts": [{"kind": "text", "text": json.dumps(payload)}],  
                "messageId": uuid4().hex,  
            }  
        ),  
    )  
    resp = await client.send_message(req)  
    print(f"Response: {resp}")
    output = resp.model_dump(mode='json', exclude_none=True)
    return output.get("result", {}).get("parts", [{}])[0].get("text", "{}")
  
  
async def main() -> None:  
    async with httpx.AsyncClient(timeout=60) as httpx_client:  
        # Discover agent card & create client  
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=BASE_URL)  
        card = await resolver.get_agent_card()  
        print("Agent Card\n----------")
        card = await resolver.get_agent_card()  
        print(card.model_dump_json(indent=2, exclude_none=True)
)
        client = A2AClient(httpx_client=httpx_client, agent_card=card)  
  

        send_message_payload: dict[str, Any] = {
        'message': {
            'role': 'user',
            'parts': [
                {'kind': 'text', 'text': 'Give me a few available slots for a pick-up from 1 Microsoft Way, Redmond WA between 2025-10-15 and 2025-10-19 .'}
            ],
            'messageId': uuid4().hex,
        },
    }
        request = SendMessageRequest(
            id=str(uuid4()), params=MessageSendParams(**send_message_payload)
        )

        response = await client.send_message(request)
        print(response.model_dump(mode='json', exclude_none=True))


        task_id = response.root.result.taskId
        text_content = response.model_dump(mode='json', exclude_none=True)['result']['parts'][0]['text']
        print("Text content:", text_content)


        contextId =response.root.result.contextId

        second_send_message_payload_multiturn: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {'kind': 'text', 'text': 'Ok, schedule a pick-up for same address on 2025-10-16 at 10:00 am'}
                ],
                'messageId': uuid4().hex,
                'taskId':task_id,
                'contextId': contextId
            },
        }

        second_request = SendMessageRequest(
            id=str(uuid4()), params=MessageSendParams(**second_send_message_payload_multiturn)
        )
        second_response = await client.send_message(second_request)
        print(second_response.model_dump(mode='json', exclude_none=True))

  
if __name__ == "__main__":  
    asyncio.run(main())  