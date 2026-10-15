# Payment Tables Verification Report
**Date:** October 12, 2026  
**Status:** Analysis Complete

---

## EXECUTIVE SUMMARY

✅ **payment_events table EXISTS** in production database  
❌ **Table is MINIMAL** - Only 2 columns (id, payload)  
⚠️ **Schema INSUFFICIENT** for full payment microservice implementation  
📋 **Action Required:** Extended migration needed for production use

---

## CURRENT STATE - WHAT EXISTS

### Database Tables
```
✅ payment_events (ALREADY EXISTS)
   - id: UUID (Primary Key)
   - payload: VARCHAR (String)
```

**Location:** Created in `alembic/versions/fddb75def85e_initial.py`

**Created when:** Initial migration (July 2, 2026)

**Verification:**
```
Database: Supabase PostgreSQL
Table: payment_events
Rows: 0 (empty)
Columns: 2
```

### Code Files
```
✅ app/modules/payment/models.py
   └─ PaymentEvent model (minimal stub)

✅ app/modules/payment/routers.py
   └─ POST /api/v1/webhooks/razorpay (stub - returns "received")

✅ app/modules/payment/repositories.py
   └─ Empty (stub)

✅ app/modules/payment/services.py
   └─ Empty (stub)

✅ app/modules/payment/schemas.py
   └─ Empty (stub)
```

### Documentation
```
✅ README.md
   └─ Mentions: "payment/ - Razorpay webhook scaffold (stub)"
   └─ No detailed schema documentation
   └─ No payment_events table schema listed

✅ FEATURES_STATUS.md
   └─ Section 2.4: Payments (Razorpay) — stub
   └─ Lists all tasks to be done
   └─ Notes: "PaymentEvent stores only a raw payload string"
```

---

## WHAT'S MISSING FOR MICROSERVICE

### Database Tables Needed

**1. payment_orders** (NEW)
```sql
CREATE TABLE payment_orders (
    id UUID PRIMARY KEY,
    creator_id UUID NOT NULL FOREIGN KEY → creators.id,
    razorpay_order_id VARCHAR(50) UNIQUE,
    plan_id UUID NOT NULL FOREIGN KEY → plans.id,
    amount_paise INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'INR',
    status VARCHAR(50) DEFAULT 'pending',
    receipt_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE
);
```

**2. payment_webhooks** (NEW)
```sql
CREATE TABLE payment_webhooks (
    id UUID PRIMARY KEY,
    razorpay_event_id VARCHAR(100) UNIQUE,
    event_type VARCHAR(100),
    raw_payload JSONB,
    signature_valid BOOLEAN,
    processed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE
);
```

**3. payment_events** (EXISTING - NEEDS EXPANSION)
```sql
-- Current (minimal):
CREATE TABLE payment_events (
    id UUID PRIMARY KEY,
    payload VARCHAR NOT NULL
);

-- Required for microservice:
CREATE TABLE payment_events (
    id UUID PRIMARY KEY,
    idempotency_key VARCHAR(255) UNIQUE NOT NULL,  -- NEW
    razorpay_payment_id VARCHAR(50),                -- NEW
    razorpay_signature VARCHAR(255),                -- NEW
    event_type VARCHAR(50),                         -- NEW
    payload JSONB,                                  -- CHANGED: from VARCHAR
    status VARCHAR(50) DEFAULT 'pending',           -- NEW
    error_message TEXT,                             -- NEW
    retry_count INTEGER DEFAULT 0,                  -- NEW
    processed_at TIMESTAMP WITH TIME ZONE,          -- NEW
    created_at TIMESTAMP WITH TIME ZONE             -- NEW
);
```

---

## MIGRATION PATH

### Option A: Single Migration (Recommended)
Create one new migration that:
1. ✅ Alters existing `payment_events` table to add new columns
2. ✅ Creates `payment_orders` table
3. ✅ Creates `payment_webhooks` table

**File:** `alembic/versions/<timestamp>_extend_payment_schema.py`

```bash
# Generate migration
alembic revision --autogenerate -m "extend_payment_schema"

# Apply migration
alembic upgrade head
```

