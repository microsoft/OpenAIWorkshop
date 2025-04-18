from fastmcp import FastMCP  
from typing import List, Optional, Dict, Any  
from pydantic import BaseModel  
import sqlite3, os, json, math, asyncio, logging  
from datetime import datetime  
from dotenv import load_dotenv  
  
# ────────────────────────── FastMCP INITIALISATION ──────────────────────  
mcp = FastMCP(  
    name="Contoso Customer API as Tools",  
    instructions=(  
        "All customer, billing and knowledge data isaccessible ONLY via the declared "  
        "tools below.  Return values follow the pydanticschemas.  Always call the most "  
        "specific tool that answers the user’s question."  
    ),  
)  
  
# ─────────────────────────────  ENV & EMBEDDINGS  ───────────────────────  
load_dotenv()  
DB_PATH = os.getenv("DB_PATH", "data/contoso.db")  
  
def get_db() -> sqlite3.Connection:  
    db = sqlite3.connect(DB_PATH)  
    db.row_factory = sqlite3.Row  
    return db  
  
# — safe OpenAI import / dummy embedding  
try:  
    from openai import AzureOpenAI  
  
    _client = AzureOpenAI(  
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),  
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),  
    )  
    _emb_model = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")  
  
    def get_embedding(text: str) -> List[float]:  
        text = text.replace("\n", " ")  
        return _client.embeddings.create(input=[text], model=_emb_model).data[0].embedding  
  
except Exception:  # pragma: no cover  
    def get_embedding(text: str) -> List[float]:  
        # 1536‑d zero vector falls back when creds are missing (tests/dev mode)  
        return [0.0] * 1536  
  
  
def cosine_similarity(vec1, vec2):  
    dot = sum(a * b for a, b in zip(vec1, vec2))  
    norm1 = math.sqrt(sum(a * a for a in vec1))  
    norm2 = math.sqrt(sum(b * b for b in vec2))  
    return dot / (norm1 * norm2) if norm1 and norm2 else 0.0  
  
  
##############################################################################  
#                              Pydantic MODELS                               #  
##############################################################################  
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
    subscriptions: List[dict]  
  
  
class Payment(BaseModel):  
    payment_id: int  
    payment_date: Optional[str]  
    amount: float  
    method: str  
    status: str  
  
  
class Invoice(BaseModel):  
    invoice_id: int  
    invoice_date: str  
    amount: float  
    description: str  
    due_date: str  
    payments: List[Payment]  
    outstanding: float  
  
  
class ServiceIncident(BaseModel):  
    incident_id: int  
    incident_date: str  
    description: str  
    resolution_status: str  
  
  
class SubscriptionDetail(BaseModel):  
    subscription_id: int  
    product_id: int  
    start_date: str  
    end_date: str  
    status: str  
    roaming_enabled: int  
    service_status: str  
    speed_tier: Optional[str]  
    data_cap_gb: Optional[int]  
    autopay_enabled: int  
    product_name: str  
    product_description: Optional[str]  
    category: Optional[str]  
    monthly_fee: Optional[float]  
    invoices: List[Invoice]  
    service_incidents: List[ServiceIncident]  
  
  
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
  
  
class DataUsageRecord(BaseModel):  
    usage_date: str  
    data_used_mb: int  
    voice_minutes: int  
    sms_count: int  
  
  
class SupportTicket(BaseModel):  
    ticket_id: int  
    subscription_id: int  
    category: str  
    opened_at: str  
    closed_at: Optional[str]  
    status: str  
    priority: str  
    subject: str  
    description: str  
    cs_agent: str  
  
  
class SubscriptionUpdateRequest(BaseModel):  
    roaming_enabled: Optional[int] = None  
    status: Optional[str] = None  
    service_status: Optional[str] = None  
    product_id: Optional[int] = None  
    start_date: Optional[str] = None  
    end_date: Optional[str] = None  
    autopay_enabled: Optional[int] = None  
    speed_tier: Optional[str] = None  
    data_cap_gb: Optional[int] = None  
  
  
