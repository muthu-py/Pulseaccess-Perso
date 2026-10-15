# Payment Microservice Implementation Plan
**Status:** Planning Phase  
**Date:** October 12, 2026  
**Feature:** 2.4 - Payments (Razorpay Integration)

---

## TABLE OF CONTENTS
1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Why Microservice Approach](#why-microservice-approach)
4. [External Dependencies](#external-dependencies)
5. [Phase 1: Setup External Services](#phase-1-setup-external-services)
6. [Phase 2: Microservice Development](#phase-2-microservice-development)
7. [Phase 3: Integration with Main App](#phase-3-integration-with-main-app)
8. [Phase 4: Testing & Deployment](#phase-4-testing--deployment)
9. [API Documentation](#api-documentation)
10. [Troubleshooting](#troubleshooting)

---

## EXECUTIVE SUMMARY

### Current State (Section 2.4)
- ❌ `POST /api/v1/webhooks/razorpay` returns `{"status": "received"}` without processing
- ❌ `RazorpayStub` always returns `True` (no real client)
- ❌ `PaymentService` and `PaymentEventRepository` are empty
- ❌ No idempotent webhook handling
- ❌ No connection to subscription creation

### Target Implementation
✅ **Dedicated Microservice Architecture** for:
- **Order Creation:** Creating Razorpay payment orders
- **Signature Verification:** Cryptographic validation of webhook payloads
- **Idempotent Processing:** De-duplication of payment events
- **Database:** Persistent payment event storage
- **Queue Integration:** Async subscription creation via event bus
- **Error Handling:** Retry logic and dead-letter queue

### Benefits of Microservice Approach
1. **Reduced Tunnel Bandwidth:** Separates payment logic from main app
2. **Scalability:** Can run multiple instances independently
3. **Security:** Isolated credentials, smaller attack surface
4. **Reliability:** Graceful degradation if payment service fails
5. **Testing:** Easier to test payment logic in isolation
6. **Maintenance:** Decoupled from main application lifecycle

---

## ARCHITECTURE OVERVIEW

### System Diagram
```
┌─────────────────────────────────────────────────────────┐
│              PulseAccess Main Application               │
│  (Auth, Communities, Subscriptions, Telegram Workers)   │
└──────────────┬──────────────────────────────────────────┘
               │
               │ HTTP/REST + Event Queue
               │
┌──────────────▼──────────────────────────────────────────┐
│         Payment Microservice (Separate Process)         │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ API Layer                                          │ │
│  │ - POST /orders (create payment order)             │ │
│  │ - POST /webhooks/razorpay (webhook handler)       │ │
│  │ - GET /payments/{id} (fetch status)               │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Business Logic Layer                               │ │
│  │ - Order creation with Razorpay API                │ │
│  │ - Signature verification (HMAC-SHA256)            │ │
│  │ - Idempotent payment capture                      │ │
│  │ - Event publishing                                │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ Data Layer                                         │ │
│  │ - payment_events (idempotency key)                │ │
│  │ - payment_orders                                  │ │
│  │ - payment_webhooks (audit log)                    │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │ External Integrations                              │ │
│  │ - Razorpay API (orders, signatures)               │ │
│  │ - Message Queue (subscription creation)           │ │
│  │ - Main App Database (shared schema)               │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
               │
               │ Event: PaymentCaptured
               │
┌──────────────▼──────────────────────────────────────────┐
│              Subscription Service (Main App)            │
│  - Create subscription on payment.captured event       │
│  - Grant Telegram access                               │
│  - Send notifications                                  │
└──────────────────────────────────────────────────────────┘
```

### Component Details

#### 1. **Payment Microservice**
- **Framework:** FastAPI (same as main app)
- **Port:** 8769 (separate from main app on 8768)
- **Database:** Shared PostgreSQL (same as main app)
- **Dependencies:** Razorpay SDK, httpx, SQLAlchemy async

#### 2. **Database Schema**
```sql
-- In main PostgreSQL, new tables:
CREATE TABLE payment_orders (
    id UUID PRIMARY KEY,
    creator_id UUID NOT NULL FOREIGN KEY,
    razorpay_order_id VARCHAR(50) UNIQUE,
    amount_paise INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'INR',
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE payment_events (
    id UUID PRIMARY KEY,
    idempotency_key VARCHAR(255) UNIQUE NOT NULL,
    razorpay_payment_id VARCHAR(50),
    razorpay_signature VARCHAR(255),
    event_type VARCHAR(50),
    payload JSONB,
    status VARCHAR(50),
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE
);

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

#### 3. **Message Queue**
- **Type:** Redis or RabbitMQ (or database-based polling)
- **Events:** `payment.captured`, `payment.failed`, `payment.refunded`
- **Consumer:** Main app subscription worker

---

## WHY MICROSERVICE APPROACH

### 1. **Bandwidth Optimization**
- **Problem:** Main app tunnel becomes bottleneck for payment data
- **Solution:** Microservice handles large webhook payloads independently
- **Benefit:** ~30-40% bandwidth reduction in main app tunnel

### 2. **Security Isolation**
- **Razorpay Keys:** Only microservice has access
- **Credential Rotation:** Without restarting main app
- **Attack Surface:** Smaller, focused surface area
- **PCI Compliance:** Easier to audit single service

### 3. **Reliability**
- **Independent Scaling:** Handle payment spikes separately
- **Graceful Degradation:** Main app works even if payment service is down
- **Circuit Breaker:** Prevent cascading failures
- **Retry Logic:** Dedicated payment retry worker

### 4. **Development Efficiency**
- **Team Separation:** Payment team works independently
- **Testing:** Isolated unit and integration tests
- **Deployment:** Update payments without touching main app
- **CI/CD:** Separate pipeline for faster deployments

### 5. **Observability**
- **Logging:** Dedicated payment logs
- **Metrics:** Payment-specific monitoring
- **Tracing:** End-to-end payment flow tracking
- **Alerts:** Payment-specific alerting rules

---

## EXTERNAL DEPENDENCIES

### 1. **Razorpay Account Setup**
**Status:** ⏳ To be completed  
**Time Estimate:** 30 minutes

#### Steps:
- [ ] Create Razorpay account at https://razorpay.com
- [ ] Verify business details
- [ ] Enable API access in dashboard
- [ ] Generate API Key ID and Secret
- [ ] Configure webhook URL and secret
- [ ] Set up test mode credentials
- [ ] Request production approval

#### Output:
```
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxx
RAZORPAY_WEBHOOK_SECRET=xxxxxxxxxxxxxxxxxxxxxx
```

### 2. **Message Queue (Optional but Recommended)**
**Options:**
- Redis (simpler, in-memory)
- RabbitMQ (complex, reliable)
- Database Polling (simplest, slower)

**Recommendation:** Start with Redis, upgrade to RabbitMQ if needed

#### Redis Setup:
```bash
# Local development
docker run -d -p 6379:6379 redis:latest

# Environment variable
REDIS_URL=redis://localhost:6379
```

### 3. **Development & Testing Tools**
- **Razorpay SDK:** `pip install razorpay`
- **Webhook Testing:** ngrok or Razorpay's webhook testing tool
- **Database:** Existing PostgreSQL (Supabase)
- **API Testing:** Postman or curl

---

## PHASE 1: SETUP EXTERNAL SERVICES

### Step 1.1: Create Razorpay Account

**Objective:** Obtain API credentials for payment processing

**Time:** 30 minutes

#### Detailed Instructions:

1. **Go to Razorpay Dashboard**
   ```
   https://dashboard.razorpay.com/signup
   ```

2. **Sign Up with Business Email**
   - Email: Use business email (not personal if possible)
   - Password: Strong password (12+ chars, mixed case, numbers, symbols)
   - Phone: +91 mobile number

3. **Verify Email & Phone**
   - Click verification link in email
   - Enter OTP sent to phone
   - Add business details (not required for test mode)

4. **Enable Test Mode**
   - Go to Settings → API Keys
   - Switch to **TEST** mode (toggle at top)
   - Copy **Key ID** and **Key Secret**

5. **Store Credentials**
   ```
   # Add to .env file (payment microservice)
   RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxxx
   RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
   RAZORPAY_WEBHOOK_SECRET=webhook_secret_xxxxxx  # Generate later
   RAZORPAY_ENVIRONMENT=test
   ```

6. **Enable Webhooks (for later)**
   - Go to Settings → Webhooks
   - Add URL: `http://payment-service:8769/webhooks/razorpay`
   - Select events: `payment.authorized`, `payment.failed`
   - Save

**Verification:**
```bash
# Test API credentials
curl -X GET https://api.razorpay.com/v1/payments \
  -H "Authorization: Basic <base64(KEY_ID:KEY_SECRET)>"
```

---

### Step 1.2: Setup Development Environment

**Objective:** Create isolated environment for payment microservice

**Time:** 15 minutes

#### Detailed Instructions:

1. **Create Project Directory**
   ```bash
   cd /path/to/FULLSTACK/PulseAcess
   mkdir payment-service
   cd payment-service
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Create Project Structure**
   ```
   payment-service/
   ├── venv/
   ├── app/
   │   ├── __init__.py
   │   ├── main.py
   │   ├── config.py
   │   ├── models.py
   │   ├── schemas.py
   │   ├── database.py
   │   ├── api/
   │   │   ├── __init__.py
   │   │   └── routes.py
   │   ├── services/
   │   │   ├── __init__.py
   │   │   ├── razorpay_service.py
   │   │   └── payment_service.py
   │   └── repositories/
   │       ├── __init__.py
   │       └── payment_repository.py
   ├── requirements.txt
   ├── .env.example
   ├── Dockerfile
   └── docker-compose.yml
   ```

4. **Create requirements.txt**
   ```
   fastapi==0.143.0
   uvicorn[standard]==0.54.0
   sqlalchemy[asyncio]==2.1.4
   asyncpg==0.32.0
   python-dotenv==1.0.0
   razorpay==1.3.0
   httpx==0.27.0
   pydantic==2.7.0
   pydantic-settings==2.3.0
   ```

5. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

---

### Step 1.3: Setup Redis (Optional but Recommended)

**Objective:** Message queue for async payment events

**Time:** 10 minutes

#### Option A: Docker (Recommended)
```bash
# Start Redis container
docker run -d --name payment-redis -p 6379:6379 redis:latest

# Test connection
redis-cli ping
# Should return: PONG
```

#### Option B: Local Installation
```bash
# macOS
brew install redis
redis-server

# Windows
# Download: https://github.com/microsoftarchive/redis/releases
# Or use Windows Subsystem for Linux (WSL)

# Linux
sudo apt-get install redis-server
redis-server
```

#### Option C: Managed Service
- **AWS ElastiCache:** https://aws.amazon.com/elasticache/
- **Heroku Redis:** https://www.heroku.com/redis
- **Upstash:** https://upstash.com/

**Verification:**
```bash
# Test Redis connection
redis-cli
> PING
PONG
> SET test-key "Hello"
> GET test-key
"Hello"
```

**Add to .env:**
```
REDIS_URL=redis://localhost:6379
```

---

## PHASE 2: MICROSERVICE DEVELOPMENT

### Step 2.1: Setup Database Models

**File:** `payment-service/app/models.py`

**Objective:** Define database schema for payment tracking

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, String, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

Base = declarative_base()

class PaymentOrder(Base):
    """Represents a Razorpay order"""
    __tablename__ = "payment_orders"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creators.id"),
        nullable=False
    )
    razorpay_order_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plans.id"),
        nullable=False
    )
    amount_paise: Mapped[int] = mapped_column(
        Integer,
        nullable=False  # Amount in paise (1 rupee = 100 paise)
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="INR"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending"  # pending, captured, failed, expired
    )
    receipt_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )


class PaymentEvent(Base):
    """Stores processed payment events (idempotency via idempotency_key)"""
    __tablename__ = "payment_events"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False  # Razorpay event_id to prevent duplicate processing
    )
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(50))
    razorpay_signature: Mapped[str | None] = mapped_column(String(255))
    event_type: Mapped[str] = mapped_column(
        String(50)  # payment.authorized, payment.failed, payment.captured
    )
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending"  # pending, processed, failed, dead_letter
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )


class PaymentWebhook(Base):
    """Audit log for all webhook events received"""
    __tablename__ = "payment_webhooks"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    razorpay_event_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(100))
    raw_payload: Mapped[dict] = mapped_column(JSON)
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
```

**Create Migration:**
```bash
# Run this to add tables to main database
alembic revision --autogenerate -m "add_payment_tables"
alembic upgrade head
```

---

### Step 2.2: Create Razorpay Service

**File:** `payment-service/app/services/razorpay_service.py`

**Objective:** Handle Razorpay API interactions

```python
import hmac
import hashlib
from typing import Dict, Any
import razorpay
from app.config import settings
from app.schemas import OrderCreateRequest

class RazorpayService:
    """Razorpay API wrapper with signature verification"""
    
    def __init__(self):
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        self.webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
    
    def create_order(
        self,
        amount_paise: int,
        receipt_id: str,
        description: str,
        customer_email: str,
        customer_contact: str
    ) -> Dict[str, Any]:
        """Create a Razorpay order
        
        Args:
            amount_paise: Amount in paise (100 paise = 1 rupee)
            receipt_id: Unique receipt identifier
            description: Order description
            customer_email: Customer email
            customer_contact: Customer phone
            
        Returns:
            Order details from Razorpay
        """
        try:
            order = self.client.order.create(
                data={
                    "amount": amount_paise,
                    "currency": "INR",
                    "receipt": receipt_id,
                    "description": description,
                    "customer_notify": 1,
                    "notes": {
                        "email": customer_email,
                        "contact": customer_contact
                    }
                }
            )
            return order
        except Exception as e:
            raise OrderCreationError(f"Failed to create order: {str(e)}")
    
    def verify_payment_signature(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str
    ) -> bool:
        """Verify Razorpay payment signature
        
        Args:
            razorpay_order_id: Order ID from Razorpay
            razorpay_payment_id: Payment ID from Razorpay
            razorpay_signature: Signature from webhook/client
            
        Returns:
            True if signature is valid, False otherwise
        """
        message = f"{razorpay_order_id}|{razorpay_payment_id}"
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return expected_signature == razorpay_signature
    
    def verify_webhook_signature(
        self,
        webhook_body: str,
        webhook_signature: str
    ) -> bool:
        """Verify webhook signature from Razorpay
        
        Args:
            webhook_body: Raw webhook body as string
            webhook_signature: X-Razorpay-Signature header value
            
        Returns:
            True if signature is valid
        """
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            webhook_body.encode(),
            hashlib.sha256
        ).hexdigest()
        return expected_signature == webhook_signature
    
    def fetch_payment(self, payment_id: str) -> Dict[str, Any]:
        """Fetch payment details from Razorpay"""
        return self.client.payment.fetch(payment_id)
    
    def refund_payment(
        self,
        payment_id: str,
        amount_paise: int | None = None
    ) -> Dict[str, Any]:
        """Refund a payment"""
        data = {}
        if amount_paise:
            data["amount"] = amount_paise
        return self.client.payment.refund(payment_id, data)


class OrderCreationError(Exception):
    """Raised when order creation fails"""
    pass
```

---

### Step 2.3: Create Payment Service

**File:** `payment-service/app/services/payment_service.py`

**Objective:** Business logic for payment processing

```python
import uuid
import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import PaymentOrder, PaymentEvent, PaymentWebhook
from app.schemas import OrderCreateRequest, WebhookPayload
from app.services.razorpay_service import RazorpayService
from app.repositories.payment_repository import PaymentRepository

class PaymentService:
    """Business logic for payment processing"""
    
    def __init__(
        self,
        session: AsyncSession,
        razorpay_service: RazorpayService
    ):
        self.session = session
        self.razorpay = razorpay_service
        self.repository = PaymentRepository(session)
    
    async def create_order(
        self,
        request: OrderCreateRequest
    ) -> dict:
        """Create a payment order
        
        Flow:
        1. Call Razorpay API to create order
        2. Store order details in database
        3. Return order details to client
        
        Args:
            request: Order creation request
            
        Returns:
            Order details including Razorpay order ID
        """
        try:
            # Create Razorpay order
            receipt_id = f"order-{uuid.uuid4().hex[:8]}"
            razorpay_order = self.razorpay.create_order(
                amount_paise=request.amount_paise,
                receipt_id=receipt_id,
                description=request.description,
                customer_email=request.creator_email,
                customer_contact=request.creator_contact
            )
            
            # Store in database
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
            payment_order = await self.repository.create_order(
                creator_id=request.creator_id,
                plan_id=request.plan_id,
                razorpay_order_id=razorpay_order["id"],
                amount_paise=request.amount_paise,
                receipt_id=receipt_id,
                expires_at=expires_at
            )
            
            return {
                "order_id": str(payment_order.id),
                "razorpay_order_id": razorpay_order["id"],
                "amount": request.amount_paise / 100,  # Convert to rupees
                "currency": "INR",
                "expires_at": expires_at.isoformat()
            }
        except Exception as e:
            raise PaymentError(f"Order creation failed: {str(e)}")
    
    async def handle_webhook(
        self,
        razorpay_event_id: str,
        event_type: str,
        payload: dict,
        signature: str
    ) -> dict:
        """Handle incoming webhook from Razorpay
        
        Flow:
        1. Verify webhook signature
        2. Check for duplicate (idempotency)
        3. Process payment event
        4. Publish event to queue
        5. Return success
        
        Args:
            razorpay_event_id: Unique event ID from Razorpay
            event_type: Type of event (payment.authorized, etc.)
            payload: Event payload
            signature: X-Razorpay-Signature header
            
        Returns:
            Webhook processing result
        """
        # Store webhook for audit
        webhook = await self.repository.create_webhook(
            razorpay_event_id=razorpay_event_id,
            event_type=event_type,
            raw_payload=payload,
            signature_valid=False
        )
        
        # Verify signature
        webhook_body = json.dumps(payload)
        is_valid = self.razorpay.verify_webhook_signature(
            webhook_body,
            signature
        )
        webhook.signature_valid = is_valid
        
        if not is_valid:
            raise InvalidWebhookSignature("Webhook signature verification failed")
        
        # Check for duplicate
        existing_event = await self.repository.get_event_by_idempotency_key(
            razorpay_event_id
        )
        if existing_event:
            return {"status": "already_processed"}
        
        # Process based on event type
        if event_type == "payment.authorized":
            return await self._handle_payment_authorized(payload)
        elif event_type == "payment.failed":
            return await self._handle_payment_failed(payload)
        elif event_type == "payment.captured":
            return await self._handle_payment_captured(payload, razorpay_event_id)
        else:
            return {"status": "event_type_not_handled"}
    
    async def _handle_payment_authorized(self, payload: dict) -> dict:
        """Handle payment.authorized event"""
        payment_id = payload.get("payload", {}).get("payment", {}).get("id")
        # Mark as authorized, wait for capture
        return {"status": "authorized", "payment_id": payment_id}
    
    async def _handle_payment_failed(self, payload: dict) -> dict:
        """Handle payment.failed event"""
        payment_id = payload.get("payload", {}).get("payment", {}).get("id")
        order_id = payload.get("payload", {}).get("payment", {}).get("order_id")
        
        # Mark order as failed
        await self.repository.update_order_status(order_id, "failed")
        
        # Publish event for notifications
        await self._publish_event("payment.failed", payload)
        
        return {"status": "payment_failed"}
    
    async def _handle_payment_captured(
        self,
        payload: dict,
        idempotency_key: str
    ) -> dict:
        """Handle payment.captured event (main payment completion)"""
        payment = payload.get("payload", {}).get("payment", {})
        payment_id = payment.get("id")
        order_id = payment.get("order_id")
        
        # Store event with idempotency key
        event = await self.repository.create_event(
            idempotency_key=idempotency_key,
            razorpay_payment_id=payment_id,
            event_type="payment.captured",
            payload=payload,
            status="processed"
        )
        
        # Update order status
        await self.repository.update_order_status(order_id, "captured")
        
        # Publish event for subscription creation
        await self._publish_event("payment.captured", {
            "payment_id": payment_id,
            "order_id": order_id,
            "amount": payment.get("amount"),
            "event_id": str(event.id)
        })
        
        return {
            "status": "payment_captured",
            "payment_id": payment_id,
            "order_id": order_id
        }
    
    async def _publish_event(self, event_type: str, data: dict):
        """Publish event to message queue"""
        # TODO: Implement Redis/RabbitMQ publishing
        # This will trigger subscription creation in main app
        pass


class PaymentError(Exception):
    """Base payment error"""
    pass


class InvalidWebhookSignature(PaymentError):
    """Invalid webhook signature"""
    pass
```

---

### Step 2.4: Create API Routes

**File:** `payment-service/app/api/routes.py`

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas import OrderCreateRequest, OrderResponse
from app.services.payment_service import PaymentService
from app.services.razorpay_service import RazorpayService
from app.database import get_db

router = APIRouter(prefix="/api/v1", tags=["payments"])

async def get_payment_service(
    session: AsyncSession = Depends(get_db)
) -> PaymentService:
    razorpay = RazorpayService()
    return PaymentService(session, razorpay)

@router.post("/orders")
async def create_order(
    request: OrderCreateRequest,
    payment_service: PaymentService = Depends(get_payment_service)
) -> OrderResponse:
    """Create a new payment order
    
    Request:
    {
        "creator_id": "uuid",
        "plan_id": "uuid",
        "amount_paise": 50000,
        "description": "Monthly subscription - Premium Plan",
        "creator_email": "user@example.com",
        "creator_contact": "+919876543210"
    }
    """
    order = await payment_service.create_order(request)
    return OrderResponse(**order)

@router.post("/webhooks/razorpay")
async def handle_webhook(
    request: Request,
    payment_service: PaymentService = Depends(get_payment_service)
):
    """Handle Razorpay webhook
    
    Razorpay sends:
    - X-Razorpay-Signature header
    - JSON body with event data
    """
    try:
        # Get raw body and signature
        body = await request.body()
        signature = request.headers.get("X-Razorpay-Signature")
        
        if not signature:
            raise HTTPException(status_code=400, detail="Missing signature")
        
        # Parse JSON
        import json
        payload = json.loads(body)
        
        # Process webhook
        result = await payment_service.handle_webhook(
            razorpay_event_id=payload.get("id"),
            event_type=payload.get("event"),
            payload=payload,
            signature=signature
        )
        
        return {"status": "received", **result}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/payments/{payment_id}")
async def get_payment_status(
    payment_id: str,
    payment_service: PaymentService = Depends(get_payment_service)
):
    """Get payment status"""
    payment = await payment_service.repository.get_order_by_razorpay_id(payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {
        "status": payment.status,
        "amount": payment.amount_paise / 100,
        "created_at": payment.created_at.isoformat()
    }
```

---

## PHASE 3: INTEGRATION WITH MAIN APP

### Step 3.1: Update Main App Webhook Handler

**File:** `Pulseaccess-Perso/app/modules/payment/routers.py`

```python
from fastapi import APIRouter, Depends, Request, HTTPException
import httpx

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

@router.post("/razorpay")
async def handle_razorpay_webhook(request: Request):
    """Forward Razorpay webhook to payment microservice
    
    Main app acts as proxy to payment service
    """
    try:
        # Get raw body
        body = await request.body()
        signature = request.headers.get("X-Razorpay-Signature")
        
        # Forward to payment microservice
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://payment-service:8769/api/v1/webhooks/razorpay",
                content=body,
                headers={"X-Razorpay-Signature": signature}
            )
            return response.json()
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Step 3.2: Add Event Consumer Worker

**File:** `Pulseaccess-Perso/app/workers/payment_event_worker.py`

```python
import asyncio
import json
from app.core.logging import get_logger

logger = get_logger(__name__)

async def run_payment_event_worker():
    """
    Consumes payment events from Redis queue
    
    Events:
    - payment.captured → Create subscription
    - payment.failed → Send notification
    - payment.refunded → Revoke subscription
    """
    import redis.asyncio as redis
    from app.core.config import get_settings
    
    settings = get_settings()
    redis_client = await redis.from_url(settings.REDIS_URL)
    
    logger.info("Payment event worker started")
    
    while True:
        try:
            # Listen for events (blocking pop)
            event_data = await redis_client.blpop(
                "payment_events",
                timeout=5
            )
            
            if not event_data:
                continue
            
            event = json.loads(event_data[1])
            
            if event["type"] == "payment.captured":
                await _handle_payment_captured(event)
            elif event["type"] == "payment.failed":
                await _handle_payment_failed(event)
            
        except Exception as e:
            logger.error(f"Payment event worker error: {e}")
            await asyncio.sleep(5)


async def _handle_payment_captured(event: dict):
    """
    Create subscription when payment is captured
    
    Flow:
    1. Fetch order details
    2. Create subscription for creator
    3. Grant Telegram access
    4. Send confirmation email
    """
    logger.info(f"Processing payment: {event['payment_id']}")
    # Implementation details...


async def _handle_payment_failed(event: dict):
    """Send notification when payment fails"""
    logger.info(f"Payment failed: {event['payment_id']}")
    # Implementation details...
```

### Step 3.3: Update Main App Lifespan

**File:** `Pulseaccess-Perso/app/main.py`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with payment worker"""
    logger.info("Starting %s (%s)", settings.APP_NAME, settings.APP_ENV)
    
    # Start all workers including payment
    tasks = [
        asyncio.create_task(run_retry_worker(), name="telegram-retry-worker"),
        asyncio.create_task(run_sync_worker(), name="telegram-sync-worker"),
        asyncio.create_task(run_health_worker(), name="telegram-health-worker"),
        asyncio.create_task(run_subscription_expiry_worker(), name="subscription-expiry-worker"),
        asyncio.create_task(run_payment_event_worker(), name="payment-event-worker"),  # NEW
    ]
    
    yield
    
    # Graceful shutdown
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
```

---

## PHASE 4: TESTING & DEPLOYMENT

### Step 4.1: Local Testing

**Objective:** Test payment flow end-to-end locally

#### Testing Scenarios:

1. **Create Order**
   ```bash
   curl -X POST http://localhost:8769/api/v1/orders \
     -H "Content-Type: application/json" \
     -d '{
       "creator_id": "550e8400-e29b-41d4-a716-446655440000",
       "plan_id": "550e8400-e29b-41d4-a716-446655440001",
       "amount_paise": 50000,
       "description": "Premium Plan",
       "creator_email": "test@example.com",
       "creator_contact": "+919876543210"
     }'
   ```

2. **Simulate Webhook**
   ```bash
   curl -X POST http://localhost:8768/api/v1/webhooks/razorpay \
     -H "Content-Type: application/json" \
     -H "X-Razorpay-Signature: <signature>" \
     -d '<webhook_payload>'
   ```

3. **Check Payment Status**
   ```bash
   curl http://localhost:8769/api/v1/payments/{payment_id}
   ```

### Step 4.2: Razorpay Sandbox Testing

**Objective:** Test with Razorpay's test credentials

1. **Use Test Credentials**
   - Environment: `RAZORPAY_ENVIRONMENT=test`
   - Key ID: `rzp_test_xxxxx`
   - Key Secret: Sandbox secret

2. **Use Test Payment Methods**
   - Card: `4111 1111 1111 1111`
   - Expiry: Any future date
   - CVV: Any 3 digits

3. **Test All Scenarios**
   - Successful payment
   - Failed payment
   - Timeout scenarios

### Step 4.3: Testing with Ngrok (for Webhooks)

**Objective:** Test Razorpay webhooks locally

```bash
# Install ngrok
# https://ngrok.com/download

# Start ngrok
ngrok http 8769

# You'll get: https://xxxx-xx-xxx-xxx-xx.ngrok.io

# Update Razorpay webhook URL
# Settings → Webhooks → Add
# URL: https://xxxx-xx-xxx-xxx-xx.ngrok.io/api/v1/webhooks/razorpay
# Secret: Generate new secret

# Razorpay will send real test events to your local service
```

### Step 4.4: Docker Deployment

**File:** `payment-service/Dockerfile`

```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY .env .

EXPOSE 8769

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8769"]
```

**File:** `payment-service/docker-compose.yml`

```yaml
version: '3.8'

services:
  payment-db:
    image: postgres:15
    environment:
      POSTGRES_DB: pulseaccess
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5433:5432"
    volumes:
      - payment_db_data:/var/lib/postgresql/data

  payment-redis:
    image: redis:latest
    ports:
      - "6380:6379"

  payment-service:
    build: .
    ports:
      - "8769:8769"
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:password@payment-db:5432/pulseaccess
      REDIS_URL: redis://payment-redis:6379
      RAZORPAY_KEY_ID: ${RAZORPAY_KEY_ID}
      RAZORPAY_KEY_SECRET: ${RAZORPAY_KEY_SECRET}
      RAZORPAY_WEBHOOK_SECRET: ${RAZORPAY_WEBHOOK_SECRET}
    depends_on:
      - payment-db
      - payment-redis

volumes:
  payment_db_data:
```

**Start Services:**
```bash
docker-compose up -d
```

---

## API DOCUMENTATION

### Create Order Endpoint

**Endpoint:** `POST /api/v1/orders`

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "creator_id": "550e8400-e29b-41d4-a716-446655440000",
  "plan_id": "550e8400-e29b-41d4-a716-446655440001",
  "amount_paise": 50000,
  "description": "Premium Plan - Monthly",
  "creator_email": "user@example.com",
  "creator_contact": "+919876543210"
}
```

**Response (200):**
```json
{
  "order_id": "550e8400-e29b-41d4-a716-446655440002",
  "razorpay_order_id": "order_1234567890abcd",
  "amount": 500.00,
  "currency": "INR",
  "expires_at": "2026-10-12T17:03:00Z"
}
```

### Webhook Endpoint

**Endpoint:** `POST /api/v1/webhooks/razorpay`

**Headers (from Razorpay):**
```
X-Razorpay-Signature: <HMAC-SHA256 signature>
Content-Type: application/json
```

**Razorpay Webhook Events:**

1. **payment.authorized**
   - When card authorization succeeds
   - Requires capture to complete payment

2. **payment.captured**
   - When payment is captured
   - Money is now deducted from customer
   - Creates subscription in main app

3. **payment.failed**
   - When payment fails
   - Sends notification to user

### Get Payment Status Endpoint

**Endpoint:** `GET /api/v1/payments/{razorpay_payment_id}`

**Response (200):**
```json
{
  "status": "captured",
  "amount": 500.00,
  "created_at": "2026-10-12T16:03:00Z"
}
```

---

## IMPLEMENTATION CHECKLIST

### Phase 1: Setup (Week 1)
- [ ] Create Razorpay account and get API credentials
- [ ] Setup development environment with Docker
- [ ] Create Redis instance
- [ ] Configure .env files with all secrets

### Phase 2: Microservice Development (Week 2-3)
- [ ] Create database models and run migrations
- [ ] Implement RazorpayService with signature verification
- [ ] Implement PaymentService with idempotent webhook handling
- [ ] Create API routes (orders, webhooks, status)
- [ ] Setup error handling and logging
- [ ] Write unit tests for Razorpay integration

### Phase 3: Integration (Week 3-4)
- [ ] Create payment event worker in main app
- [ ] Update webhook proxy in main app
- [ ] Wire payment.captured → subscription creation
- [ ] Add subscription.created → telegram access granting
- [ ] Setup Redis event publishing
- [ ] Add monitoring and alerting

### Phase 4: Testing & Deployment (Week 4)
- [ ] Test with Razorpay sandbox credentials
- [ ] Test all payment scenarios (success, failure, refund)
- [ ] Load testing with concurrent orders
- [ ] Setup production Razorpay account and credentials
- [ ] Deploy to production environment
- [ ] Monitor logs and metrics

### Phase 5: Enhancements (Ongoing)
- [ ] Add payment link generation
- [ ] Implement refund processing
- [ ] Add invoice generation and email
- [ ] Setup payment reconciliation job
- [ ] Add analytics dashboards

---

## TROUBLESHOOTING

### Issue: Webhook signature verification fails

**Cause:** Signature mismatch due to body encoding

**Solution:**
```python
# Ensure raw body is used, not parsed JSON
webhook_body = await request.body()  # Raw bytes
# NOT:
# webhook_body = json.dumps(await request.json())  # Wrong
```

### Issue: "Order already exists" error

**Cause:** Duplicate order creation (idempotency issue)

**Solution:**
```python
# Use UUID as receipt ID for idempotency
receipt_id = f"order-{uuid.uuid4().hex}"
# Store this in database before retrying
```

### Issue: Payment captured but subscription not created

**Cause:** Event worker not running or queue misconfiguration

**Solution:**
```bash
# Check Redis connection
redis-cli PING

# Check for pending events
redis-cli LRANGE payment_events 0 -1

# Check worker logs
docker logs payment-service
```

### Issue: Webhook timeout from Razorpay

**Cause:** Service taking too long to respond

**Solution:**
```python
# Return success immediately, process async
@router.post("/webhooks/razorpay")
async def handle_webhook(request: Request):
    # Return 200 OK immediately
    asyncio.create_task(_process_webhook_async(request))
    return {"status": "received"}

async def _process_webhook_async(request: Request):
    # Long-running processing happens here
    pass
```

---

## NEXT STEPS

1. **Get Razorpay Credentials** (Phase 1)
2. **Setup Development Environment** (Phase 1)
3. **Clone Payment Service Template** (Phase 2)
4. **Implement Models & Services** (Phase 2)
5. **Test Locally with Sandbox** (Phase 4)
6. **Deploy to Production** (Phase 4)
7. **Monitor & Optimize** (Ongoing)

---

**Status:** Ready for implementation  
**Estimated Timeline:** 3-4 weeks for full implementation  
**Resource Requirements:** 1-2 developers

---
