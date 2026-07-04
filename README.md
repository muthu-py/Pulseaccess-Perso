# PulseAccess

PulseAccess is a FastAPI-based backend built with a modular monolith architecture. It is designed to manage creators, communities, plans, subscriptions, and access control.

## Architecture Overview

The project follows a clean, modular monolith architecture with strong separation of concerns:
- **`app/core/`**: Configuration, logging, exception handling, and core cryptographic utilities (`SecurityService`).
- **`app/infrastructure/`**: Reusable infrastructure services (Database connections, JWT issuance, Session lifecycle, Email/SMTP, and external API stubs).
- **`app/modules/`**: Feature-specific modules (Auth, Community, Plan, Subscription, etc.) containing their own Models, Schemas, Repositories, Services, and Routers.

---

## Authentication Module

The authentication system uses a highly secure **Passwordless (OTP-based)** flow, utilizing JWT access tokens and HttpOnly refresh cookies. 

### Key Features
- **No Passwords**: Authentication is handled entirely via one-time passcodes sent via email.
- **Secure Token Management**: Short-lived Access Tokens (15 min) are returned in the JSON payload, while long-lived Refresh Tokens (30 days) are securely set in an HttpOnly, SameSite=Lax cookie to mitigate XSS attacks.
- **Database Session Tracking**: Active refresh tokens and OTP attempts are tracked in PostgreSQL. This allows for strict attempt limits and remote session revocation.
- **Cryptographic Hashing**: OTPs and Refresh Tokens are never stored in plain text. They are hashed using HMAC-SHA256 before being persisted to the database.
- **Privacy-First Design**: The `request-otp` endpoint always returns a generic success message to prevent account enumeration attacks.

### Auth Flow & Endpoints
1. **Register**: `POST /api/v1/auth/register`
   - Creates a new Creator account. Validates email and username uniqueness.
2. **Request OTP**: `POST /api/v1/auth/request-otp`
   - Invalidates any previous active OTPs, generates a new 6-digit code, stores its hash, and emails it to the user.
3. **Verify OTP**: `POST /api/v1/auth/verify-otp`
   - Validates the code (checks expiry, attempt limits, and hash match). Marks the OTP as used and issues an Access Token (JSON) and a Refresh Token (HttpOnly Cookie).
4. **Refresh**: `POST /api/v1/auth/refresh`
   - Reads the HttpOnly cookie, validates the hash against the database, revokes the old token, and issues a new Access/Refresh token pair (Token Rotation).
5. **Logout**: `POST /api/v1/auth/logout`
   - Revokes the active session in the database and clears the user's cookie.

---

## Local Development Setup

### 1. Requirements
- Python 3.12+
- PostgreSQL

### 2. Environment Variables
Ensure you have a `.env` file in the project root. Key variables include:
```env
# Database (Auto-converted to asyncpg internally)
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Security Secrets (Must be long, random strings)
JWT_SECRET_KEY=your_jwt_secret
OTP_HASH_SECRET=your_otp_hash_secret

# SMTP Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email
SMTP_PASSWORD=your_app_password
```

### 3. Installation
Install the required dependencies:
```bash
pip install -r requirements.txt
```

### 4. Database Migrations
Initialize the database tables using Alembic (uses the async engine):
```bash
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

### 5. Running the Server
Start the FastAPI application with Uvicorn:
```bash
uvicorn app.main:app --reload
```
Interactive API documentation (Swagger UI) is automatically generated and available at:
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
