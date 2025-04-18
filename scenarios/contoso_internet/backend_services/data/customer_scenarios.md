# Customer Scenarios –  Answer Key Included

## Scenario 1: Invoice Higher Than Usual
- **Customer ID**: 251
- **Name**       : John Doe
- **Email**      : scenario1@example.com
- **Phone**      : 555‑0001
- **Address**    : 123 Main St, City
- **Loyalty**    : Silver

### Challenge
Latest invoice shows $150, 2.5× the usual amount.

### How the AI agent should solve
1. SELECT last 6 invoices → detect $150 outlier (std‑dev or >50 % above mean).  
2. Cross‑check DataUsage for same billing cycle → find ~22 GB vs plan’s 10 GB cap.  
3. Quote **Data Overage Policy – “may retroactively upgrade within 15 days”**.  
4. Offer: (a) file invoice‑adjustment; (b) upgrade plan & credit overage pro‑rata.  
5. Note that $50 already paid; $100 balance remains.

---

## Scenario 2: Internet Slower Than Before
- **Customer ID**: 252
- **Name**       : Jane Doe
- **Email**      : scenario2@example.com
- **Phone**      : 555‑0002
- **Address**    : 234 Elm St, Town
- **Loyalty**    : Gold

### Challenge
Throughput much lower than advertised 1 Gbps tier.

### How the AI agent should solve
1. Confirm Subscriptions.service_status = 'slow'.  
2. Query ServiceIncidents – open ticket still 'investigating'.  
3. Use KB: **Troubleshooting Slow Internet – Basic Steps**.  
4. Ask customer to run speed‑test, reboot; escalate if still <25 % of tier.

---

## Scenario 3: Travelling Abroad – Needs Roaming
- **Customer ID**: 253
- **Name**       : Mark Doe
- **Email**      : scenario3@example.com
- **Phone**      : 555‑0003
- **Address**    : 345 Oak St, Village
- **Loyalty**    : Bronze

### Challenge
Leaving for Spain in 2 days, unsure how to enable roaming.

### How the AI agent should solve
1. Subscriptions.roaming_enabled = 0 → verify not active.  
2. Check product offerings → suggest 'International Roaming' add‑on.  
3. Quote **International Roaming Options Explained**: must activate ≥3 days ahead.  
4. Offer immediate activation with pro‑rated charges.

---

## Scenario 4: Account Locked
- **Customer ID**: 254
- **Name**       : Alice Doe
- **Email**      : scenario4@example.com
- **Phone**      : 555‑0004
- **Address**    : 456 Pine St, Hamlet
- **Loyalty**    : Gold

### Challenge
Cannot log in; system says account locked.

### How the AI agent should solve
1. SELECT * FROM SecurityLogs WHERE customer_id = ? ORDER BY event_timestamp DESC.  
2. Detect 'account_locked' record 12 min ago.  
3. Follow **Account Unlock Procedure – Verification Steps**:   
   • send 2FA code, verify identity, force password reset.

---

## Scenario 5: Promotion / Discount Eligibility
- **Customer ID**: 255
- **Name**       : Ron Doe
- **Email**      : scenario5@example.com
- **Phone**      : 555‑0005
- **Address**    : 567 Maple St, Metropolis
- **Loyalty**    : Gold

### Challenge
Wants to know what promos he qualifies for.

### How the AI agent should solve
1. Look up Promotions where eligibility_criteria matches loyalty_level = 'Gold'  
   AND current_date between start_date/end_date.  
2. Return 'Mobile Loyalty Discount' (10%).  
3. Summer2025 Teaser Promo is FUTURE – explain not yet active per KB   
   **Promotion Eligibility Guidelines**.

---

## Scenario 6: Product Return Within Window
- **Customer ID**: 256
- **Name**       : Mary Doe
- **Email**      : scenario6@example.com
- **Phone**      : 555‑0006
- **Address**    : 678 Birch St, Capital
- **Loyalty**    : Silver

### Challenge
Returned a handset, waiting for refund.

### How the AI agent should solve
1. Verify Orders.order_status = 'returned' and order_date is 25 days ago < 30‑day window.  
2. Cite **Return Policy and Process**: 7‑10 business days for refund.  
3. If >10 days passed, escalate to fulfilment.

---

## Scenario 7: Frequent Dropped Calls
- **Customer ID**: 257
- **Name**       : Tom Smith
- **Email**      : scenario7@example.com
- **Phone**      : 555‑0007
- **Address**    : 789 Cedar St, Hill
- **Loyalty**    : Silver

### Challenge
Calls drop whenever downtown.

### How the AI agent should solve
1. Review open SupportTickets (category 'call_drop') – capture 3 sample times/locations.  
2. Follow KB **Dropped Call Investigation Workflow**: escalate to RF engineering.  
3. If systemic issue confirmed, apply credit per **Service Reliability SLA – Credit Matrix**.

---

## Scenario 8: Overdue Invoice – Service Suspended
- **Customer ID**: 258
- **Name**       : Sara Lee
- **Email**      : scenario8@example.com
- **Phone**      : 555‑0008
- **Address**    : 123 Ocean Blvd, Bay City
- **Loyalty**    : Gold

### Challenge
Service suspended due to missed payment; wants late fee waived.

### How the AI agent should solve
1. Invoice unpaid >14 days; Payments show 2 failed attempts → beyond 10‑day grace.  
2. Account status = 'inactive' (suspended).  
3. Reference **Payment Failure & Reinstatement Rules** for reconnection fee  
   and first‑time waiver eligibility + **Late Payment Fee Policy**.  
4. Offer hardship plan per **Financial Hardship Payment Plan Procedure**.

---

## Scenario 9: Mobile Data Overage Charge
- **Customer ID**: 259
- **Name**       : Alex Brown
- **Email**      : scenario9@example.com
- **Phone**      : 555‑0009
- **Address**    : 321 Spruce Ln, Forest
- **Loyalty**    : Bronze

### Challenge
Received $150 bill due to data overage.

### How the AI agent should solve
1. DataUsage sum for billing cycle ≈22 GB vs 10 GB cap → 12 GB over.  
2. Quote **Data Overage Policy**: can switch to higher tier retroactively  
   within 15 days of invoice; overage will be re‑rated.  
3. Upsell larger plan or unlimited bundle.

---

