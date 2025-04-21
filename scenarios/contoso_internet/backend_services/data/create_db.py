#!/usr/bin/env python3  
"""  
Creates   contoso.db   (SQLite) plus   customer_scenarios.md  
The DB contains 250 random customers + 9 deterministic scenarios that require  
multi‑table reasoning & KB look‑ups.  The markdown now includes an  
“answer‑key / how‑the‑agent‑should‑solve” section for every scenario.  
  
Major changes vs v1  
───────────────────  
• deterministic RNG  (random.seed / Faker.seed)  for identical re‑runs  
• indexes on all FK columns  → faster joins for the agent  
• write_md_block()  now prints Challenge + Solution  
• richer scenario data (partial/failed payments, usage that exceeds caps, etc.)  
• optional Azure OpenAI embeddings – falls back to zero‑vector if creds missing  
"""  
  
import os, random, json, math, sqlite3, contextlib  
from datetime import datetime, timedelta  
from pathlib import Path  
from faker import Faker  
  
# ──────────────────────────────────  RNG SETUP  ──────────────────────────  
SEED = 42  
random.seed(SEED)  
fake = Faker()  
fake.seed_instance(SEED)  
  
# ─────────────────────────────  OpenAI Embeddings  ───────────────────────  
def try_import_openai():  
    try:  
        from openai import AzureOpenAI  
        return AzureOpenAI  
    except Exception:  
        return None  
  
AzureOpenAI = try_import_openai()  
  
def get_embedding(text: str):  
    """Return embedding list[float]; dummy zeros when Azure creds unavailable."""  
    if (  
        AzureOpenAI is None  
        or not os.getenv("AZURE_OPENAI_API_KEY")  
        or not os.getenv("AZURE_OPENAI_ENDPOINT")  
    ):  
        return [0.0] * 1536                                   # gpt‑4‑class size  
    client = AzureOpenAI(  
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),  
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),  
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),  
    )  
    model = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")  
    text = text.replace("\n", " ")  
    return client.embeddings.create(input=[text], model=model).data[0].embedding  
  
# ─────────────────────────────  GLOBALS  ─────────────────────────────────  
DB_NAME   = "contoso.db"  
BASE_DATE = datetime.now()  
  
