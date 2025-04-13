#!/usr/bin/env python3  
  
import sqlite3  
import json  
import math  
import os  
from flask import Flask, jsonify, g, request  
from flasgger import Swagger  
from dotenv import load_dotenv  
from openai import AzureOpenAI  
from datetime import datetime  
  
app = Flask(__name__)  
swagger = Swagger(app)  
  
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
  
@app.route("/customers", methods=["GET"])  
def customers():  
    """  
    Retrieve all customers  
    ---  
    description: Fetch a list of all customers including their basic details like ID, name, email, and loyalty level.  
    responses:  
      200:  
        description: A list of all customers  
        schema:  
          type: array  
          items:  
            type: object  
            properties:  
              customer_id:  
                type: integer  
                description: The unique identifier of the customer  
              first_name:  
                type: string  
                description: The first name of the customer  
              last_name:  
                type: string  
                description: The last name of the customer  
              email:  
                type: string  
                description: The email address of the customer  
              loyalty_level:  
                type: string  
                description: The loyalty level of the customer  
    """  
    cur = get_db().execute(  
        "SELECT customer_id, first_name, last_name, email, loyalty_level FROM Customers"  
    )  
    rows = cur.fetchall()  
    cur.close()  
    results = [dict(row) for row in rows]  
    return jsonify(results)  
  
@app.route("/customer/<int:customer_id>", methods=["GET"])  
def get_customer(customer_id):  
    """  
    Retrieve a specific customer by ID  
    ---  
    description: Get detailed information about a specific customer including their profile and subscriptions.  
    parameters:  
      - name: customer_id  
        in: path  
        type: integer  
        required: true  
        description: The ID of the customer to retrieve  
    responses:  
      200:  
        description: A detailed customer object  
        schema:  
          type: object  
          properties:  
            customer_id:  
              type: integer  
              description: The unique identifier of the customer  
            first_name:  
              type: string  
              description: The first name of the customer  
            last_name:  
              type: string  
              description: The last name of the customer  
            email:  
              type: string  
              description: The email address of the customer  
            loyalty_level:  
              type: string  
              description: The loyalty level of the customer  
            subscriptions:  
              type: array  
              items:  
                type: object  
                properties:  
                  subscription_id:  
                    type: integer  
                    description: The subscription ID  
                  product_id:  
                    type: integer  
                    description: The product ID associated with the subscription  
                  status:  
                    type: string  
                    description: The status of the subscription  
      404:  
        description: Customer not found  
    """  
    db = get_db()  
    cur = db.execute(  
        "SELECT * FROM Customers WHERE customer_id = ?",  
        (customer_id,)  
    )  
    customer = cur.fetchone()  
    cur.close()  
  
    if customer is None:  
        return jsonify({"error": "Customer not found"}), 404  
  
    customer_dict = dict(customer)  
  
    # Get subscriptions for this customer  
    cur = db.execute(  
        "SELECT * FROM Subscriptions WHERE customer_id = ?",  
        (customer_id,)  
    )  
    subscriptions = [dict(row) for row in cur.fetchall()]  
    cur.close()  
  
    customer_dict["subscriptions"] = subscriptions  
    return jsonify(customer_dict)  
  
@app.route("/subscription/<int:subscription_id>", methods=["GET"])  
def get_subscription(subscription_id):  
    """  
    Retrieve subscription details by ID  
    ---  
    description: Get detailed information about a specific subscription including the product details and related invoices and service incidents.  
    parameters:  
      - name: subscription_id  
        in: path  
        type: integer  
        required: true  
        description: The ID of the subscription to retrieve  
    responses:  
      200:  
        description: A detailed subscription object  
        schema:  
          type: object  
          properties:  
            subscription_id:  
              type: integer  
              description: The unique identifier of the subscription  
            product_name:  
              type: string  
              description: The name of the product associated with this subscription  
            product_description:  
              type: string  
              description: The description of the product  
            invoices:  
              type: array  
              items:  
                type: object  
                properties:  
                  invoice_id:  
                    type: integer  
                    description: The invoice ID  
                  amount:  
                    type: number  
                    description: The invoice amount  
                  status:  
                    type: string  
                    description: The invoice status  
            service_incidents:  
              type: array  
              items:  
                type: object  
                properties:  
                  incident_id:  
                    type: integer  
                    description: The service incident ID  
                  description:  
                    type: string  
                    description: The incident description  
      404:  
        description: Subscription not found  
    """  
    db = get_db()  
    cur = db.execute(  
        """SELECT s.*, p.name as product_name, p.description as product_description  
           FROM Subscriptions s  
           JOIN Products p ON s.product_id = p.product_id  
           WHERE s.subscription_id = ?""",  
        (subscription_id,)  
    )  
    subscription = cur.fetchone()  
    cur.close()  
  
    if subscription is None:  
        return jsonify({"error": "Subscription not found"}), 404  
  
    sub_dict = dict(subscription)  
  
    # Retrieve invoices for this subscription  
    cur = db.execute(  
        "SELECT * FROM Invoices WHERE subscription_id = ?",  
        (subscription_id,)  
    )  
    sub_dict["invoices"] = [dict(row) for row in cur.fetchall()]  
    cur.close()  
  
    # Retrieve service incidents for this subscription  
    cur = db.execute(  
        "SELECT * FROM ServiceIncidents WHERE subscription_id = ?",  
        (subscription_id,)  
    )  
    sub_dict["service_incidents"] = [dict(row) for row in cur.fetchall()]  
    cur.close()  
  
    return jsonify(sub_dict)  
  
