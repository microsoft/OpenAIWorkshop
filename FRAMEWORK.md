
# Microsoft AI Agentic Workshop Framework 
  
This document describes the framework and resources used by the different Agent Designs for AI Agentic Workshop from Microsoft. 
Users are not expected to make any modifications to this framework for this workshop as the main focus is on the Agentic implementations. 

## 1. Model Context Protocol API Service Endpoints  
  
**The following services are exposed as tools for AI Agents:**  
  
- `get_all_customers`: List all customers with basic info.  
- `get_customer_detail`: Get a full customer profile including their subscriptions.  
- `get_subscription_detail`: Detailed subscription view including invoices (with payments) and service incidents.  
- `get_invoice_payments`: Return invoice-level payments list.  
- `pay_invoice`: Record a payment for a given invoice and get new outstanding balance.  
- `get_data_usage`: Daily data-usage records for a subscription over a date range (optional aggregation).  
- `get_promotions`: List every active promotion (no filtering).  
- `get_eligible_promotions`: Promotions eligible for a given customer (evaluates basic loyalty/date criteria).  
- `search_knowledge_base`: Semantic search on policy/procedure knowledge documents.  
- `get_security_logs`: Security events for a customer (newest first).  
- `get_customer_orders`: All orders placed by a customer.  
- `get_support_tickets`: Retrieve support tickets for a customer (optionally filter by open status).  
- `create_support_ticket`: Create a new support ticket for a customer.  
- `get_products`: List or search available products (optional category filter).  
- `get_product_detail`: Return a single product by ID.  
- `update_subscription`: Update one or more mutable fields on a subscription.  
- `unlock_account`: Unlock a customer account locked for security reasons.  
- `get_billing_summary`: What does a customer currently owe across all subscriptions?  
  
---  
  
## 2. Backend  
  
## 3. Frontend

## 4. Agent BaseModel
  