#!/usr/bin/env python3  
  
import sqlite3  
import random  
import json  
from datetime import datetime, timedelta  
from faker import Faker  
from pathlib import Path  
from tenacity import retry, wait_random_exponential, stop_after_attempt  
from dotenv import load_dotenv  
from openai import AzureOpenAI  
import os  
import math  
  
# Load environment variables  
load_dotenv()  
  
# Azure OpenAI deployment names  
chat_engine = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")  
emb_engine = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")  
  
# Azure OpenAI client setup  
client = AzureOpenAI(  
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),  
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")  
)  
  
# Function to generate embedding  
def get_embedding(text, model=emb_engine):  
    text = text.replace("\n", " ")  
    return client.embeddings.create(input=[text], model=model).data[0].embedding  
  
fake = Faker()  
DB_NAME = "contoso.db"  
  
def create_tables(conn):  
    c = conn.cursor()  
    tables = ["ServiceIncidents", "Orders", "KnowledgeDocuments", "SecurityLogs",  
              "Promotions", "Invoices", "Subscriptions", "Products", "Customers"]  
      
    for t in tables:  
        c.execute(f"DROP TABLE IF EXISTS {t}")  
  
    c.execute("""  
        CREATE TABLE Customers (  
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,  
            first_name TEXT NOT NULL,  
            last_name TEXT NOT NULL,  
            email TEXT UNIQUE,  
            phone TEXT,  
            address TEXT,  
            loyalty_level TEXT  
        )  
    """)  
  
    c.execute("""  
        CREATE TABLE Products (  
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,  
            name TEXT NOT NULL,  
            description TEXT,  
            category TEXT,  
            monthly_fee REAL  
        )  
    """)  
  
    c.execute("""  
        CREATE TABLE Subscriptions (  
            subscription_id INTEGER PRIMARY KEY AUTOINCREMENT,  
            customer_id INTEGER NOT NULL,  
            product_id INTEGER NOT NULL,  
            start_date TEXT,  
            end_date TEXT,  
            status TEXT,  
            roaming_enabled INTEGER DEFAULT 0,  
            service_status TEXT,  
            FOREIGN KEY (customer_id) REFERENCES Customers(customer_id),  
            FOREIGN KEY (product_id) REFERENCES Products(product_id)  
        )  
    """)  
  
    c.execute("""  
        CREATE TABLE Invoices (  
            invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,  
            subscription_id INTEGER,  
            invoice_date TEXT,  
            amount REAL,  
            description TEXT,  
            FOREIGN KEY (subscription_id) REFERENCES Subscriptions(subscription_id)  
        )  
    """)  
  
    c.execute("""  
        CREATE TABLE Promotions (  
            promotion_id INTEGER PRIMARY KEY AUTOINCREMENT,  
            product_id INTEGER,  
            name TEXT,  
            description TEXT,  
            eligibility_criteria TEXT,  
            start_date TEXT,  
            end_date TEXT,  
            discount_percent INTEGER,  
            FOREIGN KEY (product_id) REFERENCES Products(product_id)  
        )  
    """)  
  
    c.execute("""  
        CREATE TABLE SecurityLogs (  
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,  
            customer_id INTEGER,  
            event_type TEXT,  
            event_timestamp TEXT,  
            description TEXT,  
            FOREIGN KEY (customer_id) REFERENCES Customers(customer_id)  
        )  
    """)  
  
    c.execute("""  
        CREATE TABLE KnowledgeDocuments (  
            document_id INTEGER PRIMARY KEY AUTOINCREMENT,  
            title TEXT,  
            doc_type TEXT,  
            content TEXT,  
            topic_embedding TEXT  
        )  
    """)  
  
    c.execute("""  
        CREATE TABLE Orders (  
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,  
            customer_id INTEGER,  
            product_id INTEGER,  
            order_date TEXT,  
            amount REAL,  
            order_status TEXT,  
            FOREIGN KEY (customer_id) REFERENCES Customers(customer_id),  
            FOREIGN KEY (product_id) REFERENCES Products(product_id)  
        )  
    """)  
  
    c.execute("""  
        CREATE TABLE ServiceIncidents (  
            incident_id INTEGER PRIMARY KEY AUTOINCREMENT,  
            subscription_id INTEGER,  
            incident_date TEXT,  
            description TEXT,  
            resolution_status TEXT,  
            FOREIGN KEY (subscription_id) REFERENCES Subscriptions(subscription_id)  
        )  
    """)  
  
    conn.commit()  
  