# ─── simple arg models ───────────────────────────────────────────────────  
class CustomerIdParam(BaseModel):  
    customer_id: int  
  
  
class SubscriptionIdParam(BaseModel):  
    subscription_id: int  
  
  
class InvoiceIdParam(BaseModel):  
    invoice_id: int  
  
  
##############################################################################  
#                               TOOL ENDPOINTS                               #  
##############################################################################  
@mcp.tool(description="List all customers with basic info")  
def get_all_customers() -> List[CustomerSummary]:  
    db = get_db()  
    rows = db.execute(  
        "SELECT customer_id, first_name, last_name, email, loyalty_level FROM Customers"  
    ).fetchall()  
    db.close()  
    return [CustomerSummary(**dict(r)) for r in rows]  
  
  
@mcp.tool(description="Get a full customer profile including their subscriptions")  
def get_customer_detail(params: CustomerIdParam) -> CustomerDetail:  
    db = get_db()  
    cust = db.execute(  
        "SELECT * FROM Customers WHERE customer_id = ?", (params.customer_id,)  
    ).fetchone()  
    if not cust:  
        db.close()  
        raise ValueError(f"Customer {params.customer_id} not found")  
    subs = db.execute(  
        "SELECT * FROM Subscriptions WHERE customer_id = ?", (params.customer_id,)  
    ).fetchall()  
    db.close()  
    return CustomerDetail(**dict(cust), subscriptions=[dict(s) for s in subs])  
  
  
@mcp.tool(  
    description=(  
        "Detailed subscription view → invoices (with payments) + service incidents."  
    )  
)  
def get_subscription_detail(params: SubscriptionIdParam) -> SubscriptionDetail:  
    db = get_db()  
    sub = db.execute(  
        """  
        SELECT s.*, p.name AS product_name, p.description AS product_description,  
               p.category, p.monthly_fee  
        FROM Subscriptions s  
        JOIN Products p ON p.product_id = s.product_id  
        WHERE s.subscription_id = ?  
        """,  
        (params.subscription_id,),  
    ).fetchone()  
    if not sub:  
        db.close()  
        raise ValueError("Subscription not found")  
  
    # invoices + nested payments  
    invoices_rows = db.execute(  
        """  
        SELECT invoice_id, invoice_date, amount, description, due_date  
        FROM Invoices WHERE subscription_id = ?""",  
        (params.subscription_id,),  
    ).fetchall()  
  
    invoices: List[Invoice] = []  
    for inv in invoices_rows:  
        pay_rows = db.execute(  
            "SELECT * FROM Payments WHERE invoice_id = ?", (inv["invoice_id"],)  
        ).fetchall()  
        total_paid = sum(p["amount"] for p in pay_rows if p["status"] == "successful")  
        invoices.append(  
            Invoice(  
                **dict(inv),  
                payments=[Payment(**dict(p)) for p in pay_rows],  
                outstanding=max(inv["amount"] - total_paid, 0.0),  
            )  
        )  
  
    # service incidents  
    inc_rows = db.execute(  
        """  
        SELECT incident_id, incident_date, description, resolution_status  
        FROM ServiceIncidents  
        WHERE subscription_id = ?""",  
        (params.subscription_id,),  
    ).fetchall()  
  
    db.close()  
    return SubscriptionDetail(  
        **dict(sub),  
        invoices=invoices,  
        service_incidents=[ServiceIncident(**dict(r)) for r in inc_rows],  
    )  
  
  
@mcp.tool(description="Return invoice‑level payments list")  
def get_invoice_payments(params: InvoiceIdParam) -> List[Payment]:  
    db = get_db()  
    rows = db.execute("SELECT * FROM Payments WHERE invoice_id = ?", (params.invoice_id,)).fetchall()  
    db.close()  
    return [Payment(**dict(r)) for r in rows]  
  
  
