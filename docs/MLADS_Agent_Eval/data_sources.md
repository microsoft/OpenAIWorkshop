# Data Sources & Categories — Quick Reference

This document explains the **"5 data sources"** and **"6 categories"** referenced
on slides 1, 7, and 10 of the deck. The workshop's MCP backend persists data in
12 Cosmos containers (or equivalent SQLite tables); for presentation purposes
we group them into 5 functional data sources and 6 customer-facing categories.

## 5 Data Sources (logical grouping)

| # | Data source | MCP containers / tables backing it | Read by tools |
|---|---|---|---|
| 1 | **Customer & account records** | `customers`, `orders`, `security_logs` | `get_all_customers`, `get_customer_detail`, `get_customer_orders`, `get_security_logs`, `unlock_account` |
| 2 | **Billing & payments** | `invoices`, `payments` | `get_billing_summary`, `get_invoice_payments`, `pay_invoice` |
| 3 | **Subscriptions & usage** | `subscriptions`, `data_usage`, `service_incidents` | `get_subscription_detail`, `update_subscription`, `get_data_usage` |
| 4 | **Product catalog & promotions** | `products`, `promotions` | `get_products`, `get_product_detail`, `get_promotions`, `get_eligible_promotions` |
| 5 | **Support & knowledge** | `support_tickets`, `knowledge_documents` (vectorised) | `get_support_tickets`, `create_support_ticket`, `search_knowledge_base` |

**18 MCP tools** total across the 5 sources — see `mcp/mcp_service.py`.

## 6 Customer-Facing Categories

The slide shows six business-facing categories. The dataset
(`eval_dataset.json`) labels each case with one of seven internal `category`
values — the table below shows the mapping:

| Slide category | Dataset categories | Examples |
|---|---|---|
| Billing      | `billing` (6 cases)            | high invoice, payment history, autopay setup |
| Technical    | `internet` (7), `tv` (2)       | connectivity, outages, hardware issues |
| Account      | `account` (6)                  | logins, MFA, security unlocks |
| Plans        | `mobile` (4)                   | data caps, plan changes, family lines |
| Promotions   | `bundle` (3)                   | bundle deals, eligible offers |
| Escalation   | `support` (2)                  | ticket creation, escalation flows |

Total: **30 test cases** (25 single-turn + 5 multi-turn).

> **Why the mismatch?** Internal `category` values are scoped narrowly so each
> case maps to a single MCP domain expert. The slide groups them into the six
> functional buckets a customer-support org would recognise. If you prefer
> 1:1 alignment, you can either:
>
> - Update the slide to use the 7 internal categories, or
> - Add a `business_category` field to `eval_dataset.json` mirroring the
>   left column above.