def populate_data(conn):  
    c = conn.cursor()  
  
    # Customers  
    loyalty_levels = ['Bronze', 'Silver', 'Gold']  
    customer_ids = []  
    for _ in range(100):  
        first = fake.first_name()  
        last = fake.last_name()  
        email = fake.unique.email()  
        phone = fake.phone_number()  
        address = fake.address().replace("\n", ", ")  
        loyalty = random.choice(loyalty_levels)  
        c.execute(  
            "INSERT INTO Customers (first_name, last_name, email, phone, address, loyalty_level) VALUES (?,?,?,?,?,?)",  
            (first, last, email, phone, address, loyalty)  
        )  
        customer_ids.append(c.lastrowid)  
  
    # Products  
    products = [  
        ("Contoso Mobile Plan", "Standard mobile plan offering unlimited talk and text.", "mobile", 50.00),  
        ("Contoso Internet Plan", "High-speed internet plan with unlimited data.", "internet", 60.00),  
        ("Contoso Bundle Plan", "Combination of mobile and internet services at a bundled rate.", "bundle", 90.00),  
        ("Contoso International Roaming", "Additional international roaming package for travelers.", "addon", 20.00)  
    ]  
    product_ids = {}  
    for prod in products:  
        c.execute("INSERT INTO Products (name, description, category, monthly_fee) VALUES (?,?,?,?)", prod)  
        product_ids[prod[0]] = c.lastrowid  
  
    # Subscriptions  
    subscription_ids = []  
    service_statuses = ['normal', 'slow', 'offline']  
    today = datetime.today()  
    for cid in customer_ids:  
        product_name = random.choice([p[0] for p in products])  
        product_id = product_ids[product_name]  
        start_date = today - timedelta(days=random.randint(30, 365))  
        end_date = start_date + timedelta(days=365)  
        status = random.choices(['active', 'inactive'], weights=[0.85, 0.15])[0]  
        roaming_enabled = random.choice([0, 1])  
        service_status = random.choices(service_statuses, weights=[0.8, 0.15, 0.05])[0]  
        c.execute("""  
            INSERT INTO Subscriptions (customer_id, product_id, start_date, end_date, status, roaming_enabled, service_status)  
            VALUES (?,?,?,?,?,?,?)  
        """, (cid, product_id, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), status, roaming_enabled, service_status))  
        subscription_ids.append(c.lastrowid)  
  
    # Insert Invoices (10-20 per subscription)  
    for sub_id in subscription_ids:  
        num_invoices = random.randint(10, 20)  
        for _ in range(num_invoices):  
            invoice_date = today - timedelta(days=random.randint(0, 30))  
            amount = round(random.uniform(40, 120), 2)  
            c.execute("""  
                INSERT INTO Invoices (subscription_id, invoice_date, amount, description)  
                VALUES (?,?,?,?)  
            """, (sub_id, invoice_date.strftime("%Y-%m-%d"), amount, fake.sentence(nb_words=6)))  

    # Insert Promotions (two sample promotions)  
    promotion_data = [  
        (  
            product_ids["Contoso Mobile Plan"],  
            "Mobile Loyalty Discount",  
            "10% discount for Gold members on the mobile plan.",  
            "loyalty_level = 'Gold'",  
            "2023-01-01",  
            "2023-12-31",  
            10  
        ),  
        (  
            product_ids["Contoso Internet Plan"],  
            "New Internet Sign-up Bonus",  
            "15% off for new internet subscribers.",  
            "subscription_start within last 90 days",  
            "2023-06-01",  
            "2023-09-30",  
            15  
        )  
    ]  
    for promo in promotion_data:  
        c.execute("""  
            INSERT INTO Promotions (product_id, name, description, eligibility_criteria, start_date, end_date, discount_percent)  
            VALUES (?,?,?,?,?,?,?)  
        """, promo)  

    # Insert SecurityLogs (simulate events for a few customers)  
    event_types = ['login_attempt', 'account_locked']  
    for _ in range(20):  
        cust_id = random.choice(customer_ids)  
        event_type = random.choice(event_types)  
        event_time = datetime.now() - timedelta(minutes=random.randint(1, 1000))  
        c.execute("""  
            INSERT INTO SecurityLogs (customer_id, event_type, event_timestamp, description)  
            VALUES (?,?,?,?)  
        """, (cust_id, event_type, event_time.strftime("%Y-%m-%d %H:%M:%S"), fake.sentence(nb_words=8)))  

    # Insert Orders (simulate ~50 orders, including a small chance for 'returned')  
    order_statuses = ['delivered', 'completed', 'pending', 'returned']  
    for _ in range(50):  
        cust_id = random.choice(customer_ids)  
        product_id = random.choice(list(product_ids.values()))  
        order_date = today - timedelta(days=random.randint(1, 60))  
        amount = round(random.uniform(10, 100), 2)  
        status = random.choice(order_statuses)  
        c.execute("""  
            INSERT INTO Orders (customer_id, product_id, order_date, amount, order_status)  
            VALUES (?,?,?,?,?)  
        """, (cust_id, product_id, order_date.strftime("%Y-%m-%d"), amount, status))  

    # Insert ServiceIncidents (simulate ~20 incidents)  
    resolution_statuses = ['investigating', 'resolved']  
    for _ in range(20):  
        sub_id = random.choice(subscription_ids)  
        incident_date = today - timedelta(days=random.randint(0, 30))  
        desc = fake.sentence(nb_words=10)  
        resolution = random.choice(resolution_statuses)  
        c.execute("""  
            INSERT INTO ServiceIncidents (subscription_id, incident_date, description, resolution_status)  
            VALUES (?,?,?,?)  
        """, (sub_id, incident_date.strftime("%Y-%m-%d"), desc, resolution))  
    # -----------------------------------------------------------------  
    # Insert Knowledge Documents from kb.json (instead of LLM generation)  
    # -----------------------------------------------------------------  

    with open("kb.json", "r", encoding="utf-8") as f:  
        kb_data = json.load(f)  
  
    for doc in kb_data:  
        document_title = doc["document_title"]  
        doc_type = doc["doc_type"]  
        content = doc["document_content"]  
        topic_embed = get_embedding(document_title)  
        c.execute("""  
            INSERT INTO KnowledgeDocuments (title, doc_type, content, topic_embedding)  
            VALUES (?,?,?,?)  
        """, (document_title, doc_type, content, json.dumps(topic_embed)))  
  
    conn.commit()  
  
def main():  
    conn = sqlite3.connect(DB_NAME)  
    create_tables(conn)  
    populate_data(conn)  
    conn.close()  
    print("Database populated with sample data including knowledge base from kb.json.")  
  
if __name__ == "__main__":  
    main()  