@mcp.tool(description="Record a payment for a given invoice and get new outstanding balance")  
def pay_invoice(invoice_id: int, amount: float, method: str = "credit_card") -> Dict[str, Any]:  
    today = datetime.now().strftime("%Y-%m-%d")  
    db = get_db()  
    # insert payment row  
    db.execute(  
        "INSERT INTO Payments(invoice_id, payment_date, amount, method, status) VALUES (?,?,?,?,?)",  
        (invoice_id, today, amount, method, "successful"),  
    )  
    # compute remaining balance  
    inv = db.execute("SELECT amount FROM Invoices WHERE invoice_id = ?", (invoice_id,)).fetchone()  
    if not inv:  
        db.close()  
        raise ValueError("Invoice not found")  
    paid = db.execute(  
        "SELECT SUM(amount) as paid FROM Payments WHERE invoice_id = ? AND status='successful'",  
        (invoice_id,),  
    ).fetchone()["paid"]  
    db.commit()  
    db.close()  
    outstanding = max(inv["amount"] - (paid or 0), 0.0)  
    return {"invoice_id": invoice_id, "outstanding": outstanding}  
  
  
@mcp.tool(description="Daily data‑usage records for a subscription over a date range")  
def get_data_usage(  
    subscription_id: int,  
    start_date: str,  
    end_date: str,  
    aggregate: bool = False,  
) -> List[DataUsageRecord] | Dict[str, Any]:  
    db = get_db()  
    rows = db.execute(  
        """  
        SELECT usage_date, data_used_mb, voice_minutes, sms_count  
        FROM DataUsage  
        WHERE subscription_id = ?  
          AND usage_date BETWEEN ? AND ?  
        ORDER BY usage_date  
        """,  
        (subscription_id, start_date, end_date),  
    ).fetchall()  
    db.close()  
    if aggregate:  
        total_mb = sum(r["data_used_mb"] for r in rows)  
        total_voice = sum(r["voice_minutes"] for r in rows)  
        total_sms = sum(r["sms_count"] for r in rows)  
        return {  
            "subscription_id": subscription_id,  
            "start_date": start_date,  
            "end_date": end_date,  
            "total_mb": total_mb,  
            "total_voice_minutes": total_voice,  
            "total_sms": total_sms,  
        }  
    return [DataUsageRecord(**dict(r)) for r in rows]  
  
  
@mcp.tool(description="List every active promotion (no filtering)")  
def get_promotions() -> List[Promotion]:  
    db = get_db()  
    rows = db.execute("SELECT * FROM Promotions").fetchall()  
    db.close()  
    return [Promotion(**dict(r)) for r in rows]  
  
  
@mcp.tool(  
    description="Promotions *eligible* for a given customer right now "  
    "(evaluates basic loyalty/date criteria)."  
)  
def get_eligible_promotions(params: CustomerIdParam) -> List[Promotion]:  
    db = get_db()  
    cust = db.execute("SELECT loyalty_level FROM Customers WHERE customer_id = ?", (params.customer_id,)).fetchone()  
    if not cust:  
        db.close()  
        raise ValueError("Customer not found")  
    loyalty = cust["loyalty_level"]  
    today = datetime.now().strftime("%Y-%m-%d")  
    rows = db.execute(  
        """  
        SELECT * FROM Promotions  
        WHERE start_date <= ? AND end_date >= ?  
        """,  
        (today, today),  
    ).fetchall()  
    db.close()  
    eligible = []  
    for r in rows:  
        crit = r["eligibility_criteria"] or ""  
        if f"loyalty_level = '{loyalty}'" in crit or "loyalty_level" not in crit:  
            eligible.append(Promotion(**dict(r)))  
    return eligible  
  
  
