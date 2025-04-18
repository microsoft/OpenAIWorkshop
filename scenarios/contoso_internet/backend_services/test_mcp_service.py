#!/usr/bin/env python3  
"""  
Smoke‑tests the FastMCP server exposed in mcp_services.py.  
  
The helper exercises (read‑only + mutating) tools that cover every table used  
by the nine deterministic scenarios.  
  
Run:  
  
    export MCP_URL=http://127.0.0.1:8000/sse      # override if needed  
    python smoke_test_mcp.py  
"""  
  
import os, asyncio, logging, json  
from typing import Any, List, Dict  
  
from fastmcp import Client  
from fastmcp.exceptions import ClientError  
  
MCP_URL = os.getenv("MCP_URL", "http://127.0.0.1:8000/sse")  
  
logging.basicConfig(  
    level=logging.INFO, format="%(levelname)s | %(message)s", force=True  
)  
  
  
# ──────────────────────────  utilities  ────────────────────────────────  
def _to_native(content) -> Any:  
    """Return native python object (dict/list/str) regardless of TextContent/JsonContent"""  
    try:  
        return content.as_json()  
    except Exception:  
        try:  
            return json.loads(content.text)  
        except Exception:  
            return content.text  
  
  
def print_result(title: str, success: bool, data: Any = None, error: Exception | str = None):  
    if success:  
        logging.info("[PASS] %s", title)  
        if data is not None:  
            logging.debug("    → %s", repr(data)[:300])  
    else:  
        logging.error("[FAIL] %s", title)  
        if error:  
            logging.error("       error: %s", error)  
        if data is not None:  
            logging.debug("       data : %s", repr(data)[:300])  
  
  
# ───────────────────────  individual tests  ────────────────────────────  
async def test_get_all_customers(client: Client) -> List[Dict[str, Any]] | None:  
    title = "get_all_customers"  
    try:  
        res = await client.call_tool("get_all_customers")  
        data = _to_native(res[0])  
        ok = isinstance(data, list) and data  
        print_result(title, ok, data[:2])  
        return data  
    except Exception as e:  
        print_result(title, False, error=e)  
  
  
async def test_customer_detail(client: Client, cust_id: int):  
    title = f"get_customer_detail({cust_id})"  
    try:  
        res = await client.call_tool("get_customer_detail", {"customer_id": cust_id})  
        data = _to_native(res[0])  
        print_result(title, isinstance(data, dict), data)  
    except Exception as e:  
        print_result(title, False, error=e)  
  
  
async def test_subscription_detail(client: Client, sub_id: int):  
    title = f"get_subscription_detail({sub_id})"  
    try:  
        res = await client.call_tool("get_subscription_detail", {"subscription_id": sub_id})  
        data = _to_native(res[0])  
        print_result(title, isinstance(data, dict), data)  
    except Exception as e:  
        print_result(title, False, error=e)  
  
  
async def test_promotions(client: Client):  
    title = "get_promotions"  
    try:  
        res = await client.call_tool("get_promotions")  
        data = _to_native(res[0])  
        print_result(title, isinstance(data, list), data)  
    except Exception as e:  
        print_result(title, False, error=e)  
  
  
async def test_eligible_promos(client: Client, cust_id: int):  
    title = f"get_eligible_promotions({cust_id})"  
    try:  
        res = await client.call_tool("get_eligible_promotions", {"customer_id": cust_id})  
        data = _to_native(res[0])  
        print_result(title, isinstance(data, list), data)  
    except Exception as e:  
        print_result(title, False, error=e)  
  
  
async def test_kb_search(client: Client, query: str):  
    title = f"search_knowledge_base('{query}')"  
    try:  
        res = await client.call_tool("search_knowledge_base", {"query": query, "topk": 2})  
        data = [_to_native(c) for c in res]  
        ok = isinstance(data, list) and data  
        print_result(title, ok, data)  
    except Exception as e:  
        print_result(title, False, error=e)  
  
  
