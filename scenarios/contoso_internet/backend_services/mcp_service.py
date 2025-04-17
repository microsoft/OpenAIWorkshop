from fastmcp import FastMCP  
from typing import List, Optional  
from pydantic import BaseModel  
import sqlite3  
import os  
import json  
import math  
from datetime import datetime  
from dotenv import load_dotenv  
from openai import AzureOpenAI  
import asyncio
import logging
  
mcp = FastMCP(  
    name="Contoso Customer API as Tools",  
    instructions=(  
        "All info (including reads) is available via tools. Use provided parameters and schemas for arguments. "  
        "Results are JSON objects or lists of objects as shown in schemas."  
    ),  
)  
  
load_dotenv()  
DATABASE = "data/contoso.db"  
emb_engine = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")  
client = AzureOpenAI(  
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),  
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),  
)  
  
def get_db():  
    db = sqlite3.connect(DATABASE)  
    db.row_factory = sqlite3.Row  
    return db  
  
def get_embedding(text, model=emb_engine):  
    text = text.replace("\n", " ")  
    return client.embeddings.create(input=[text], model=model).data[0].embedding  
  
def cosine_similarity(vec1, vec2):  
    dot = sum(a * b for a, b in zip(vec1, vec2))  
    norm1 = math.sqrt(sum(a * a for a in vec1))  
    norm2 = math.sqrt(sum(b * b for b in vec2))  
    return dot / (norm1 * norm2) if norm1 and norm2 else 0  
  
# --- Pydantic Schemas ---  
  
class CustomerSummary(BaseModel):  
    customer_id: int  
    first_name: str  
    last_name: str  
    email: str  
    loyalty_level: str  
  
class CustomerDetail(BaseModel):  
    customer_id: int  
    first_name: str  
    last_name: str  
    email: str  
    phone: Optional[str]  
    address: Optional[str]  
    loyalty_level: str  
    subscriptions: List[dict] # List of subscriptions (flattened)  
  
class SubscriptionDetail(BaseModel):  
    subscription_id: int  
    product_id: int  
    start_date: str  
    end_date: str  
    status: str  
    roaming_enabled: int  
    service_status: str  
    product_name: str  
    product_description: Optional[str]  
    category: Optional[str]  
    monthly_fee: Optional[float]  
    invoices: List[dict]  
    service_incidents: List[dict]  
  
class Promotion(BaseModel):  
    promotion_id: int  
    product_id: int  
    name: str  
    description: str  
    eligibility_criteria: Optional[str]  
    start_date: str  
    end_date: str  
    discount_percent: Optional[int]  
  
class KBSearchParams(BaseModel):  
    query: str  
    topk: Optional[int] = 3  
  
class KBDoc(BaseModel):  
    title: str  
    doc_type: str  
    content: str  
  
class SecurityLog(BaseModel):  
    log_id: int  
    event_type: str  
    event_timestamp: str  
    description: str  
  
class Order(BaseModel):  
    order_id: int  
    order_date: str  
    product_name: str  
    amount: float  
    order_status: str  
  
class SubscriptionUpdateRequest(BaseModel):  
    roaming_enabled: Optional[int] = None  
    status: Optional[str] = None  
    service_status: Optional[str] = None  
    product_id: Optional[int] = None  
    start_date: Optional[str] = None  
    end_date: Optional[str] = None  
  
# --- TOOL ARGUMENT MODELS ---  
  
class CustomerIdParam(BaseModel):  
    customer_id: int  
  
class SubscriptionIdParam(BaseModel):  
    subscription_id: int  
  
# --- TOOL ENDPOINTS (formerly resources) ---  
  
@mcp.tool(description="Get all customers (basic info)")  
def get_all_customers() -> List[CustomerSummary]:  
    db = get_db()  
    cur = db.execute("SELECT customer_id, first_name, last_name, email, loyalty_level FROM Customers")  
    rows = cur.fetchall()  
    db.close()  
    return [CustomerSummary(**dict(row)) for row in rows]  
  
@mcp.tool(description="Get full profile for a customer, with subscriptions")  
def get_customer_detail(params: CustomerIdParam) -> CustomerDetail:  
    print(f"Fetching details for customer ID: {params.customer_id}")
    db = get_db()  
    cur = db.execute("SELECT customer_id, first_name, last_name, email, phone, address, loyalty_level FROM Customers WHERE customer_id = ?", (params.customer_id,))  
    customer = cur.fetchone()  
    if not customer:  
        db.close()  
        raise ValueError(f"Customer ID {params.customer_id} not found")  
    customer_dict = dict(customer)  
    cur2 = db.execute("SELECT subscription_id, product_id, start_date, end_date, status, roaming_enabled, service_status FROM Subscriptions WHERE customer_id = ?", (params.customer_id,))  
    subscriptions = [dict(row) for row in cur2.fetchall()]  
    db.close()  
    return CustomerDetail(**customer_dict, subscriptions=subscriptions)  
  
