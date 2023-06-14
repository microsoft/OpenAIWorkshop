import azure.functions as func
import azure.durable_functions as df
import logging
import json
import os
from core import recommend_solution

myApp = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@myApp.route(route="append_conversation/{conversation_id}&&{utterance}")
@myApp.durable_client_input(client_name="client")
async def append_conversation(req: func.HttpRequest, client) -> func.HttpResponse:
    conversation_id = req.route_params.get('conversation_id')
    utterance = req.route_params.get('utterance')
    entity_id = df.EntityId("entity_function", conversation_id)
    instance_id = await client.signal_entity(entity_id, "add", utterance)
    return func.HttpResponse("Entity signaled")

@myApp.route(route="recommend/{conversation_id}")
@myApp.durable_client_input(client_name="client")
async def recommend(req: func.HttpRequest, client) -> func.HttpResponse:
    conversation_id = req.route_params.get('conversation_id')
    entity_id = df.EntityId("entity_function",conversation_id)
    entity_state_result = await client.read_entity_state(entity_id)
    
    if entity_state_result.entity_exists:
        entity_state = str(entity_state_result.entity_state)
        logging.info("conversation: "+ entity_state )
        solutions=recommend_solution(entity_state)
        return func.HttpResponse(str(solutions))
    else:
        return func.HttpResponse("no conversation found")

    

@myApp.entity_trigger(context_name="context")
def entity_function(context: df.DurableEntityContext):
    current_value = context.get_state(lambda: "")
    operation = context.operation_name
    if operation == "add":
        current_text = context.get_input()
        current_value = current_value + "\n" +current_text
    elif operation == "reset":
        current_value = ""
    elif operation == "get":
        context.set_result(current_value)
    context.set_state(current_value)


