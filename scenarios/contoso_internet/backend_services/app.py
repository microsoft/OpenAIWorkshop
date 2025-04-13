#!/usr/bin/env python3  
  
import sqlite3  
import json  
import math  
import os  
from flask import Flask, jsonify, g, request  
from pathlib import Path  
from dotenv import load_dotenv  
from openai import AzureOpenAI  
from tenacity import retry, wait_random_exponential, stop_after_attempt  
  
app = Flask(__name__)  
DATABASE = "data/contoso.db"  
  
# Load OpenAI credentials  
load_dotenv()  
chat_engine = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  
emb_engine = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")  
client = AzureOpenAI(  
    api_key=os.environ.get("AZURE_OPENAI_API_KEY"),  
    api_version=os.environ.get("AZURE_OPENAI_API_VERSION"),  
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT")  
)  
  
  
def get_embedding(text, model=emb_engine):  
    text = text.replace("\n", " ")  
    return client.embeddings.create(input=[text], model=model).data[0].embedding  
  
  
def cosine_similarity(vec1, vec2):  
    dot = sum(a * b for a, b in zip(vec1, vec2))  
    norm1 = math.sqrt(sum(a * a for a in vec1))  
    norm2 = math.sqrt(sum(b * b for b in vec2))  
    return dot / (norm1 * norm2) if norm1 and norm2 else 0  
  
  
def get_db():  
    db = getattr(g, '_database', None)  
    if db is None:  
        db = g._database = sqlite3.connect(DATABASE)  
        db.row_factory = sqlite3.Row  
    return db  
  
  
@app.teardown_appcontext  
def close_connection(exception):  
    db = getattr(g, '_database', None)  
    if db is not None:  
        db.close()  
  
# -----------------------------------------------------------------  
# Basic CRM / Customer and Subscription endpoints  
# -----------------------------------------------------------------  
  
@app.route("/customers", methods=["GET"])  
def customers():  
    cur = get_db().execute(  
        "SELECT customer_id, first_name, last_name, email, loyalty_level FROM Customers"  
    )  
    rows = cur.fetchall()  
    cur.close()  
    results = [dict(row) for row in rows]  
    return jsonify(results)  
  
  
@app.route("/customer/<int:customer_id>", methods=["GET"])  
def get_customer(customer_id):  
    db = get_db()  
    cur = db.execute(  
        "SELECT * FROM Customers WHERE customer_id = ?", (customer_id,)  
    )  
    customer = cur.fetchone()  
    cur.close()  
  
    if customer is None:  
        return jsonify({"error": "Customer not found"}), 404  
  
    customer_dict = dict(customer)  
  
    # Get subscriptions for this customer  
    cur = db.execute(  
        "SELECT * FROM Subscriptions WHERE customer_id = ?", (customer_id,)  
    )  
    subscriptions = [dict(row) for row in cur.fetchall()]  
    cur.close()  
  
    customer_dict["subscriptions"] = subscriptions  
    return jsonify(customer_dict)  
  
  
@app.route("/subscription/<int:subscription_id>", methods=["GET"])  
def get_subscription(subscription_id):  
    db = get_db()  
    cur = db.execute("""  
        SELECT s.*, p.name as product_name, p.description as product_description  
        FROM Subscriptions s  
        JOIN Products p ON s.product_id = p.product_id  
        WHERE s.subscription_id = ?  
    """, (subscription_id,))  
    subscription = cur.fetchone()  
    cur.close()  
  
    if subscription is None:  
        return jsonify({"error": "Subscription not found"}), 404  
  
    sub_dict = dict(subscription)  
  
    # Retrieve invoices for this subscription  
    cur = db.execute(  
        "SELECT * FROM Invoices WHERE subscription_id = ?", (subscription_id,)  
    )  
    sub_dict["invoices"] = [dict(row) for row in cur.fetchall()]  
    cur.close()  
  
    # Retrieve service incidents for this subscription  
    cur = db.execute(  
        "SELECT * FROM ServiceIncidents WHERE subscription_id = ?", (subscription_id,)  
    )  
    sub_dict["service_incidents"] = [dict(row) for row in cur.fetchall()]  
    cur.close()  
  
    return jsonify(sub_dict)  
  
# -----------------------------------------------------------------  
# Promotions  
# -----------------------------------------------------------------  
  
@app.route("/promotions", methods=["GET"])  
def promotions():  
    cur = get_db().execute("SELECT * FROM Promotions")  
    promos = [dict(row) for row in cur.fetchall()]  
    cur.close()  
    return jsonify(promos)  
  
# -----------------------------------------------------------------  
# Knowledge Base Search  
# -----------------------------------------------------------------  
  
@app.route("/kb/search", methods=["GET"])  
def search_kb():  
    query = request.args.get("query")  
    topk = request.args.get("topk", default=3, type=int)  
  
    if not query:  
        return jsonify({"error": "Query parameter is required"}), 400  
  
    query_embedding = get_embedding(query)  
    db = get_db()  
    cur = db.execute("SELECT title, doc_type, content, topic_embedding FROM KnowledgeDocuments")  
    rows = cur.fetchall()  
    cur.close()  
  
    results = []  
    for row in rows:  
        try:  
            stored_embed = json.loads(row["topic_embedding"])  
        except Exception:  
            continue  
        sim = cosine_similarity(query_embedding, stored_embed)  
        results.append({  
            "title": row["title"],  
            "doc_type": row["doc_type"],  
            "content": row["content"],  
            "similarity": sim  
        })  
  
    results = sorted(results, key=lambda x: x["similarity"], reverse=True)  
      
    # Return only the requested fields (title, doc_type, content) for topk results  
    trimmed_results = [{  
        "title": res["title"],  
        "doc_type": res["doc_type"],  
        "content": res["content"]  
    } for res in results[:topk]]  
  
    return jsonify(trimmed_results)    
# -----------------------------------------------------------------  
# Security Logs endpoint (for account lock/unlock scenarios)  
# -----------------------------------------------------------------  
  
@app.route("/customer/<int:customer_id>/security_logs", methods=["GET"])  
def get_security_logs_for_customer(customer_id):  
    db = get_db()  
    cur = db.execute("""  
        SELECT * FROM SecurityLogs  
        WHERE customer_id = ?  
        ORDER BY event_timestamp DESC  
    """, (customer_id,))  
    logs = [dict(row) for row in cur.fetchall()]  
    cur.close()  
    return jsonify(logs)  
  
# -----------------------------------------------------------------  
# Orders endpoint (for checking recent purchases and returns)  
# -----------------------------------------------------------------  
  
@app.route("/customer/<int:customer_id>/orders", methods=["GET"])  
def get_orders_for_customer(customer_id):  
    db = get_db()  
    cur = db.execute("""  
        SELECT o.*, p.name as product_name  
        FROM Orders o  
        JOIN Products p ON o.product_id = p.product_id  
        WHERE o.customer_id = ?  
        ORDER BY o.order_date DESC  
    """, (customer_id,))  
    orders = [dict(row) for row in cur.fetchall()]  
    cur.close()  
    return jsonify(orders)  
  
  
if __name__ == '__main__':  
    app.run(host="0.0.0.0", port=5000, debug=True)  