### Option B: Separate Migrations
Create 3 separate migrations (not recommended - harder to rollback)

---

## IMPLEMENTATION CHECKLIST

### Phase 1: Database Migration
- [ ] Create Alembic migration file
- [ ] Add payment_orders table schema
- [ ] Add payment_webhooks table schema  
- [ ] Alter payment_events table (add columns, change payload type)
- [ ] Add foreign key constraints
- [ ] Add indexes on frequently queried columns
- [ ] Test migration on staging database
- [ ] Apply migration to production

### Phase 2: Update Models
- [ ] Update PaymentEvent model in `app/modules/payment/models.py`
- [ ] Create PaymentOrder model
- [ ] Create PaymentWebhook model
- [ ] Add relationships between models
- [ ] Add table constraints and indexes

### Phase 3: Implement Services
- [ ] Implement RazorpayService (signature verification, API calls)
- [ ] Implement PaymentService (business logic)
- [ ] Implement PaymentRepository (database access)

### Phase 4: Update API Routes
- [ ] Implement POST /api/v1/orders
- [ ] Implement POST /api/v1/webhooks/razorpay
- [ ] Implement GET /api/v1/payments/{id}

### Phase 5: Integration
- [ ] Create payment event worker
- [ ] Wire to subscription creation
- [ ] Setup Redis/message queue
- [ ] Test end-to-end flow

---

## NOTES FOR IMPLEMENTATION

### Idempotency Key Strategy
```python
# When webhook arrives from Razorpay
idempotency_key = razorpay_event_id  # Unique per Razorpay event

# Check if already processed
existing = await db.query(PaymentEvent).filter(
    PaymentEvent.idempotency_key == idempotency_key
).first()

if existing:
    return {"status": "already_processed"}

# If not, create new event with idempotency key
new_event = PaymentEvent(
    idempotency_key=idempotency_key,
    razorpay_payment_id=payment_id,
    ...
)
```

### Status Transitions
```
Payment Status Flow:
pending → captured → (subscription creation) → completed
     → failed → (notification sent)
     → refunded → (revoke access)
```

### Payload Storage
- Change from VARCHAR to JSONB for better querying
- Store entire Razorpay webhook payload as JSON
- Allows filtering: `WHERE payload->>'event' = 'payment.captured'`

---

## VERIFICATION COMMANDS

### Check Table Schema
```sql
-- Connect to Supabase PostgreSQL
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'payment_events'
ORDER BY ordinal_position;
```

### Check if Data Exists
```sql
SELECT COUNT(*) FROM payment_events;
```

### Verify Migrations Applied
```sql
SELECT * FROM alembic_version;
```

---

## SUMMARY TABLE

| Item | Status | Location | Notes |
|------|--------|----------|-------|
| payment_events table | ✅ EXISTS | Database | Only 2 columns (id, payload) |
| payment_orders table | ❌ MISSING | Planned | Needed for order tracking |
| payment_webhooks table | ❌ MISSING | Planned | Needed for audit logging |
| PaymentEvent model | ✅ EXISTS | app/modules/payment/models.py | Needs extension |
| PaymentOrder model | ❌ MISSING | Planned | New model needed |
| PaymentWebhook model | ❌ MISSING | Planned | New model needed |
| Payment routes | ✅ EXISTS | app/modules/payment/routers.py | Stub only |
| Payment service | ✅ EXISTS | app/modules/payment/services.py | Empty (stub) |
| Payment repository | ✅ EXISTS | app/modules/payment/repositories.py | Empty (stub) |
| README documentation | ⚠️ PARTIAL | README.md | Lists module, not tables |
| FEATURES_STATUS.md | ✅ UPDATED | FEATURES_STATUS.md | References plan doc |

---

## CONCLUSION

**Starting Point:** ✅ Good - Basic table exists  
**Gap:** ⚠️ Schema is insufficient for production use  
**Action:** 📋 Create migration to extend schema with required columns and tables  
**Timeline:** 1 migration file + 5 hours of implementation  

The existing `payment_events` table is a good foundation. The next step is to:
1. Create extended migration
2. Add the two new tables
3. Extend payment_events with required columns
4. Implement microservice code using expanded schema
