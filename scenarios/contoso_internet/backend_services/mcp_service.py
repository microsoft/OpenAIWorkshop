"""  
Contoso Customer API - Model Context Protocol (MCP) Implementation  
  
This MCP server exposes customer, subscription, promotion, knowledge base, and security logs functionality  
for use by LLM assistants and other MCP clients, using FastMCP.  
"""  
  
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
  
# ====== MCP SERVER INIT =======  
mcp = FastMCP(  
    name="Contoso Customer API",  
    instructions=(  
        "Provides customer, subscriptions, promotions, knowledge base, and security logs. "  
        "Use resources to fetch info (customer://...), tools to perform actions (unlock_account, update_subscription), "  
        "and search_knowledge_base for semantic KB search. All results are JSON-encoded."  
    ),  
)  
  
# ====== ENV & OPENAI CLIENT  =======  
load_dotenv()  
DATABASE = "data/contoso.db"  
  
# Load OpenAI deployment/environment details from .env or environment  
chat_engine = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  
emb_engine = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")  
client = AzureOpenAI(  
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),  
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),  
)  
  
# ====== DATA MODELS (reuseable everywhere)  =======  
class CustomerBasic(BaseModel):  
    customer_id: int  
    first_name: str  
    last_name: str  
    email: str  
    loyalty_level: str  
  
class SubscriptionSummary(BaseModel):  
    subscription_id: int  
    product_id: int  
    status: str  
  
class CustomerDetail(CustomerBasic):  
    subscriptions: List[SubscriptionSummary]  
  
class Invoice(BaseModel):  
    invoice_id: int  
    amount: float  
    status: str  
  
class ServiceIncident(BaseModel):  
    incident_id: int  
    description: str  
  
class SubscriptionDetail(BaseModel):  
    subscription_id: int  
    product_name: str  
    product_description: str  
    invoices: List[Invoice]  
    service_incidents: List[ServiceIncident]  
  
class Promotion(BaseModel):  
    promotion_id: int  
    name: str  
    details: str  
  
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
    quantity: int  
    total_price: float  
  
class SubscriptionUpdateRequest(BaseModel):  
    roaming_enabled: Optional[int] = None  
    status: Optional[str] = None  
    service_status: Optional[str] = None  
    product_id: Optional[int] = None  
  
  
# ====== UTILITY FUNCTIONS =======  
def get_db():  
    """Obtain a SQLite3 database connection."""  
    db = sqlite3.connect(DATABASE)  
    db.row_factory = sqlite3.Row  
    return db  
  
def get_embedding(text, model=emb_engine):  
    """Get OpenAI embedding vector from Azure OpenAI deployment."""  
    text = text.replace("\n", " ")  
    return client.embeddings.create(input=[text], model=model).data[0].embedding  
  
def cosine_similarity(vec1, vec2):  
    """Compute cosine similarity between two vectors."""  
    dot = sum(a * b for a, b in zip(vec1, vec2))  
    norm1 = math.sqrt(sum(a * a for a in vec1))  
    norm2 = math.sqrt(sum(b * b for b in vec2))  
    return dot / (norm1 * norm2) if norm1 and norm2 else 0  
  
# ====== MCP RESOURCE & TOOL DEFINITIONS =======  
  
# --- CUSTOMERS ---  
  
@mcp.resource("customer://list", description="Retrieve all customers with basic info")  
def get_all_customers() -> List[CustomerBasic]:  
    db = get_db()  
    cur = db.execute("SELECT customer_id, first_name, last_name, email, loyalty_level FROM Customers")  
    rows = cur.fetchall()  
    db.close()  
    return [CustomerBasic(**dict(row)) for row in rows]  
  
@mcp.resource("customer://{customer_id}/profile", description="Retrieve a specific customer's profile and subscriptions")  
def get_customer_detail(customer_id: int) -> CustomerDetail:  
    db = get_db()  
    cur = db.execute("SELECT * FROM Customers WHERE customer_id = ?", (customer_id,))  
    customer = cur.fetchone()  
    if not customer:  
        db.close()  
        raise ValueError(f"Customer ID {customer_id} not found")  
    customer_dict = dict(customer)  
    cur2 = db.execute("SELECT subscription_id, product_id, status FROM Subscriptions WHERE customer_id = ?", (customer_id,))  
    subscriptions = [SubscriptionSummary(**dict(row)) for row in cur2.fetchall()]  
    db.close()  
    return CustomerDetail(**customer_dict, subscriptions=subscriptions)  
  
# --- SUBSCRIPTIONS ---  
  