##############################################################################  
#                              TABLE DDL                                     #  
##############################################################################  
def create_tables(conn: sqlite3.Connection):  
    c = conn.cursor()  
  
    # Drop in reverse dependency order just to be safe  
    tables = [  
        "KnowledgeDocuments", "ServiceIncidents", "DataUsage", "SupportTickets",  
        "Orders", "SecurityLogs", "Promotions", "Payments", "Invoices",  
        "Subscriptions", "Products", "Customers"  
    ]  
    for t in tables:  
        c.execute(f"DROP TABLE IF EXISTS {t}")  
  
    # Customers  
    c.execute("""  
        CREATE TABLE Customers(  
            customer_id   INTEGER PRIMARY KEY AUTOINCREMENT,  
            first_name    TEXT NOT NULL,  
            last_name     TEXT NOT NULL,  
            email         TEXT UNIQUE,  
            phone         TEXT,  
            address       TEXT,  
            loyalty_level TEXT  
        )  
    """)  
  
    # Products  
    c.execute("""  
        CREATE TABLE Products(  
            product_id   INTEGER PRIMARY KEY AUTOINCREMENT,  
            name         TEXT NOT NULL,  
            description  TEXT,  
            category     TEXT,  
            monthly_fee  REAL  
        )  
    """)  
  
    # Subscriptions  
    c.execute("""  
        CREATE TABLE Subscriptions(  
            subscription_id  INTEGER PRIMARY KEY AUTOINCREMENT,  
            customer_id      INTEGER NOT NULL,  
            product_id       INTEGER NOT NULL,  
            start_date       TEXT,  
            end_date         TEXT,  
            status           TEXT,  
            roaming_enabled  INTEGER DEFAULT 0,  
            service_status   TEXT,  
            speed_tier       TEXT,  
            data_cap_gb      INTEGER,  
            autopay_enabled  INTEGER DEFAULT 1,  
            FOREIGN KEY(customer_id) REFERENCES Customers(customer_id),  
            FOREIGN KEY(product_id)  REFERENCES Products(product_id)  
        )  
    """)  
  
    # Invoices  
    c.execute("""  
        CREATE TABLE Invoices(  
            invoice_id      INTEGER PRIMARY KEY AUTOINCREMENT,  
            subscription_id INTEGER,  
            invoice_date    TEXT,  
            amount          REAL,  
            description     TEXT,  
            due_date        TEXT,  
            FOREIGN KEY (subscription_id) REFERENCES Subscriptions(subscription_id)  
        )  
    """)  
  
    # Payments  
    c.execute("""  
        CREATE TABLE Payments(  
            payment_id   INTEGER PRIMARY KEY AUTOINCREMENT,  
            invoice_id   INTEGER,  
            payment_date TEXT,  
            amount       REAL,  
            method       TEXT,  
            status       TEXT,  
            FOREIGN KEY (invoice_id) REFERENCES Invoices(invoice_id)  
        )  
    """)  
  
    # Promotions  
    c.execute("""  
        CREATE TABLE Promotions(  
            promotion_id       INTEGER PRIMARY KEY AUTOINCREMENT,  
            product_id         INTEGER,  
            name               TEXT,  
            description        TEXT,  
            eligibility_criteria TEXT,  
            start_date         TEXT,  
            end_date           TEXT,  
            discount_percent   INTEGER,  
            FOREIGN KEY (product_id) REFERENCES Products(product_id)  
        )  
    """)  
  
    # Security Logs  
    c.execute("""  
        CREATE TABLE SecurityLogs(  
            log_id         INTEGER PRIMARY KEY AUTOINCREMENT,  
            customer_id    INTEGER,  
            event_type     TEXT,  
            event_timestamp TEXT,  
            description    TEXT,  
            FOREIGN KEY (customer_id) REFERENCES Customers(customer_id)  
        )  
    """)  
  
    # Orders  
    c.execute("""  
        CREATE TABLE Orders(  
            order_id     INTEGER PRIMARY KEY AUTOINCREMENT,  
            customer_id  INTEGER,  
            product_id   INTEGER,  
            order_date   TEXT,  
            amount       REAL,  
            order_status TEXT,  
            FOREIGN KEY(customer_id) REFERENCES Customers(customer_id),  
            FOREIGN KEY(product_id)  REFERENCES Products(product_id)  
        )  
    """)  
  
    # Support Tickets  
    c.execute("""  
        CREATE TABLE SupportTickets(  
            ticket_id       INTEGER PRIMARY KEY AUTOINCREMENT,  
            customer_id     INTEGER,  
            subscription_id INTEGER,  
            category        TEXT,  
            opened_at       TEXT,  
            closed_at       TEXT,  
            status          TEXT,  
            priority        TEXT,  
            subject         TEXT,  
            description     TEXT,  
            cs_agent        TEXT,  
            FOREIGN KEY(customer_id)     REFERENCES Customers(customer_id),  
            FOREIGN KEY(subscription_id) REFERENCES Subscriptions(subscription_id)  
        )  
    """)  
  
    # DataUsage  
    c.execute("""  
        CREATE TABLE DataUsage(  
            usage_id        INTEGER PRIMARY KEY AUTOINCREMENT,  
            subscription_id INTEGER,  
            usage_date      TEXT,  
            data_used_mb    INTEGER,  
            voice_minutes   INTEGER,  
            sms_count       INTEGER,  
            FOREIGN KEY(subscription_id) REFERENCES Subscriptions(subscription_id)  
        )  
    """)  
  
    # Service Incidents  
    c.execute("""  
        CREATE TABLE ServiceIncidents(  
            incident_id       INTEGER PRIMARY KEY AUTOINCREMENT,  
            subscription_id   INTEGER,  
            incident_date     TEXT,  
            description       TEXT,  
            resolution_status TEXT,  
            FOREIGN KEY(subscription_id) REFERENCES Subscriptions(subscription_id)  
        )  
    """)  
  
    # Knowledge Base  
    c.execute("""  
        CREATE TABLE KnowledgeDocuments(  
            document_id     INTEGER PRIMARY KEY AUTOINCREMENT,  
            title           TEXT,  
            doc_type        TEXT,  
            content         TEXT,  
            topic_embedding TEXT  
        )  
    """)  
  
    # ────────────────────────── Indexes for fast lookup ─────────────────  
    idx_cmds = [  
        "CREATE INDEX idx_subs_customer    ON Subscriptions(customer_id)",  
        "CREATE INDEX idx_inv_sub          ON Invoices(subscription_id)",  
        "CREATE INDEX idx_pay_inv          ON Payments(invoice_id)",  
        "CREATE INDEX idx_usage_sub        ON DataUsage(subscription_id)",  
        "CREATE INDEX idx_tickets_cust     ON SupportTickets(customer_id)",  
        "CREATE INDEX idx_tickets_sub      ON SupportTickets(subscription_id)",  
        "CREATE INDEX idx_inc_sub          ON ServiceIncidents(subscription_id)",  
    ]  
    for cmd in idx_cmds:  
        c.execute(cmd)  
  
    conn.commit()  
  
