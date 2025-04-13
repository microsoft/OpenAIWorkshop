#!/usr/bin/env python3  
  
import sqlite3  
import random  
import json  
from datetime import datetime, timedelta  
from faker import Faker  
from pathlib import Path  
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
  
###############################################################################  
# Helper functions  
###############################################################################  
  
def get_embedding(text, model=emb_engine):  
    text = text.replace("\n", " ")  
    return client.embeddings.create(input=[text], model=model).data[0].embedding  
  
fake = Faker()  
DB_NAME = "contoso.db"  
  
# Define a fixed base date to ensure consistency across runs  
BASE_DATE = datetime.now()  
  
def create_tables(conn):  
    c = conn.cursor()  
    tables = [  
        "ServiceIncidents",  
        "Orders",  
        "KnowledgeDocuments",  
        "SecurityLogs",  
        "Promotions",  
        "Invoices",  
        "Subscriptions",  
        "Products",  
        "Customers"  
    ]  
      
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
  
def populate_data(conn, markdown_file="customer_scenarios.md"):  
    c = conn.cursor()  
  
    # Create random customers  
    loyalty_levels = ['Bronze', 'Silver', 'Gold']  
    all_customer_ids = []  
      
    for _ in range(100):  
        first = fake.first_name()  
        last = fake.last_name()  
        email = fake.unique.email()  
        phone = fake.phone_number()  
        address = fake.address().replace("\n", ", ")  
        loyalty = random.choice(loyalty_levels)  
          
        c.execute("""  
            INSERT INTO Customers (first_name, last_name, email, phone, address, loyalty_level)  
            VALUES (?, ?, ?, ?, ?, ?)  
        """, (first, last, email, phone, address, loyalty))  
          
        all_customer_ids.append(c.lastrowid)  
  
    # Create products  
    products = [  
        ("Contoso Mobile Plan", "Standard mobile plan offering unlimited talk and text.", "mobile", 50.00),  
        ("Contoso Internet Plan", "High-speed internet plan with unlimited data.", "internet", 60.00),  
        ("Contoso Bundle Plan", "Combination of mobile and internet services at a bundled rate.", "bundle", 90.00),  
        ("Contoso International Roaming", "Additional international roaming package for travelers.", "addon", 20.00)  
    ]  
      
    product_ids = {}  
      
    for prod in products:  
        c.execute("""  
            INSERT INTO Products (name, description, category, monthly_fee)  
            VALUES (?, ?, ?, ?)  
        """, prod)  
        product_ids[prod[0]] = c.lastrowid  
  
    # Generate random subscriptions (for random customers)  
    subscription_ids = []  
    service_statuses = ['normal', 'slow', 'offline']  
      
    for cid in all_customer_ids:  
        product_name = random.choice([p[0] for p in products])  
        product_id = product_ids[product_name]  
          
        # Pick a random start date up to 365 days prior to BASE_DATE  
        start_offset = random.randint(30, 365)  
        start_date = BASE_DATE - timedelta(days=start_offset)  
        end_date = start_date + timedelta(days=365)  
        status = random.choices(['active', 'inactive'], weights=[0.85, 0.15])[0]  
        roaming_enabled = random.choice([0, 1])  
        service_status = random.choices(service_statuses, weights=[0.8, 0.15, 0.05])[0]  
          
        c.execute("""  
            INSERT INTO Subscriptions (customer_id, product_id, start_date, end_date, status, roaming_enabled, service_status)  
            VALUES (?, ?, ?, ?, ?, ?, ?)  
        """, (  
            cid,  
            product_id,  
            start_date.strftime("%Y-%m-%d"),  
            end_date.strftime("%Y-%m-%d"),  
            status,  
            roaming_enabled,  
            service_status  
        ))  
          
        subscription_ids.append(c.lastrowid)  
  
    # Generate random invoices (10-20 per subscription)  
    for sub_id in subscription_ids:  
        num_invoices = random.randint(10, 20)  
          
        for _ in range(num_invoices):  
            # Pick a random day in the last 60 days relative to BASE_DATE  
            invoice_offset = random.randint(1, 60)  
            invoice_date = BASE_DATE - timedelta(days=invoice_offset)  
            amount = round(random.uniform(40, 120), 2)  
              
            c.execute("""  
                INSERT INTO Invoices (subscription_id, invoice_date, amount, description)  
                VALUES (?, ?, ?, ?)  
            """, (  
                sub_id,  
                invoice_date.strftime("%Y-%m-%d"),  
                amount,  
                fake.sentence(nb_words=6)  
            ))  
  
    # Insert some sample promotions with static start/end dates  
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
            VALUES (?, ?, ?, ?, ?, ?, ?)  
        """, promo)  
  
    # Generate random security logs  
    event_types = ['login_attempt', 'account_locked']  
      
    for _ in range(20):  
        cust_id = random.choice(all_customer_ids)  
        event_type = random.choice(event_types)  
          
        # Random time in the last 2000 minutes prior to BASE_DATE  
        event_minutes = random.randint(1, 2000)  
        event_time = BASE_DATE - timedelta(minutes=event_minutes)  
          
        c.execute("""  
            INSERT INTO SecurityLogs (customer_id, event_type, event_timestamp, description)  
            VALUES (?, ?, ?, ?)  
        """, (  
            cust_id,  
            event_type,  
            event_time.strftime("%Y-%m-%d %H:%M:%S"),  
            fake.sentence(nb_words=8)  
        ))  
  
    # Generate random orders  
    order_statuses = ['delivered', 'completed', 'pending', 'returned']  
      
    for _ in range(50):  
        cust_id = random.choice(all_customer_ids)  
        product_id = random.choice(list(product_ids.values()))  
          
        # Random day in last 90 days  
        order_offset = random.randint(1, 90)  
        order_date = BASE_DATE - timedelta(days=order_offset)  
        amount = round(random.uniform(10, 100), 2)  
        status = random.choice(order_statuses)  
          
        c.execute("""  
            INSERT INTO Orders (customer_id, product_id, order_date, amount, order_status)  
            VALUES (?, ?, ?, ?, ?)  
        """, (  
            cust_id,  
            product_id,  
            order_date.strftime("%Y-%m-%d"),  
            amount,  
            status  
        ))  
  
    # Generate random service incidents  
    resolution_statuses = ['investigating', 'resolved']  
      
    for _ in range(20):  
        sub_id = random.choice(subscription_ids)  
        incident_offset = random.randint(1, 60)  
        incident_date = BASE_DATE - timedelta(days=incident_offset)  
        desc = fake.sentence(nb_words=10)  
        resolution = random.choice(resolution_statuses)  
          
        c.execute("""  
            INSERT INTO ServiceIncidents (subscription_id, incident_date, description, resolution_status)  
            VALUES (?, ?, ?, ?)  
        """, (  
            sub_id,  
            incident_date.strftime("%Y-%m-%d"),  
            desc,  
            resolution  
        ))  
  
    # ─────────────────────────────────────────────────────────────────────────────  
    # SCENARIO-SPECIFIC DATA: six customers (ONE FOR EACH EXAMPLE)  
    # ─────────────────────────────────────────────────────────────────────────────  
  
    # Open markdown file for writing  
    with open(markdown_file, 'w') as f:  
        f.write("# Customer Scenarios\n\n")  
  
        # Scenario 1: Invoice higher than usual  
        c.execute("""  
            INSERT INTO Customers (first_name, last_name, email, phone, address, loyalty_level)  
            VALUES (?, ?, ?, ?, ?, ?)  
        """, ("John", "Doe", "scenario1@example.com", "555-0001", "123 Main St, City", "Silver"))  
        scenario1_cust = c.lastrowid  
  
        start_s1 = BASE_DATE - timedelta(days=60)  
        end_s1 = start_s1 + timedelta(days=365)  
  
        c.execute("""  
            INSERT INTO Subscriptions  
            (customer_id, product_id, start_date, end_date, status, roaming_enabled, service_status)  
            VALUES (?, ?, ?, ?, ?, ?, ?)  
        """, (scenario1_cust, product_ids["Contoso Internet Plan"], start_s1.strftime("%Y-%m-%d"), end_s1.strftime("%Y-%m-%d"), "active", 0, "normal"))  
        s1_sub_id = c.lastrowid  
  
        c.execute("""  
            INSERT INTO Invoices (subscription_id, invoice_date, amount, description)  
            VALUES (?, ?, ?, ?)  
        """, (s1_sub_id, (BASE_DATE - timedelta(days=30)).strftime("%Y-%m-%d"), 60.00, "Standard monthly charge"))  
        c.execute("""  
            INSERT INTO Invoices (subscription_id, invoice_date, amount, description)  
            VALUES (?, ?, ?, ?)  
        """, (s1_sub_id, (BASE_DATE - timedelta(days=1)).strftime("%Y-%m-%d"), 150.00, "Unexpected overage charges"))  
  
        # Write scenario 1 to markdown  
        f.write(f"## Scenario 1: Invoice Higher Than Usual\n")  
        f.write(f"- **Customer ID**: {scenario1_cust}\n")  
        f.write(f"- **Name**: John Doe\n")  
        f.write(f"- **Email**: scenario1@example.com\n")  
        f.write(f"- **Phone**: 555-0001\n")  
        f.write(f"- **Address**: 123 Main St, City\n")  
        f.write(f"- **Loyalty Level**: Silver\n")  
        f.write(f"- **Scenario Description**: I noticed my last invoice was higher than usual—can you help me understand why and what can be done about it?.\n")  
        f.write("\n---\n\n")  
  
        # Scenario 2: Internet is slower than before  
        c.execute("""  
            INSERT INTO Customers (first_name, last_name, email, phone, address, loyalty_level)  
            VALUES (?, ?, ?, ?, ?, ?)  
        """, ("Jane", "Doe", "scenario2@example.com", "555-0002", "234 Elm St, Town", "Gold"))  
        scenario2_cust = c.lastrowid  
  
        start_s2 = BASE_DATE - timedelta(days=45)  
        end_s2 = start_s2 + timedelta(days=365)  
  
        c.execute("""  
            INSERT INTO Subscriptions  
            (customer_id, product_id, start_date, end_date, status, roaming_enabled, service_status)  
            VALUES (?, ?, ?, ?, ?, ?, ?)  
        """, (scenario2_cust, product_ids["Contoso Internet Plan"], start_s2.strftime("%Y-%m-%d"), end_s2.strftime("%Y-%m-%d"), "active", 0, "slow"))  
        s2_sub_id = c.lastrowid  
  
        c.execute("""  
            INSERT INTO ServiceIncidents (subscription_id, incident_date, description, resolution_status)  
            VALUES (?, ?, ?, ?)  
        """, (s2_sub_id, (BASE_DATE - timedelta(days=2)).strftime("%Y-%m-%d"), "Customer reports slow speeds for 3 days.", "investigating"))  
  
        # Write scenario 2 to markdown  
        f.write(f"## Scenario 2: Internet Slower Than Before\n")  
        f.write(f"- **Customer ID**: {scenario2_cust}\n")  
        f.write(f"- **Name**: Jane Doe\n")  
        f.write(f"- **Email**: scenario2@example.com\n")  
        f.write(f"- **Phone**: 555-0002\n")  
        f.write(f"- **Address**: 234 Elm St, Town\n")  
        f.write(f"- **Loyalty Level**: Gold\n")  
        f.write(f"- **Scenario Description**: Customer experiencing slower internet speeds than expected.\n")  
        f.write("\n---\n\n")  
  
        # Scenario 3: Traveling abroad, phone plan  
        c.execute("""  
            INSERT INTO Customers (first_name, last_name, email, phone, address, loyalty_level)  
            VALUES (?, ?, ?, ?, ?, ?)  
        """, ("Mark", "Doe", "scenario3@example.com", "555-0003", "345 Oak St, Village", "Bronze"))  
        scenario3_cust = c.lastrowid  
  
        start_s3 = BASE_DATE - timedelta(days=90)  
        end_s3 = start_s3 + timedelta(days=365)  
  
        c.execute("""  
            INSERT INTO Subscriptions  
            (customer_id, product_id, start_date, end_date, status, roaming_enabled, service_status)  
            VALUES (?, ?, ?, ?, ?, ?, ?)  
        """, (scenario3_cust, product_ids["Contoso Mobile Plan"], start_s3.strftime("%Y-%m-%d"), end_s3.strftime("%Y-%m-%d"), "active", 0, "normal"))  
  
        # Write scenario 3 to markdown  
        f.write(f"## Scenario 3: Traveling Abroad\n")  
        f.write(f"- **Customer ID**: {scenario3_cust}\n")  
        f.write(f"- **Name**: Mark Doe\n")  
        f.write(f"- **Email**: scenario3@example.com\n")  
        f.write(f"- **Phone**: 555-0003\n")  
        f.write(f"- **Address**: 345 Oak St, Village\n")  
        f.write(f"- **Loyalty Level**: Bronze\n")  
        f.write(f"- **Scenario Description**: I'm traveling abroad next month. What should I do about my phone plan?.\n")  
        f.write("\n---\n\n")  
  
        # Scenario 4: Locked out of account  
        c.execute("""  
            INSERT INTO Customers (first_name, last_name, email, phone, address, loyalty_level)  
            VALUES (?, ?, ?, ?, ?, ?)  
        """, ("Alice", "Doe", "scenario4@example.com", "555-0004", "456 Pine St, Hamlet", "Gold"))  
        scenario4_cust = c.lastrowid  
  
        event_time_4 = BASE_DATE - timedelta(minutes=15)  
        c.execute("""  
            INSERT INTO SecurityLogs (customer_id, event_type, event_timestamp, description)  
            VALUES (?, ?, ?, ?)  
        """, (scenario4_cust, "account_locked", event_time_4.strftime("%Y-%m-%d %H:%M:%S"), "Exceeded login attempts; account locked"))  
  
        # Write scenario 4 to markdown  
        f.write(f"## Scenario 4: Account Locked\n")  
        f.write(f"- **Customer ID**: {scenario4_cust}\n")  
        f.write(f"- **Name**: Alice Doe\n")  
        f.write(f"- **Email**: scenario4@example.com\n")  
        f.write(f"- **Phone**: 555-0004\n")  
        f.write(f"- **Address**: 456 Pine St, Hamlet\n")  
        f.write(f"- **Loyalty Level**: Gold\n")  
        f.write(f"- **Scenario Description**: I tried logging into my account, but it says I'm locked out. Can you help?.\n")  
        f.write("\n---\n\n")  
  
        # Scenario 5: Discounts/promotions  
        c.execute("""  
            INSERT INTO Customers (first_name, last_name, email, phone, address, loyalty_level)  
            VALUES (?, ?, ?, ?, ?, ?)  
        """, ("Ron", "Doe", "scenario5@example.com", "555-0005", "567 Maple St, Metropolis", "Gold"))  
        scenario5_cust = c.lastrowid  
  
        start_s5 = BASE_DATE - timedelta(days=10)  
        end_s5 = start_s5 + timedelta(days=365)  
  
        c.execute("""  
            INSERT INTO Subscriptions  
            (customer_id, product_id, start_date, end_date, status, roaming_enabled, service_status)  
            VALUES (?, ?, ?, ?, ?, ?, ?)  
        """, (scenario5_cust, product_ids["Contoso Mobile Plan"], start_s5.strftime("%Y-%m-%d"), end_s5.strftime("%Y-%m-%d"), "active", 0, "normal"))  
  
        # Write scenario 5 to markdown  
        f.write(f"## Scenario 5: Discounts/Promotions\n")  
        f.write(f"- **Customer ID**: {scenario5_cust}\n")  
        f.write(f"- **Name**: Ron Doe\n")  
        f.write(f"- **Email**: scenario5@example.com\n")  
        f.write(f"- **Phone**: 555-0005\n")  
        f.write(f"- **Address**: 567 Maple St, Metropolis\n")  
        f.write(f"- **Loyalty Level**: Gold\n")  
        f.write(f"- **Scenario Description**: Do I qualify for any discounts or promotions.\n")  
        f.write("\n---\n\n")  
  
        # Scenario 6: Return a recently purchased product  
        c.execute("""  
            INSERT INTO Customers (first_name, last_name, email, phone, address, loyalty_level)  
            VALUES (?, ?, ?, ?, ?, ?)  
        """, ("Mary", "Doe", "scenario6@example.com", "555-0006", "678 Birch St, Capital", "Silver"))  
        scenario6_cust = c.lastrowid  
  
        order_date_6 = BASE_DATE - timedelta(days=5)  
        c.execute("""  
            INSERT INTO Orders (customer_id, product_id, order_date, amount, order_status)  
            VALUES (?, ?, ?, ?, ?)  
        """, (scenario6_cust, product_ids["Contoso Mobile Plan"], order_date_6.strftime("%Y-%m-%d"), 75.00, "returned"))  
  
        # Write scenario 6 to markdown  
        f.write(f"## Scenario 6: Product Return\n")  
        f.write(f"- **Customer ID**: {scenario6_cust}\n")  
        f.write(f"- **Name**: Mary Doe\n")  
        f.write(f"- **Email**: scenario6@example.com\n")  
        f.write(f"- **Phone**: 555-0006\n")  
        f.write(f"- **Address**: 678 Birch St, Capital\n")  
        f.write(f"- **Loyalty Level**: Silver\n")  
        f.write(f"- **Scenario Description**: customer wants to undertand process to return recently purchased product.\n")  
        f.write("\n---\n\n")  

  
    # ─────────────────────────────────────────────────────────────────────────────  
    # Insert knowledge base documents from kb.json  
    # ─────────────────────────────────────────────────────────────────────────────  
    with open("kb.json", "r", encoding="utf-8") as f:  
        kb_data = json.load(f)  
  
    for doc in kb_data:  
        title = doc["document_title"]  
        doc_type = doc["doc_type"]  
        content = doc["document_content"]  
        topic_embed = get_embedding(title)  
          
        c.execute("""  
            INSERT INTO KnowledgeDocuments (title, doc_type, content, topic_embedding)  
            VALUES (?, ?, ?, ?)  
        """, (title, doc_type, content, json.dumps(topic_embed)))  
  
    conn.commit()  
  
def main():  
    conn = sqlite3.connect(DB_NAME)  
    create_tables(conn)  
    populate_data(conn)  
    conn.close()  
    print("Database populated with sample data (using BASE_DATE) and extended knowledge base.")  
    print("Customer scenarios exported to markdown file.")  

if __name__ == "__main__":  
    main()  