# ─── Knowledge Base Search ───────────────────────────────────────────────  
@mcp.tool(description="Semantic search on policy / procedure knowledge documents")  
def search_knowledge_base(params: KBSearchParams) -> List[KBDoc]:  
    query_emb = get_embedding(params.query)  
    db = get_db()  
    rows = db.execute("SELECT title, doc_type, content, topic_embedding FROM KnowledgeDocuments").fetchall()  
    db.close()  
    scored = []  
    for r in rows:  
        try:  
            emb = json.loads(r["topic_embedding"])  
            sim = cosine_similarity(query_emb, emb)  
            scored.append((sim, r))  
        except Exception:  
            continue  
    scored.sort(reverse=True, key=lambda x: x[0])  
    best = scored[: params.topk]  
    return [  
        KBDoc(title=r["title"], doc_type=r["doc_type"], content=r["content"])  
        for sim, r in best  
    ]  
  
  
# ─── Security Logs ───────────────────────────────────────────────────────  
@mcp.tool(description="Security events for a customer (newest first)")  
def get_security_logs(params: CustomerIdParam) -> List[SecurityLog]:  
    db = get_db()  
    rows = db.execute(  
        "SELECT log_id, event_type, event_timestamp, description "  
        "FROM SecurityLogs WHERE customer_id = ? ORDER BY event_timestamp DESC",  
        (params.customer_id,),  
    ).fetchall()  
    db.close()  
    return [SecurityLog(**dict(r)) for r in rows]  
  
  
# ─── Orders ──────────────────────────────────────────────────────────────  
@mcp.tool(description="All orders placed by a customer")  
def get_customer_orders(params: CustomerIdParam) -> List[Order]:  
    db = get_db()  
    rows = db.execute(  
        """  
        SELECT o.order_id, o.order_date, p.name as product_name,  
               o.amount, o.order_status  
        FROM Orders o  
        JOIN Products p ON p.product_id = o.product_id  
        WHERE o.customer_id = ?  
        ORDER BY o.order_date DESC  
        """,  
        (params.customer_id,),  
    ).fetchall()  
    db.close()  
    return [Order(**dict(r)) for r in rows]  
  
  
# ─── Support Tickets ────────────────────────────────────────────────────  
@mcp.tool(description="Retrieve support tickets for a customer (optionally filter by open status)")  
def get_support_tickets(  
    customer_id: int,  
    open_only: bool = False,  
) -> List[SupportTicket]:  
    db = get_db()  
    query = "SELECT * FROM SupportTickets WHERE customer_id = ?"  
    if open_only:  
        query += " AND status != 'closed'"  
    rows = db.execute(query, (customer_id,)).fetchall()  
    db.close()  
    return [SupportTicket(**dict(r)) for r in rows]  
  
  
@mcp.tool(description="Create a new support ticket for a customer")  
def create_support_ticket(  
    customer_id: int,  
    subscription_id: int,  
    category: str,  
    priority: str,  
    subject: str,  
    description: str,  
) -> SupportTicket:  
    opened = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  
    db = get_db()  
    cur = db.execute(  
        """  
        INSERT INTO SupportTickets  
        (customer_id, subscription_id, category, opened_at, closed_at,  
         status, priority, subject, description, cs_agent)  
        VALUES (?,?,?,?,?,?,?,?,?,?)  
        """,  
        (  
            customer_id,  
            subscription_id,  
            category,  
            opened,  
            None,  
            "open",  
            priority,  
            subject,  
            description,  
            "AI_Bot",  
        ),  
    )  
    ticket_id = cur.lastrowid  
    db.commit()  
    row = db.execute("SELECT * FROM SupportTickets WHERE ticket_id = ?", (ticket_id,)).fetchone()  
    db.close()  
    return SupportTicket(**dict(row))  
  
  
# ─── Products ────────────────────────────────────────────────────────────  
class Product(BaseModel):  
    product_id: int  
    name: str  
    description: str  
    category: str  
    monthly_fee: float  
  
  