@app.route("/subscription/<int:subscription_id>", methods=["PUT"])  
def update_subscription(subscription_id):  
    """  
    Update subscription details  
    ---  
    description: Update fields in an existing subscription such as roaming, status, service status, or product ID.  
    parameters:  
      - name: subscription_id  
        in: path  
        type: integer  
        required: true  
        description: The ID of the subscription to update  
      - name: body  
        in: body  
        required: true  
        schema:  
          type: object  
          properties:  
            roaming_enabled:  
              type: integer  
              description: Enable (1) or disable (0) roaming  
            status:  
              type: string  
              description: The status of the subscription (e.g., active, inactive)  
            service_status:  
              type: string  
              description: The service status (e.g., normal, slow, offline)  
            product_id:  
              type: integer  
              description: The ID of the product  
    responses:  
      200:  
        description: Subscription updated successfully  
      400:  
        description: No valid fields to update  
      404:  
        description: Subscription not found  
    """  
    db = get_db()  
    data = request.get_json() or {}  
  
    fields_to_update = []  
    params = []  
  
    if "roaming_enabled" in data:  
        fields_to_update.append("roaming_enabled = ?")  
        params.append(data["roaming_enabled"])  
    if "status" in data:  
        fields_to_update.append("status = ?")  
        params.append(data["status"])  
    if "service_status" in data:  
        fields_to_update.append("service_status = ?")  
        params.append(data["service_status"])  
    if "product_id" in data:  
        fields_to_update.append("product_id = ?")  
        params.append(data["product_id"])  
  
    if not fields_to_update:  
        return jsonify({"error": "No valid fields to update"}), 400  
  
    params.append(subscription_id)  
    query = f"UPDATE Subscriptions SET {', '.join(fields_to_update)} WHERE subscription_id = ?"  
    cur = db.execute(query, tuple(params))  
    db.commit()  
  
    if cur.rowcount == 0:  
        return jsonify({"error": "Subscription not found"}), 404  
  
    return jsonify({"message": "Subscription updated successfully"}), 200  
  
@app.route("/promotions", methods=["GET"])  
def promotions():  
    """  
    Retrieve all promotions  
    ---  
    description: Fetch a list of all current promotions available for customers.  
    responses:  
      200:  
        description: A list of promotions  
        schema:  
          type: array  
          items:  
            type: object  
            properties:  
              promotion_id:  
                type: integer  
                description: The unique identifier of the promotion  
              name:  
                type: string  
                description: The name of the promotion  
              details:  
                type: string  
                description: Detailed description of the promotion  
    """  
    cur = get_db().execute("SELECT * FROM Promotions")  
    promos = [dict(row) for row in cur.fetchall()]  
    cur.close()  
    return jsonify(promos)  
  
@app.route("/kb/search", methods=["GET"])  
def search_kb():  
    """  
    Search the Knowledge Base  
    ---  
    description: Perform a semantic search in the knowledge base using a query.  
    parameters:  
      - name: query  
        in: query  
        type: string  
        required: true  
        description: The search query  
      - name: topk  
        in: query  
        type: integer  
        default: 3  
        description: The number of top results to return  
    responses:  
      200:  
        description: Search results from the knowledge base  
        schema:  
          type: array  
          items:  
            type: object  
            properties:  
              title:  
                type: string  
                description: The title of the document  
              doc_type:  
                type: string  
                description: The type of the document  
              content:  
                type: string  
                description: The content of the document  
    """  
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
    trimmed_results = [{  
        "title": res["title"],  
        "doc_type": res["doc_type"],  
        "content": res["content"]  
    } for res in results[:topk]]  
  
    return jsonify(trimmed_results)  
  
