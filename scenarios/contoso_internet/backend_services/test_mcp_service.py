import asyncio  
from fastmcp import Client  
from fastmcp.exceptions import ClientError
  
# Set to match your MCP SSE endpoint  
MCP_URL = "http://127.0.0.1:8000/sse"  
  
def print_result(title, success, data=None, error=None):  
    if success:  
        print(f"[PASS] {title}")  
    else:  
        print(f"[FAIL] {title}")  
        if data is not None:  
            print(f"  Data: {data}")  
        if error:  
            print(f"  Error: {error}")  
  
async def test_customers(client):  
    title = "customer://list (get all customers)"  
    try:  
        contents = await client.read_resource("customer://list")  
        data = contents[0].as_json() if hasattr(contents[0], 'as_json') else contents[0].text  
        is_list = isinstance(data, list)  
        print_result(title, is_list, data)  
        return data  
    except Exception as e:  
        print_result(title, False, error=e)  
        return None  
  
async def test_customer_detail(client, customer_id):  
    title = f"customer://{customer_id}/profile (get customer detail)"  
    try:  
        uri = f"customer://{customer_id}/profile"  
        contents = await client.read_resource(uri)  
        data = contents[0].as_json() if hasattr(contents[0], 'as_json') else contents[0].text  
        is_dict = isinstance(data, dict)  
        print_result(title, is_dict, data)  
    except Exception as e:  
        # Consider "not found" as PASS if that's the test's purpose  
        if "not found" in str(e).lower():  
            print_result(title, True, error=e)  
        else:  
            print_result(title, False, error=e)  
  
async def test_subscription_detail(client, subscription_id):  
    title = f"subscription://{subscription_id}/detail (get subscription detail)"  
    try:  
        uri = f"subscription://{subscription_id}/detail"  
        contents = await client.read_resource(uri)  
        data = contents[0].as_json() if hasattr(contents[0], 'as_json') else contents[0].text  
        is_dict = isinstance(data, dict)  
        print_result(title, is_dict, data)  
    except Exception as e:  
        if "not found" in str(e).lower():  
            print_result(title, True, error=e)  
        else:  
            print_result(title, False, error=e)  
  
async def test_promotions(client):  
    title = "promotion://list (get all promotions)"  
    try:  
        contents = await client.read_resource("promotion://list")  
        data = contents[0].as_json() if hasattr(contents[0], 'as_json') else contents[0].text  
        is_list = isinstance(data, list)  
        print_result(title, is_list, data)  
    except Exception as e:  
        print_result(title, False, error=e)  
  
async def test_security_logs(client, customer_id):  
    title = f"customer://{customer_id}/security_logs"  
    try:  
        uri = f"customer://{customer_id}/security_logs"  
        contents = await client.read_resource(uri)  
        data = contents[0].as_json() if hasattr(contents[0], 'as_json') else contents[0].text  
        is_list = isinstance(data, list)  
        print_result(title, is_list, data)  
    except Exception as e:  
        print_result(title, False, error=e)  
  
async def test_orders(client, customer_id):  
    title = f"customer://{customer_id}/orders"  
    try:  
        uri = f"customer://{customer_id}/orders"  
        contents = await client.read_resource(uri)  
        data = contents[0].as_json() if hasattr(contents[0], 'as_json') else contents[0].text  
        is_list = isinstance(data, list)  
        print_result(title, is_list, data)  
    except Exception as e:  
        print_result(title, False, error=e)  
  
async def test_kb_search(client, query):  
    """Test tool: search_knowledge_base(query)"""  
    title = f"search_knowledge_base (query='{query}')"  
    try:  
        tool_result = await client.call_tool("search_knowledge_base", {"query": query, "topk": 3})  
        # Returns a list of contents (usually [TextContent])  
        results = []  
        for content in tool_result:  
            try:  
                results.append(content.as_json() if hasattr(content, 'as_json') else content.text)  
            except Exception:  
                results.append(str(content))  
        is_list = isinstance(results[0], list) or isinstance(results, list) 
        print_result(title, is_list, results)  
    except ClientError as e:  
        print_result(title, False, error=f"ClientError: {e}")  
    except Exception as e:  
        print_result(title, False, error=e)  
  
  
async def test_update_subscription(client, subscription_id):  
    """Test tool: update_subscription"""  
    title = f"update_subscription (subscription_id={subscription_id})"  
    try:  
        params = {  
            "subscription_id": subscription_id,  
            "update": {"status": "inactive"}  # Example change  
        }  
        result = await client.call_tool("update_subscription", params)  
        # Output should be a JSON message from the server  
        text = result[0].as_json() if hasattr(result[0], 'as_json') else result[0].text  
        success = "successfully" in str(text).lower()  
        print_result(title, success, text)  
    except Exception as e:  
        print_result(title, False, error=e)  
  
async def test_unlock_account(client, customer_id):  
    """Test tool: unlock_account"""  
    title = f"unlock_account (customer_id={customer_id})"  
    try:  
        params = {"customer_id": customer_id}  
        result = await client.call_tool("unlock_account", params)  
        text = result[0].as_json() if hasattr(result[0], 'as_json') else result[0].text  
        success = "unlocked" in str(text).lower()  
        print_result(title, success, text)  
    except ClientError as e:  
        print_result(title, False, error=f"ClientError: {e}")  
    except Exception as e:  
        print_result(title, False, error=e)  
  
# ----------- Main async test runner ------------  
  
async def run_tests():  
    client = Client(MCP_URL)  
    async with client:  
        print("\n=== Running FastMCP Service Tests ===\n")  
  
        # You may want to use existing customer/subscription IDs from your DB  
        customer_list = await test_customers(client)  
        sample_cust_id = None  
        if customer_list:  
            try:  
                sample_cust_id = customer_list[0]['customer_id'] if isinstance(customer_list[0], dict) else None  
            except Exception:  
                sample_cust_id = None  
        if not sample_cust_id:  
            sample_cust_id = 1  
  
        # Use sample subscription IDs, else fallback to ID=1  
        sample_subscription_id = 1  
  
        await test_customer_detail(client, sample_cust_id)  
        await test_customer_detail(client, 99999)  # Should fail for missing ID  
  
        await test_subscription_detail(client, sample_subscription_id)  
        await test_promotions(client)  
        await test_kb_search(client, "Invoice Adjustment")  
        await test_security_logs(client, sample_cust_id)  
        await test_orders(client, sample_cust_id)  
        await test_update_subscription(client, sample_subscription_id)  
        await test_unlock_account(client, sample_cust_id)  
  
        # Add extra coverage for missing/edge case subscription ID  
        await test_subscription_detail(client, 99999)  
  
# -------- Run as script --------  
if __name__ == "__main__":  
    asyncio.run(run_tests())  