##############################################################################  
#                              DATA SEEDING                                  #  
##############################################################################  
def populate_data(conn: sqlite3.Connection, markdown_file="customer_scenarios.md"):  
    c = conn.cursor()  
  
    # ========================= 1. RANDOM "NOISE" DATA ======================  
    loyalty_levels = ["Bronze", "Silver", "Gold"]  
    all_customer_ids = []  
  
    # Customers  
    for _ in range(250):  
        first, last = fake.first_name(), fake.last_name()  
        c.execute(  
            """INSERT INTO Customers(first_name,last_name,email,phone,address,loyalty_level)  
               VALUES (?,?,?,?,?,?)""",  
            (  
                first,  
                last,  
                fake.unique.email(),  
                fake.phone_number(),  
                fake.address().replace("\n", ", "),  
                random.choice(loyalty_levels),  
            ),  
        )  
        all_customer_ids.append(c.lastrowid)  
  
    # Products  
    products = [  
        (  
            "Contoso Mobile Plan",  
            "Unlimited talk & text; data‑cap varies by tier.",  
            "mobile",  
            50.00,  
        ),  
        (  
            "Contoso Internet Plan",  
            "Fiber or cable internet with several speed tiers.",  
            "internet",  
            60.00,  
        ),  
        (  
            "Contoso Bundle Plan",  
            "Discount when you bundle mobile + internet.",  
            "bundle",  
            90.00,  
        ),  
        ("Contoso International Roaming", "Add‑on for travellers.", "addon", 20.00),  
    ]  
    product_ids = {}  
    for name, desc, cat, fee in products:  
        c.execute(  
            """INSERT INTO Products(name,description,category,monthly_fee)  
               VALUES (?,?,?,?)""",  
            (name, desc, cat, fee),  
        )  
        product_ids[name] = c.lastrowid  
  
    # Subscriptions  
    subscription_ids = []  
    speed_choices = ["50Mbps", "100Mbps", "300Mbps", "1Gbps"]  
    service_statuses = ["normal", "slow", "offline"]  
    for cid in all_customer_ids:  
        chosen_product_name = random.choice(products)[0]  
        product_id = product_ids[chosen_product_name]  
        start_date = BASE_DATE - timedelta(days=random.randint(60, 450))  
        end_date = start_date + timedelta(days=365)  
        c.execute(  
            """  
            INSERT INTO Subscriptions  
                (customer_id,product_id,start_date,end_date,status,roaming_enabled,  
                 service_status,speed_tier,data_cap_gb,autopay_enabled)  
            VALUES (?,?,?,?,?,?,?,?,?,?)  
        """,  
            (  
                cid,  
                product_id,  
                start_date.strftime("%Y-%m-%d"),  
                end_date.strftime("%Y-%m-%d"),  
                random.choices(["active", "inactive"], [0.88, 0.12])[0],  
                random.choice([0, 1]),  
                random.choices(service_statuses, [0.8, 0.15, 0.05])[0],  
                random.choice(speed_choices),  
                random.choice([10, 20, 50, 100, None]),  
                random.choice([0, 1]),  
            ),  
        )  
        subscription_ids.append(c.lastrowid)  
  
    # Invoices + Payments  
    payment_methods = ["credit_card", "ach", "paypal", "apple_pay"]  
    for sub_id in subscription_ids:  
        for _ in range(random.randint(8, 14)):  
            invoice_date = BASE_DATE - timedelta(days=random.randint(1, 120))  
            due_date = invoice_date + timedelta(days=14)  
            amount = round(random.uniform(40, 130), 2)  
            c.execute(  
                """INSERT INTO Invoices(subscription_id,invoice_date,amount,description,due_date)  
                   VALUES (?,?,?,?,?)""",  
                (  
                    sub_id,  
                    invoice_date.strftime("%Y-%m-%d"),  
                    amount,  
                    fake.sentence(nb_words=6),  
                    due_date.strftime("%Y-%m-%d"),  
                ),  
            )  
            invoice_id = c.lastrowid  
  
            # Random payment status  
            rand_val = random.random()  
            if rand_val < 0.75:  
                payment_status = "successful"  
                paid_amount = amount  
            elif rand_val < 0.85:  
                payment_status = "failed"  
                paid_amount = 0  
            else:  
                payment_status = "partial"  
                paid_amount = round(amount * random.uniform(0.2, 0.8), 2)  
  
            pay_date = due_date + timedelta(days=random.randint(0, 10))  
            c.execute(  
                """INSERT INTO Payments(invoice_id, payment_date, amount, method, status)  
                   VALUES (?,?,?,?,?)""",  
                (  
                    invoice_id,  
                    pay_date.strftime("%Y-%m-%d"),  
                    paid_amount,  
                    random.choice(payment_methods),  
                    payment_status,  
                ),  
            )  
  
    # DataUsage  
    for sub_id in subscription_ids:  
        usage_rows = []  
        for day_offset in range(60):  
            day_date = (BASE_DATE - timedelta(days=day_offset)).strftime("%Y-%m-%d")  
            usage_rows.append(  
                (  
                    sub_id,  
                    day_date,  
                    random.randint(50, 1200),  
                    random.randint(0, 60),  
                    random.randint(0, 40),  
                )  
            )  
        c.executemany(  
            """INSERT INTO DataUsage(subscription_id,usage_date,data_used_mb,voice_minutes,sms_count)  
               VALUES (?,?,?,?,?)""",  
            usage_rows,  
        )  
  
    # Support Tickets  
    categories = ["billing", "technical", "account", "call_drop", "sms_issue"]  
    priorities = ["low", "normal", "high", "urgent"]  
    ticket_rows = []  
    for _ in range(120):  
        cid = random.choice(all_customer_ids)  
        sid = random.choice(subscription_ids)  
        opened = BASE_DATE - timedelta(hours=random.randint(1, 2000))  
        status = random.choice(["open", "pending", "closed"])  
        closed = None if status != "closed" else opened + timedelta(hours=random.randint(1, 48))  
        ticket_rows.append(  
            (  
                cid,  
                sid,  
                random.choice(categories),  
                opened.strftime("%Y-%m-%d %H:%M:%S"),  
                None if closed is None else closed.strftime("%Y-%m-%d %H:%M:%S"),  
                status,  
                random.choice(priorities),  
                fake.sentence(nb_words=6),  
                fake.text(max_nb_chars=120),  
                fake.first_name(),  
            )  
        )  
    c.executemany(  
        """INSERT INTO SupportTickets(customer_id,subscription_id,category,opened_at,closed_at,  
                                       status,priority,subject,description,cs_agent)  
           VALUES (?,?,?,?,?,?,?,?,?,?)""",  
        ticket_rows,  
    )  
  
    # Promotions  
    promotion_data = [  
        (  
            product_ids["Contoso Mobile Plan"],  
            "Mobile Loyalty Discount",  
            "10% discount for Gold members on the mobile plan.",  
            "loyalty_level = 'Gold'",  
            "2023-01-01",  
            "2023-12-31",  
            10,  
        ),  
        (  
            product_ids["Contoso Internet Plan"],  
            "New Internet Sign‑up Bonus",  
            "15% off for new internet subscribers.",  
            "subscription_start within last 90 days",  
            "2023-06-01",  
            "2023-09-30",  
            15,  
        ),  
        # Future promotion to test scenario 5 (eligibility denial)  
        (  
            product_ids["Contoso Mobile Plan"],  
            "Summer2025 Teaser Promo",  
            "Early‑bird discount starting next summer.",  
            "loyalty_level = 'Gold'",  
            "2025-06-01",  
            "2025-08-31",  
            15,  
        ),  
    ]  
    c.executemany(  
        """INSERT INTO Promotions(product_id,name,description,eligibility_criteria,  
                                   start_date,end_date,discount_percent)  
           VALUES (?,?,?,?,?,?,?)""",  
        promotion_data,  
    )  
  
    # Security Logs  
    event_types = ["login_attempt", "account_locked"]  
    sec_rows = []  
    for _ in range(40):  
        cust_id = random.choice(all_customer_ids)  
        event_time = BASE_DATE - timedelta(minutes=random.randint(1, 3000))  
        sec_rows.append(  
            (  
                cust_id,  
                random.choice(event_types),  
                event_time.strftime("%Y-%m-%d %H:%M:%S"),  
                fake.sentence(nb_words=8),  
            )  
        )  
    c.executemany(  
        """INSERT INTO SecurityLogs(customer_id,event_type,event_timestamp,description)  
           VALUES (?,?,?,?)""",  
        sec_rows,  
    )  
  
    # Orders  
    order_statuses = ["delivered", "completed", "pending", "returned"]  
    order_rows = []  
    for _ in range(120):  
        cust_id = random.choice(all_customer_ids)  
        product_id = random.choice(list(product_ids.values()))  
        order_date = BASE_DATE - timedelta(days=random.randint(1, 120))  
        order_rows.append(  
            (  
                cust_id,  
                product_id,  
                order_date.strftime("%Y-%m-%d"),  
                round(random.uniform(10, 100), 2),  
                random.choice(order_statuses),  
            )  
        )  
    c.executemany(  
        """INSERT INTO Orders(customer_id,product_id,order_date,amount,order_status)  
           VALUES (?,?,?,?,?)""",  
        order_rows,  
    )  
  
    # Service incidents (noise)  
    inc_rows = []  
    for _ in range(60):  
        sid = random.choice(subscription_ids)  
        incident_date = BASE_DATE - timedelta(days=random.randint(1, 90))  
        inc_rows.append(  
            (  
                sid,  
                incident_date.strftime("%Y-%m-%d"),  
                fake.sentence(nb_words=10),  
                random.choice(["investigating", "resolved"]),  
            )  
        )  
    c.executemany(  
        """INSERT INTO ServiceIncidents(subscription_id,incident_date,description,resolution_status)  
           VALUES (?,?,?,?)""",  
        inc_rows,  
    )  
  
    # ========================= 2. DETERMINISTIC SCENARIOS ===================  
    md = open(markdown_file, "w", encoding="utf-8")  
    md.write("# Customer Scenarios –  Answer Key Included\n\n")  
  
    def write_md_block(idx, title, cust_id, name, email, phone, addr,  
                       loyalty, desc, solution_md):  
        md.write(f"## Scenario {idx}: {title}\n")  
        md.write(f"- **Customer ID**: {cust_id}\n")  
        md.write(f"- **Name**       : {name}\n")  
        md.write(f"- **Email**      : {email}\n")  
        md.write(f"- **Phone**      : {phone}\n")  
        md.write(f"- **Address**    : {addr}\n")  
        md.write(f"- **Loyalty**    : {loyalty}\n")  
        md.write(f"\n### Challenge\n{desc}\n")  
        md.write(f"\n### How the AI agent should solve\n{solution_md.strip()}\n")  
        md.write("\n---\n\n")  
  
    # Helper insertion functions  
    def add_customer(**kw):  
        c.execute(  
            """INSERT INTO Customers(first_name,last_name,email,phone,address,loyalty_level)  
               VALUES (?,?,?,?,?,?)""",  
            (kw["first"], kw["last"], kw["email"], kw["phone"], kw["addr"], kw["loyalty"]),  
        )  
        return c.lastrowid  
  
    def add_subscription(cust_id, **kw):  
        start = BASE_DATE - timedelta(days=60)  
        end = start + timedelta(days=365)  
        c.execute(  
            """INSERT INTO Subscriptions  
               (customer_id,product_id,start_date,end_date,status,roaming_enabled,  
                service_status,speed_tier,data_cap_gb,autopay_enabled)  
               VALUES (?,?,?,?,?,?,?,?,?,?)""",  
            (  
                cust_id,  
                product_ids[kw["product"]],  
                start.strftime("%Y-%m-%d"),  
                end.strftime("%Y-%m-%d"),  
                kw["status"],  
                kw["roaming"],  
                kw["service_status"],  
                kw.get("speed_tier", "NA"),  
                kw.get("data_cap_gb"),  
                kw.get("autopay_enabled", 1),  
            ),  
        )  
        return c.lastrowid  
  
    def add_invoice(sub_id, *, amount, desc, when_days, mark_unpaid=True):  
        inv_date = BASE_DATE + timedelta(days=when_days)  
        due_date = inv_date + timedelta(days=14)  
        c.execute(  
            """INSERT INTO Invoices(subscription_id,invoice_date,amount,description,due_date)  
               VALUES (?,?,?,?,?)""",  
            (  
                sub_id,  
                inv_date.strftime("%Y-%m-%d"),  
                amount,  
                desc,  
                due_date.strftime("%Y-%m-%d"),  
            ),  
        )  
        inv_id = c.lastrowid  
        if mark_unpaid:  
            c.execute(  
                """INSERT INTO Payments(invoice_id,payment_date,amount,method,status)  
                   VALUES (?,?,?,?,?)""",  
                (inv_id, None, 0.0, "credit_card", "pending"),  
            )  
        return inv_id  
  
    # ─────────────────────────  SCENARIO 1  ─────────────────────────────  
    sc1_cust = add_customer(  
        first="John",  
        last="Doe",  
        email="scenario1@example.com",  
        phone="555‑0001",  
        addr="123 Main St, City",  
        loyalty="Silver",  
    )  
    sc1_sub = add_subscription(  
        sc1_cust,  
        product="Contoso Internet Plan",  
        status="active",  
        roaming=0,  
        service_status="normal",  
        speed_tier="300Mbps",  
        data_cap_gb=10 # explicitly setting the data cap to 10GB

    )  
    # Prior normal invoice  
    add_invoice(sc1_sub, amount=60.00, desc="Standard monthly charge", when_days=-30, mark_unpaid=False)  
    # Surprise overage invoice  
    inv_over = add_invoice(sc1_sub, amount=150.00, desc="Unexpected overage charges", when_days=-1)  
  
    # Also insert partial payment equal to 50  (so remaining 100 unpaid)  
    c.execute(  
        """INSERT INTO Payments(invoice_id,payment_date,amount,method,status)  
           VALUES (?,?,?,?,?)""",  
        (  
            inv_over,  
            (BASE_DATE + timedelta(days=3)).strftime("%Y-%m-%d"),  
            50.00,  
            "credit_card",  
            "partial",  
        ),  
    )  
  
    # Seed large DataUsage (simulate 12 GB extra)  
    for d in range(28, 0, -1):  
        c.execute(  
            """INSERT INTO DataUsage(subscription_id,usage_date,data_used_mb,voice_minutes,sms_count)  
               VALUES (?,?,?,?,?)""",  
            (sc1_sub, (BASE_DATE - timedelta(days=d)).strftime("%Y-%m-%d"),  
             random.randint(800, 900), 0, 0),  
        )  
  
    write_md_block(  
        1,  
        "Invoice Higher Than Usual",  
        sc1_cust,  
        "John Doe",  
        "scenario1@example.com",  
        "555‑0001",  
        "123 Main St, City",  
        "Silver",  
        "Latest invoice shows $150, 2.5× the usual amount.",  
        """  
1. SELECT last 6 invoices → detect $150 outlier (std‑dev or >50 % above mean).  
2. Cross‑check DataUsage for same billing cycle → find ~22 GB vs plan’s 10 GB cap.  
3. Quote **Data Overage Policy – “may retroactively upgrade within 15 days”**.  
4. Offer: (a) file invoice‑adjustment; (b) upgrade plan & credit overage pro‑rata.  
5. Note that $50 already paid; $100 balance remains.  
"""  
    )  
  
    # ─────────────────────────  SCENARIO 2  ─────────────────────────────  
    sc2_cust = add_customer(  
        first="Jane",  
        last="Doe",  
        email="scenario2@example.com",  
        phone="555‑0002",  
        addr="234 Elm St, Town",  
        loyalty="Gold",  
    )  
    sc2_sub = add_subscription(  
        sc2_cust,  
        product="Contoso Internet Plan",  
        status="active",  
        roaming=0,  
        service_status="slow",  
        speed_tier="1Gbps",  
    )  
  
    # Insert open ServiceIncident  
    c.execute(  
        """INSERT INTO ServiceIncidents(subscription_id,incident_date,description,resolution_status)  
           VALUES (?,?,?,?)""",  
        (  
            sc2_sub,  
            (BASE_DATE - timedelta(days=2)).strftime("%Y-%m-%d"),  
            "Customer reports slow speeds for 3 days.",  
            "investigating",  
        ),  
    )  
    # Insert DataUsage rows showing very low usage (symptom)  
    for d in range(3):  
        c.execute(  
            """INSERT INTO DataUsage(subscription_id,usage_date,data_used_mb,voice_minutes,sms_count)  
               VALUES (?,?,?,?,?)""",  
            (sc2_sub, (BASE_DATE - timedelta(days=d)).strftime("%Y-%m-%d"), 50, 0, 0),  
        )  
  
    write_md_block(  
        2,  
        "Internet Slower Than Before",  
        sc2_cust,  
        "Jane Doe",  
        "scenario2@example.com",  
        "555‑0002",  
        "234 Elm St, Town",  
        "Gold",  
        "Throughput much lower than advertised 1 Gbps tier.",  
        """  
1. Confirm Subscriptions.service_status = 'slow'.  
2. Query ServiceIncidents – open ticket still 'investigating'.  
3. Use KB: **Troubleshooting Slow Internet – Basic Steps**.  
4. Ask customer to run speed‑test, reboot; escalate if still <25 % of tier.  
"""  
    )  
  
    # ─────────────────────────  SCENARIO 3  ─────────────────────────────  
    sc3_cust = add_customer(  
        first="Mark",  
        last="Doe",  
        email="scenario3@example.com",  
        phone="555‑0003",  
        addr="345 Oak St, Village",  
        loyalty="Bronze",  
    )  
    sc3_sub = add_subscription(  
        sc3_cust,  
        product="Contoso Mobile Plan",  
        status="active",  
        roaming=0,  
        service_status="normal",  
    )  
    write_md_block(  
        3,  
        "Travelling Abroad – Needs Roaming",  
        sc3_cust,  
        "Mark Doe",  
        "scenario3@example.com",  
        "555‑0003",  
        "345 Oak St, Village",  
        "Bronze",  
        "Leaving for Spain in 2 days, unsure how to enable roaming.",  
        """  
1. Subscriptions.roaming_enabled = 0 → verify not active.  
2. Check product offerings → suggest 'International Roaming' add‑on.  
3. Quote **International Roaming Options Explained**: must activate ≥3 days ahead.  
4. Offer immediate activation with pro‑rated charges.  
"""  
    )  
  
    # ─────────────────────────  SCENARIO 4  ─────────────────────────────  
    sc4_cust = add_customer(  
        first="Alice",  
        last="Doe",  
        email="scenario4@example.com",  
        phone="555‑0004",  
        addr="456 Pine St, Hamlet",  
        loyalty="Gold",  
    )  
    sc4_sub = add_subscription(  
        sc4_cust,  
        product="Contoso Mobile Plan",  
        status="active",  
        roaming=0,  
        service_status="normal",  
    )  
    # Flood of login_attempts then account_locked  
    for i in range(8):  
        c.execute(  
            """INSERT INTO SecurityLogs(customer_id,event_type,event_timestamp,description)  
               VALUES (?,?,?,?)""",  
            (  
                sc4_cust,  
                "login_attempt",  
                (BASE_DATE - timedelta(minutes=20 - i)).strftime("%Y-%m-%d %H:%M:%S"),  
                "Failed login",  
            ),  
        )  
    c.execute(  
        """INSERT INTO SecurityLogs(customer_id,event_type,event_timestamp,description)  
           VALUES (?,?,?,?)""",  
        (  
            sc4_cust,  
            "account_locked",  
            (BASE_DATE - timedelta(minutes=12)).strftime("%Y-%m-%d %H:%M:%S"),  
            "Exceeded login attempts; account locked",  
        ),  
    )  
  
    write_md_block(  
        4,  
        "Account Locked",  
        sc4_cust,  
        "Alice Doe",  
        "scenario4@example.com",  
        "555‑0004",  
        "456 Pine St, Hamlet",  
        "Gold",  
        "Cannot log in; system says account locked.",  
        """  
1. SELECT * FROM SecurityLogs WHERE customer_id = ? ORDER BY event_timestamp DESC.  
2. Detect 'account_locked' record 12 min ago.  
3. Follow **Account Unlock Procedure – Verification Steps**:   
   • send 2FA code, verify identity, force password reset.  
"""  
    )  
  
    # ─────────────────────────  SCENARIO 5  ─────────────────────────────  
    sc5_cust = add_customer(  
        first="Ron",  
        last="Doe",  
        email="scenario5@example.com",  
        phone="555‑0005",  
        addr="567 Maple St, Metropolis",  
        loyalty="Gold",  
    )  
    sc5_sub = add_subscription(  
        sc5_cust,  
        product="Contoso Mobile Plan",  
        status="active",  
        roaming=0,  
        service_status="normal",  
    )  
    write_md_block(  
        5,  
        "Promotion / Discount Eligibility",  
        sc5_cust,  
        "Ron Doe",  
        "scenario5@example.com",  
        "555‑0005",  
        "567 Maple St, Metropolis",  
        "Gold",  
        "Wants to know what promos he qualifies for.",  
        """  
1. Look up Promotions where eligibility_criteria matches loyalty_level = 'Gold'  
   AND current_date between start_date/end_date.  
2. Return 'Mobile Loyalty Discount' (10%).  
3. Summer2025 Teaser Promo is FUTURE – explain not yet active per KB   
   **Promotion Eligibility Guidelines**.  
"""  
    )  
  
    # ─────────────────────────  SCENARIO 6  ─────────────────────────────  
    sc6_cust = add_customer(  
        first="Mary",  
        last="Doe",  
        email="scenario6@example.com",  
        phone="555‑0006",  
        addr="678 Birch St, Capital",  
        loyalty="Silver",  
    )  
    sc6_sub = add_subscription(  
        sc6_cust,  
        product="Contoso Mobile Plan",  
        status="active",  
        roaming=0,  
        service_status="normal",  
    )  
    # Product return 25 days ago  
    c.execute(  
        """INSERT INTO Orders(customer_id,product_id,order_date,amount,order_status)  
           VALUES (?,?,?,?,?)""",  
        (  
            sc6_cust,  
            product_ids["Contoso Mobile Plan"],  
            (BASE_DATE - timedelta(days=25)).strftime("%Y-%m-%d"),  
            75.00,  
            "returned",  
        ),  
    )  
    write_md_block(  
        6,  
        "Product Return Within Window",  
        sc6_cust,  
        "Mary Doe",  
        "scenario6@example.com",  
        "555‑0006",  
        "678 Birch St, Capital",  
        "Silver",  
        "Returned a handset, waiting for refund.",  
        """  
1. Verify Orders.order_status = 'returned' and order_date is 25 days ago < 30‑day window.  
2. Cite **Return Policy and Process**: 7‑10 business days for refund.  
3. If >10 days passed, escalate to fulfilment.  
"""  
    )  
  
    # ─────────────────────────  SCENARIO 7  ─────────────────────────────  
    sc7_cust = add_customer(  
        first="Tom",  
        last="Smith",  
        email="scenario7@example.com",  
        phone="555‑0007",  
        addr="789 Cedar St, Hill",  
        loyalty="Silver",  
    )  
    sc7_sub = add_subscription(  
        sc7_cust,  
        product="Contoso Mobile Plan",  
        status="active",  
        roaming=1,  
        service_status="normal",  
    )  
    opened = BASE_DATE - timedelta(hours=5)  
    ticket_id = c.execute(  
        """INSERT INTO SupportTickets(customer_id,subscription_id,category,opened_at,closed_at,  
                                       status,priority,subject,description,cs_agent)  
           VALUES (?,?,?,?,?,?,?,?,?,?)""",  
        (  
            sc7_cust,  
            sc7_sub,  
            "call_drop",  
            opened.strftime("%Y-%m-%d %H:%M:%S"),  
            None,  
            "open",  
            "high",  
            "Repeated call drops in downtown area",  
            "Dropped calls at 10:05, 10:22, 11:01 near 5th & Pine.",  
            "Liam",  
        ),  
    ).lastrowid  
  
    write_md_block(  
        7,  
        "Frequent Dropped Calls",  
        sc7_cust,  
        "Tom Smith",  
        "scenario7@example.com",  
        "555‑0007",  
        "789 Cedar St, Hill",  
        "Silver",  
        "Calls drop whenever downtown.",  
        """  
1. Review open SupportTickets (category 'call_drop') – capture 3 sample times/locations.  
2. Follow KB **Dropped Call Investigation Workflow**: escalate to RF engineering.  
3. If systemic issue confirmed, apply credit per **Service Reliability SLA – Credit Matrix**.  
"""  
    )  
  
    # ─────────────────────────  SCENARIO 8  ─────────────────────────────  
    sc8_cust = add_customer(  
        first="Sara",  
        last="Lee",  
        email="scenario8@example.com",  
        phone="555‑0008",  
        addr="123 Ocean Blvd, Bay City",  
        loyalty="Gold",  
    )  
    sc8_sub = add_subscription(  
        sc8_cust,  
        product="Contoso Internet Plan",  
        status="inactive",  # suspended  
        roaming=0,  
        service_status="offline",  
        speed_tier="300Mbps",  
        autopay_enabled=0,  
    )  
    inv_date = BASE_DATE - timedelta(days=40)  
    due_date = inv_date + timedelta(days=14)  
    c.execute(  
        """INSERT INTO Invoices(subscription_id,invoice_date,amount,description,due_date)  
           VALUES (?,?,?,?,?)""",  
        (  
            sc8_sub,  
            inv_date.strftime("%Y-%m-%d"),  
            95.50,  
            "Monthly internet fee",  
            due_date.strftime("%Y-%m-%d"),  
        ),  
    )  
    inv_id = c.lastrowid  
    # two failed payment attempts  
    for attempt in range(2):  
        c.execute(  
            """INSERT INTO Payments(invoice_id,payment_date,amount,method,status)  
               VALUES (?,?,?,?,?)""",  
            (  
                inv_id,  
                (due_date + timedelta(days=attempt)).strftime("%Y-%m-%d"),  
                95.50,  
                "credit_card",  
                "failed",  
            ),  
        )  
  
    write_md_block(  
        8,  
        "Overdue Invoice – Service Suspended",  
        sc8_cust,  
        "Sara Lee",  
        "scenario8@example.com",  
        "555‑0008",  
        "123 Ocean Blvd, Bay City",  
        "Gold",  
        "Service suspended due to missed payment; wants late fee waived.",  
        """  
1. Invoice unpaid >14 days; Payments show 2 failed attempts → beyond 10‑day grace.  
2. Account status = 'inactive' (suspended).  
3. Reference **Payment Failure & Reinstatement Rules** for reconnection fee  
   and first‑time waiver eligibility + **Late Payment Fee Policy**.  
4. Offer hardship plan per **Financial Hardship Payment Plan Procedure**.  
"""  
    )  
  
    # ─────────────────────────  SCENARIO 9  ─────────────────────────────  
    sc9_cust = add_customer(  
        first="Alex",  
        last="Brown",  
        email="scenario9@example.com",  
        phone="555‑0009",  
        addr="321 Spruce Ln, Forest",  
        loyalty="Bronze",  
    )  
    sc9_sub = add_subscription(  
        sc9_cust,  
        product="Contoso Mobile Plan",  
        status="active",  
        roaming=1,  
        service_status="normal",  
        data_cap_gb=10,  
    )  
    # 22 GB usage last 30 days  
    for d in range(30):  
        c.execute(  
            """INSERT INTO DataUsage(subscription_id,usage_date,data_used_mb,voice_minutes,sms_count)  
               VALUES (?,?,?,?,?)""",  
            (  
                sc9_sub,  
                (BASE_DATE - timedelta(days=d)).strftime("%Y-%m-%d"),  
                random.randint(700, 900),  
                random.randint(0, 20),  
                random.randint(0, 10),  
            ),  
        )  
    inv_date = BASE_DATE - timedelta(days=1)  
    due_date = inv_date + timedelta(days=14)  
    c.execute(  
        """INSERT INTO Invoices(subscription_id,invoice_date,amount,description,due_date)  
           VALUES (?,?,?,?,?)""",  
        (  
            sc9_sub,  
            inv_date.strftime("%Y-%m-%d"),  
            150.00,  
            "Base plan + 12GB data overage",  
            due_date.strftime("%Y-%m-%d"),  
        ),  
    )  
    write_md_block(  
        9,  
        "Mobile Data Overage Charge",  
        sc9_cust,  
        "Alex Brown",  
        "scenario9@example.com",  
        "555‑0009",  
        "321 Spruce Ln, Forest",  
        "Bronze",  
        "Received $150 bill due to data overage.",  
        """  
1. DataUsage sum for billing cycle ≈22 GB vs 10 GB cap → 12 GB over.  
2. Quote **Data Overage Policy**: can switch to higher tier retroactively  
   within 15 days of invoice; overage will be re‑rated.  
3. Upsell larger plan or unlimited bundle.  
"""  
    )  
  
    md.close()  
  
    # ========================= 3. KNOWLEDGE BASE ===========================  
    with open("kb.json", "r", encoding="utf-8") as jf:  
        kb_docs = json.load(jf)  
    for doc in kb_docs:  
        c.execute(  
            """INSERT INTO KnowledgeDocuments(title,doc_type,content,topic_embedding)  
               VALUES (?,?,?,?)""",  
            (  
                doc["document_title"],  
                doc["doc_type"],  
                doc["document_content"],  
                json.dumps(get_embedding(doc["document_title"])),  
            ),  
        )  
  
    conn.commit()  
  
  
##############################################################################  
def main():  
    with contextlib.closing(sqlite3.connect(DB_NAME)) as conn:  
        create_tables(conn)  
        populate_data(conn)  
    print("✅  contoso.db generated and customer_scenarios.md exported.")  
  
  
if __name__ == "__main__":  
    main()  