@app.route("/customer/<int:customer_id>/security_logs", methods=["GET"])  
def get_security_logs_for_customer(customer_id):  
    """  
    Retrieve security logs for a customer  
    ---  
    description: Get a list of security events related to a specific customer, ordered by the event timestamp.  
    parameters:  
      - name: customer_id  
        in: path  
        type: integer  
        required: true  
        description: The ID of the customer whose security logs are to be retrieved  
    responses:  
      200:  
        description: A list of security logs  
        schema:  
          type: array  
          items:  
            type: object  
            properties:  
              log_id:  
                type: integer  
                description: The unique identifier of the security log  
              event_type:  
                type: string  
                description: The type of security event  
              event_timestamp:  
                type: string  
                description: The timestamp of the event  
              description:  
                type: string  
                description: Detailed description of the security event  
    """  
    db = get_db()  
    cur = db.execute(  
        """SELECT * FROM SecurityLogs  
           WHERE customer_id = ?  
           ORDER BY event_timestamp DESC""",  
        (customer_id,)  
    )  
    logs = [dict(row) for row in cur.fetchall()]  
    cur.close()  
    return jsonify(logs)  
  
@app.route("/customer/<int:customer_id>/unlock_account", methods=["POST"])  
def unlock_account(customer_id):  
    """  
    Unlock a customer's account  
    ---  
    description: Unlock a customer's account if it is currently locked due to security reasons.  
    parameters:  
      - name: customer_id  
        in: path  
        type: integer  
        required: true  
        description: The ID of the customer whose account is to be unlocked  
    responses:  
      200:  
        description: Account unlocked successfully  
      400:  
        description: No lock event found or account already unlocked  
    """  
    db = get_db()  
  
    # Check if there's a recent 'account_locked' event in SecurityLogs  
    cur = db.execute(  
        """SELECT * FROM SecurityLogs WHERE customer_id = ? AND event_type = 'account_locked'  
           ORDER BY event_timestamp DESC LIMIT 1""",  
        (customer_id,)  
    )  
    row = cur.fetchone()  
  
    if not row:  
        return jsonify({"error": "No lock event found or account already unlocked"}), 400  
  
    # Insert a new log marking the account unlocked  
    unlock_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  
    db.execute(  
        """INSERT INTO SecurityLogs (customer_id, event_type, event_timestamp, description)  
           VALUES (?, 'account_unlocked', ?, 'Account unlocked via request')""",  
        (customer_id, unlock_time)  
    )  
    db.commit()  
  
    return jsonify({"message": "Account unlocked successfully"}), 200  
  
@app.route("/customer/<int:customer_id>/orders", methods=["GET"])  
def get_orders_for_customer(customer_id):  
    """  
    Retrieve orders for a customer  
    ---  
    description: Get a list of recent orders placed by a specific customer, including product details.  
    parameters:  
      - name: customer_id  
        in: path  
        type: integer  
        required: true  
        description: The ID of the customer whose orders are to be retrieved  
    responses:  
      200:  
        description: A list of orders  
        schema:  
          type: array  
          items:  
            type: object  
            properties:  
              order_id:  
                type: integer  
                description: The unique identifier of the order  
              order_date:  
                type: string  
                description: The date when the order was placed  
              product_name:  
                type: string  
                description: The name of the product ordered  
              quantity:  
                type: integer  
                description: The quantity of the product ordered  
              total_price:  
                type: number  
                description: The total price of the order  
    """  
    db = get_db()  
    cur = db.execute(  
        """SELECT o.*, p.name as product_name  
           FROM Orders o  
           JOIN Products p ON o.product_id = p.product_id  
           WHERE o.customer_id = ?  
           ORDER BY o.order_date DESC""",  
        (customer_id,)  
    )  
    orders = [dict(row) for row in cur.fetchall()]  
    cur.close()  
    return jsonify(orders)    
if __name__ == '__main__':  
    app.run(host="0.0.0.0", port=5000, debug=True)  