@mcp.tool(description="List / search available products (optional category filter)")  
def get_products(category: Optional[str] = None) -> List[Product]:  
    db = get_db()  
    if category:  
        rows = db.execute("SELECT * FROM Products WHERE category = ?", (category,)).fetchall()  
    else:  
        rows = db.execute("SELECT * FROM Products").fetchall()  
    db.close()  
    return [Product(**dict(r)) for r in rows]  
  
  
@mcp.tool(description="Return a single product by ID")  
def get_product_detail(product_id: int) -> Product:  
    db = get_db()  
    r = db.execute("SELECT * FROM Products WHERE product_id = ?", (product_id,)).fetchone()  
    db.close()  
    if not r:  
        raise ValueError("Product not found")  
    return Product(**dict(r))  
  
  
# ─── Update Subscription ────────────────────────────────────────────────  
@mcp.tool(description="Update one or more mutable fields on a subscription.")  
def update_subscription(subscription_id: int, update: SubscriptionUpdateRequest) -> dict:  
    data = update.dict(exclude_unset=True)  
    if not data:  
        raise ValueError("No fields supplied")  
    sets = ", ".join(f"{k} = ?" for k in data)  
    params = list(data.values()) + [subscription_id]  
    db = get_db()  
    cur = db.execute(f"UPDATE Subscriptions SET {sets} WHERE subscription_id = ?", params)  
    db.commit()  
    db.close()  
    if cur.rowcount == 0:  
        raise ValueError("Subscription not found")  
    return {"subscription_id": subscription_id, "updated_fields": list(data.keys())}  
  
  
# ─── Unlock Account ──────────────────────────────────────────────────────  
@mcp.tool(description="Unlock a customer account locked for security reasons")  
def unlock_account(params: CustomerIdParam) -> dict:  
    db = get_db()  
    row = db.execute(  
        "SELECT 1 FROM SecurityLogs WHERE customer_id = ? AND event_type = 'account_locked' "  
        "ORDER BY event_timestamp DESC LIMIT 1",  
        (params.customer_id,),  
    ).fetchone()  
    if not row:  
        db.close()  
        raise ValueError("No recent lock event; nothing to do.")  
    db.execute(  
        "INSERT INTO SecurityLogs (customer_id, event_type, event_timestamp, description) "  
        "VALUES (?, 'account_unlocked', ?, 'Unlocked via API')",  
        (params.customer_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),  
    )  
    db.commit()  
    db.close()  
    return {"message": "Account unlocked"}  
  
  
# ─── Billing summary ─────────────────────────────────────────────────────  
@mcp.tool(description="What does a customer currently owe across all subscriptions?")  
def get_billing_summary(params: CustomerIdParam) -> Dict[str, Any]:  
    db = get_db()  
    inv_rows = db.execute(  
        """  
        SELECT inv.invoice_id, inv.amount,  
               IFNULL(SUM(pay.amount),0) AS paid  
        FROM Invoices inv  
        LEFT JOIN Payments pay ON pay.invoice_id = inv.invoice_id  
                                 AND pay.status='successful'  
        WHERE inv.subscription_id IN  
            (SELECT subscription_id FROM Subscriptions WHERE customer_id = ?)  
        GROUP BY inv.invoice_id  
        """,  
        (params.customer_id,),  
    ).fetchall()  
    db.close()  
    outstanding = [  
        {"invoice_id": r["invoice_id"], "outstanding": max(r["amount"] - r["paid"], 0.0)}  
        for r in inv_rows  
    ]  
    total_due = sum(item["outstanding"] for item in outstanding)  
    return {"customer_id": params.customer_id, "total_due": total_due, "invoices": outstanding}  
  
  
##############################################################################  
#                                RUN SERVER                                  #  
##############################################################################  
if __name__ == "__main__":  
    asyncio.run(mcp.run_sse_async(host="0.0.0.0", port=8000))  