async def test_security_logs(client: Client, cust_id: int):  
    title = f"get_security_logs({cust_id})"  
    try:  
        res = await client.call_tool("get_security_logs", {"customer_id": cust_id})  
        data = _to_native(res[0])  
        ok = isinstance(data, list)  
        print_result(title, ok, data[:3])  
    except Exception as e:  
        print_result(title, False, error=e)  
  
  
async def test_orders(client: Client, cust_id: int):  
    title = f"get_customer_orders({cust_id})"  
    try:  
        res = await client.call_tool("get_customer_orders", {"customer_id": cust_id})  
        data = _to_native(res[0])  
        ok = isinstance(data, list)  
        print_result(title, ok, data[:2])  
    except Exception as e:  
        print_result(title, False, error=e)  
  
  
async def test_data_usage(client: Client, sub_id: int):  
    title = f"get_data_usage({sub_id}) aggregate"  
    try:  
        res = await client.call_tool(  
            "get_data_usage",  
            {  
                "subscription_id": sub_id,  
                "start_date": "2023-01-01",  
                "end_date": "2099-01-01",  
                "aggregate": True,  
            },  
        )  
        data = _to_native(res[0])  
        print_result(title, isinstance(data, dict), data)  
    except Exception as e:  
        print_result(title, False, error=e)  
  
  
async def test_billing_summary(client: Client, cust_id: int):  
    title = f"get_billing_summary({cust_id})"  
    try:  
        res = await client.call_tool("get_billing_summary", {"customer_id": cust_id})  
        data = _to_native(res[0])  
        ok = isinstance(data, dict) and "total_due" in data  
        print_result(title, ok, data)  
    except Exception as e:  
        print_result(title, False, error=e)  
  
  
async def test_update_subscription(client: Client, sub_id: int):  
    title = f"update_subscription({sub_id}) set status=inactive"  
    try:  
        res = await client.call_tool(  
            "update_subscription",  
            {"subscription_id": sub_id, "update": {"status": "inactive"}},  
        )  
        data = _to_native(res[0])  
        ok = "updated_fields" in data  
        print_result(title, ok, data)  
    except Exception as e:  
        print_result(title, False, error=e)  
  
  
async def test_unlock_account(client: Client, cust_id: int):  
    title = f"unlock_account({cust_id})"  
    try:  
        res = await client.call_tool("unlock_account", {"customer_id": cust_id})  
        data = _to_native(res[0])  
        ok = "unlocked" in str(data).lower()  
        print_result(title, ok, data)  
    except ClientError as e:  
        print_result(title, False, error=f"ClientError {e}")  
    except Exception as e:  
        print_result(title, False, error=e)  
  
  
# ─────────────────────────────  main runner  ────────────────────────────  
async def run_tests():  
    async with Client(MCP_URL) as client:  
        logging.info("Running FastMCP smoke‑tests against %s", MCP_URL)  
  
        customers = await test_get_all_customers(client)  
        sample_cust = customers[0]["customer_id"] if customers else 1  
  
        await test_customer_detail(client, sample_cust)  
        await test_customer_detail(client, 999999)          # expected fail  
  
        # pick first subscription for that customer  
        detail_res = await client.call_tool("get_customer_detail", {"customer_id": sample_cust})  
        subs = _to_native(detail_res[0]).get("subscriptions", [])  
        sample_sub = subs[0]["subscription_id"] if subs else 1  
  
        await test_subscription_detail(client, sample_sub)  
        await test_subscription_detail(client, 987654)      # expected fail  
  
        # generic reads  
        await test_promotions(client)  
        await test_eligible_promos(client, sample_cust)  
        await test_kb_search(client, "Invoice Adjustment Policy")  
        await test_security_logs(client, sample_cust)  
        await test_orders(client, sample_cust)  
        await test_data_usage(client, sample_sub)  
        await test_billing_summary(client, sample_cust)  
  
        # mutating endpoints  
        await test_update_subscription(client, sample_sub)  
        await test_unlock_account(client, sample_cust)  
  
  
# ──────────────────────────────  CLI  ───────────────────────────────────  
if __name__ == "__main__":  
    asyncio.run(run_tests())  