@mcp.tool(description="Get details for a subscription, with invoices and service incidents")  
def get_subscription_detail(params: SubscriptionIdParam) -> SubscriptionDetail:  
    db = get_db()  
    cur = db.execute(  
        """SELECT s.subscription_id, s.product_id, s.start_date, s.end_date, s.status, s.roaming_enabled, s.service_status,  
                  p.name as product_name, p.description as product_description, p.category, p.monthly_fee  
           FROM Subscriptions s  
           JOIN Products p ON s.product_id = p.product_id  
           WHERE s.subscription_id = ?""",  
        (params.subscription_id,),  
    )  
    sub = cur.fetchone()  
    if not sub:  
        db.close()  
        raise ValueError(f"Subscription ID {params.subscription_id} not found")  
    sub_dict = dict(sub)  
    cur2 = db.execute("SELECT invoice_id, invoice_date, amount, description FROM Invoices WHERE subscription_id = ?", (params.subscription_id,))  
    invoices = [dict(row) for row in cur2.fetchall()]  
    cur3 = db.execute("SELECT incident_id, incident_date, description, resolution_status FROM ServiceIncidents WHERE subscription_id = ?", (params.subscription_id,))  
    service_incidents = [dict(row) for row in cur3.fetchall()]  
    db.close()  
    return SubscriptionDetail(**sub_dict, invoices=invoices, service_incidents=service_incidents)  
  
@mcp.tool(description="Get all active promotions")  
def get_promotions() -> List[Promotion]:  
    db = get_db()  
    cur = db.execute("SELECT promotion_id, product_id, name, description, eligibility_criteria, start_date, end_date, discount_percent FROM Promotions")  
    promos = [Promotion(**dict(row)) for row in cur.fetchall()]  
    db.close()  
    return promos  
  
@mcp.tool(description="Perform a semantic knowledge base search for relevant documents")  
def search_knowledge_base(params: KBSearchParams) -> List[KBDoc]:  
    db = get_db()  
    query_embedding = get_embedding(params.query)  
    cur = db.execute("SELECT title, doc_type, content, topic_embedding FROM KnowledgeDocuments")  
    rows = cur.fetchall()  
    db.close()  
    results = []  
    for row in rows:  
        try:  
            stored_embed = json.loads(row["topic_embedding"])  
            sim = cosine_similarity(query_embedding, stored_embed)  
        except Exception:  
            continue  
        results.append({  
            "title": row["title"],  
            "doc_type": row["doc_type"],  
            "content": row["content"],  
            "similarity": sim  
        })  
    top_results = sorted(results, key=lambda x: x["similarity"], reverse=True)[:params.topk]  
    return [  
        KBDoc(title=r["title"], doc_type=r["doc_type"], content=r["content"])  
        for r in top_results  
    ]  
  
@mcp.tool(description="Get security logs/events for a customer")  
def get_security_logs(params: CustomerIdParam) -> List[SecurityLog]:  
    db = get_db()  
    cur = db.execute(  
        """SELECT log_id, event_type, event_timestamp, description  
           FROM SecurityLogs WHERE customer_id = ?  
           ORDER BY event_timestamp DESC""",  
        (params.customer_id,),  
    )  
    logs = [SecurityLog(**dict(row)) for row in cur.fetchall()]  
    db.close()  
    return logs  
  
@mcp.tool(description="Get list of orders for a customer")  
def get_customer_orders(params: CustomerIdParam) -> List[Order]:  
    try:
        db = get_db()  
        cur = db.execute(  
            """SELECT o.order_id, o.order_date, p.name as product_name, o.amount, o.order_status  
            FROM Orders o  
            JOIN Products p ON o.product_id = p.product_id  
            WHERE o.customer_id = ?  
            ORDER BY o.order_date DESC""",  
            (params.customer_id,),  
        )  
        orders = [Order(**dict(row)) for row in cur.fetchall()]  
        db.close()  
    except sqlite3.Error as e:
        logging.error(f"SQLite error: {e}")
        db.close()
        orders = []  # Return an empty list if there's an error
    return orders  
  
@mcp.tool(description="Update fields in an existing subscription (roaming, status, product, etc.)")  
def update_subscription(subscription_id: int, update: SubscriptionUpdateRequest) -> dict:  
    db = get_db()  
    data = update.dict(exclude_unset=True)  
    if not data:  
        db.close()  
        raise ValueError("No valid fields to update")  
    fields_to_update = [f"{k} = ?" for k in data]  
    params = list(data.values()) + [subscription_id]  
    query = f"UPDATE Subscriptions SET {', '.join(fields_to_update)} WHERE subscription_id = ?"  
    cur = db.execute(query, params)  
    db.commit()  
    db.close()  
    if cur.rowcount == 0:  
        raise ValueError("Subscription not found")  
    return {"message": "Subscription updated successfully"}  
  
@mcp.tool(description="Unlock a customer's account if it is currently locked")  
def unlock_account(params: CustomerIdParam) -> dict:  
    db = get_db()  
    cur = db.execute(  
        """SELECT * FROM SecurityLogs WHERE customer_id = ? AND event_type = 'account_locked'  
           ORDER BY event_timestamp DESC LIMIT 1""",  
        (params.customer_id,),  
    )  
    row = cur.fetchone()  
    if not row:  
        db.close()  
        raise ValueError("No lock event found or account already unlocked")  
    unlock_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  
    db.execute(  
        """INSERT INTO SecurityLogs (customer_id, event_type, event_timestamp, description)  
           VALUES (?, 'account_unlocked', ?, 'Account unlocked via request')""",  
        (params.customer_id, unlock_time),  
    )  
    db.commit()  
    db.close()  
    return {"message": "Account unlocked successfully"}  
# ====== SERVER RUN ===========  
if __name__ == "__main__":  
    # mcp.run()  
    # To run with SSE web server:  
    asyncio.run(mcp.run_sse_async(host="0.0.0.0", port=8000))