@mcp.resource("subscription://{subscription_id}/detail", description="Retrieve details for a subscription, including invoices and service incidents")  
def get_subscription_detail(subscription_id: int) -> SubscriptionDetail:  
    db = get_db()  
    cur = db.execute(  
        """SELECT s.subscription_id, p.name as product_name, p.description as product_description  
           FROM Subscriptions s  
           JOIN Products p ON s.product_id = p.product_id  
           WHERE s.subscription_id = ?""",  
        (subscription_id,),  
    )  
    sub = cur.fetchone()  
    if not sub:  
        db.close()  
        raise ValueError(f"Subscription ID {subscription_id} not found")  
    sub_dict = dict(sub)  
    cur2 = db.execute("SELECT invoice_id, amount, status FROM Invoices WHERE subscription_id = ?", (subscription_id,))  
    invoices = [Invoice(**dict(row)) for row in cur2.fetchall()]  
    cur3 = db.execute("SELECT incident_id, description FROM ServiceIncidents WHERE subscription_id = ?", (subscription_id,))  
    service_incidents = [ServiceIncident(**dict(row)) for row in cur3.fetchall()]  
    db.close()  
    return SubscriptionDetail(**sub_dict, invoices=invoices, service_incidents=service_incidents)  
  
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
  
# --- PROMOTIONS ---  
  
@mcp.resource("promotion://list", description="Retrieve all active promotions")  
def get_promotions() -> List[Promotion]:  
    db = get_db()  
    cur = db.execute("SELECT promotion_id, name, details FROM Promotions")  
    promos = [Promotion(**dict(row)) for row in cur.fetchall()]  
    db.close()  
    return promos  
  
# --- KNOWLEDGE BASE SEMANTIC SEARCH ---  
  
@mcp.tool(description="Perform a semantic search in the knowledge base for relevant documents")  
def search_knowledge_base(query: str, topk: int = 3) -> List[KBDoc]:  
    db = get_db()  
    query_embedding = get_embedding(query)  
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
    top_results = sorted(results, key=lambda x: x["similarity"], reverse=True)[:topk]  
    return [  
        KBDoc(title=r["title"], doc_type=r["doc_type"], content=r["content"])  
        for r in top_results  
    ]  
  
# --- SECURITY LOGS ---  
  
@mcp.resource("customer://{customer_id}/security_logs", description="Get security logs/events for a customer")  
def get_security_logs(customer_id: int) -> List[SecurityLog]:  
    db = get_db()  
    cur = db.execute(  
        """SELECT log_id, event_type, event_timestamp, description  
           FROM SecurityLogs WHERE customer_id = ?  
           ORDER BY event_timestamp DESC""",  
        (customer_id,),  
    )  
    logs = [SecurityLog(**dict(row)) for row in cur.fetchall()]  
    db.close()  
    return logs  
  
@mcp.tool(description="Unlock a customer's account if it is currently locked")  
def unlock_account(customer_id: int) -> dict:  
    db = get_db()  
    cur = db.execute(  
        """SELECT * FROM SecurityLogs WHERE customer_id = ? AND event_type = 'account_locked'  
           ORDER BY event_timestamp DESC LIMIT 1""",  
        (customer_id,),  
    )  
    row = cur.fetchone()  
    if not row:  
        db.close()  
        raise ValueError("No lock event found or account already unlocked")  
    unlock_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  
    db.execute(  
        """INSERT INTO SecurityLogs (customer_id, event_type, event_timestamp, description)  
           VALUES (?, 'account_unlocked', ?, 'Account unlocked via request')""",  
        (customer_id, unlock_time),  
    )  
    db.commit()  
    db.close()  
    return {"message": "Account unlocked successfully"}  
  
# --- CUSTOMER ORDERS ---  
  
@mcp.resource("customer://{customer_id}/orders", description="Get list of recent orders for a customer")  
def get_customer_orders(customer_id: int) -> List[Order]:  
    db = get_db()  
    cur = db.execute(  
        """SELECT o.order_id, o.order_date, p.name as product_name, o.quantity, o.total_price  
           FROM Orders o  
           JOIN Products p ON o.product_id = p.product_id  
           WHERE o.customer_id = ?  
           ORDER BY o.order_date DESC""",  
        (customer_id,),  
    )  
    orders = [Order(**dict(row)) for row in cur.fetchall()]  
    db.close()  
    return orders  
  
# ====== SERVER RUN COMMAND ===========  
if __name__ == "__main__":  
    # mcp.run()  
    # To run with SSE (as persistent web server):  
    mcp.run(transport="sse")  