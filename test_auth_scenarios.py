import httpx
import uuid
import asyncio
import re

BASE_URL = "http://localhost:8000/api/v1/auth"
DB_URL = "postgresql://postgres:muthupulseaccess@db.cqdakerdsanmyypcaqyt.supabase.co:5432/postgres"

# Let's generate a unique username and email for this test run
run_id = str(uuid.uuid4())[:8]
valid_username = f"testuser_{run_id}"
valid_email = f"test_{run_id}@example.com"
valid_name = "Test User"

results = []

def record(scenario, status_code, expected_status, passed, detail=""):
    mark = "PASS" if passed else "FAIL"
    results.append(f"{mark} | {scenario} | Expected: {expected_status}, Got: {status_code} | {detail}")

async def run_tests():
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # ==========================================
        # 1. REGISTER SCENARIOS
        # ==========================================
        # 1a. Fail: Username too short
        res = await client.post("/register", json={
            "name": valid_name,
            "username": "ab",
            "email": valid_email
        })
        record("Register - Username too short", res.status_code, 422, res.status_code == 422, res.text)

        # 1b. Fail: Invalid email
        res = await client.post("/register", json={
            "name": valid_name,
            "username": valid_username,
            "email": "not-an-email"
        })
        record("Register - Invalid email", res.status_code, 422, res.status_code == 422, res.text)

        # 1c. Success: Valid registration
        res = await client.post("/register", json={
            "name": valid_name,
            "username": valid_username,
            "email": valid_email
        })
        record("Register - Success", res.status_code, 201, res.status_code == 201, res.text)

        # 1d. Fail: Duplicate email
        res = await client.post("/register", json={
            "name": valid_name,
            "username": f"another_{run_id}",
            "email": valid_email
        })
        record("Register - Duplicate email", res.status_code, 409, res.status_code == 409, res.text)

        # 1e. Fail: Duplicate username
        res = await client.post("/register", json={
            "name": valid_name,
            "username": valid_username,
            "email": f"another_{run_id}@example.com"
        })
        record("Register - Duplicate username", res.status_code, 409, res.status_code == 409, res.text)


        # ==========================================
        # 2. REQUEST OTP SCENARIOS
        # ==========================================
        # 2a. Success (non-existent user, should return generic success)
        res = await client.post("/request-otp", json={
            "identifier": "nobody@example.com"
        })
        record("Request OTP - Non-existent user", res.status_code, 200, res.status_code == 200, res.text)

        # 2b. Success (valid user by email)
        res = await client.post("/request-otp", json={
            "identifier": valid_email
        })
        record("Request OTP - Valid user (email)", res.status_code, 200, res.status_code == 200, res.text)
        
        # 2c. Success (valid user by username)
        res = await client.post("/request-otp", json={
            "identifier": valid_username
        })
        record("Request OTP - Valid user (username)", res.status_code, 200, res.status_code == 200, res.text)


        # ==========================================
        # 3. VERIFY OTP SCENARIOS
        # ==========================================
        # Since the OTP is securely generated and hashed, we cannot easily retrieve it 
        # without querying the database directly. Let's do that using asyncpg.
        import asyncpg
        conn = await asyncpg.connect(DB_URL)
        
        # We need the active OTP hash, but it's hashed. Wait, the OTP was logged to the console
        # because the app is in APP_ENV=development.
        # But reading console output is hard from here. Let's create an OTP manually for testing
        # or use a fixed one by updating the DB.
        
        # We will generate an OTP, hash it, and insert it for our user.
        from app.core.security import SecurityService
        from app.core.config import get_settings
        settings = get_settings()
        sec = SecurityService(settings.OTP_HASH_SECRET)
        test_otp = "123456"
        test_otp_hash = sec.hash_value(test_otp)
        
        creator_row = await conn.fetchrow('SELECT id FROM creators WHERE email = $1', valid_email)
        creator_id = creator_row['id']
        
        # Invalidate existing OTPs and insert our test one
        await conn.execute('UPDATE login_otps SET used_at = now() WHERE creator_id = $1', creator_id)
        await conn.execute('''
            INSERT INTO login_otps (id, creator_id, otp_hash, purpose, attempts, expires_at, created_at)
            VALUES (gen_random_uuid(), $1, $2, 'login', 0, now() + interval '5 minutes', now())
        ''', creator_id, test_otp_hash)

        # 3a. Fail: Invalid OTP (wrong code)
        res = await client.post("/verify-otp", json={
            "identifier": valid_email,
            "otp_code": "000000"
        })
        record("Verify OTP - Invalid code", res.status_code, 401, res.status_code == 401, res.text)

        # 3b. Fail: Too many attempts
        for _ in range(4): # Make 4 more invalid attempts (5 total limit)
            await client.post("/verify-otp", json={"identifier": valid_email, "otp_code": "000000"})
        
        # 6th attempt should fail with rate limit (429)
        res = await client.post("/verify-otp", json={
            "identifier": valid_email,
            "otp_code": "000000"
        })
        record("Verify OTP - Attempt limit exceeded", res.status_code, 429, res.status_code == 429, res.text)

        # Let's insert a fresh OTP for the success test
        test_otp2 = "654321"
        test_otp2_hash = sec.hash_value(test_otp2)
        await conn.execute('UPDATE login_otps SET used_at = now() WHERE creator_id = $1', creator_id)
        await conn.execute('''
            INSERT INTO login_otps (id, creator_id, otp_hash, purpose, attempts, expires_at, created_at)
            VALUES (gen_random_uuid(), $1, $2, 'login', 0, now() + interval '5 minutes', now())
        ''', creator_id, test_otp2_hash)

        # 3c. Success: Valid OTP
        res = await client.post("/verify-otp", json={
            "identifier": valid_email,
            "otp_code": test_otp2
        })
        record("Verify OTP - Success", res.status_code, 200, res.status_code == 200, "Got token and cookie")
        access_token = res.json().get("data", {}).get("access_token")
        refresh_cookie = res.cookies.get("refresh_token")
        
        # 3d. Fail: OTP already used
        res = await client.post("/verify-otp", json={
            "identifier": valid_email,
            "otp_code": test_otp2
        })
        record("Verify OTP - Already used", res.status_code, 401, res.status_code == 401, res.text)

        # 3e. Fail: Expired OTP
        # Insert expired OTP
        test_otp3 = "111111"
        test_otp3_hash = sec.hash_value(test_otp3)
        await conn.execute('UPDATE login_otps SET used_at = now() WHERE creator_id = $1', creator_id)
        await conn.execute('''
            INSERT INTO login_otps (id, creator_id, otp_hash, purpose, attempts, expires_at, created_at)
            VALUES (gen_random_uuid(), $1, $2, 'login', 0, now() - interval '5 minutes', now())
        ''', creator_id, test_otp3_hash)
        res = await client.post("/verify-otp", json={
            "identifier": valid_email,
            "otp_code": test_otp3
        })
        record("Verify OTP - Expired", res.status_code, 401, res.status_code == 401, res.text)


        # ==========================================
        # 4. REFRESH SCENARIOS
        # ==========================================
        # 4a. Fail: No cookie
        res = await client.post("/refresh")
        record("Refresh - No cookie", res.status_code, 401, res.status_code == 401, res.text)

        # 4b. Fail: Invalid cookie
        res = await client.post("/refresh", cookies={"refresh_token": "invalid_jwt_token_format"})
        record("Refresh - Invalid cookie", res.status_code, 401, res.status_code == 401, res.text)

        # 4c. Success: Valid refresh cookie
        res = await client.post("/refresh", cookies={"refresh_token": refresh_cookie})
        record("Refresh - Success", res.status_code, 200, res.status_code == 200, "Got new tokens")
        new_refresh_cookie = res.cookies.get("refresh_token")

        # 4d. Fail: Revoked/Rotated cookie (using the old cookie)
        res = await client.post("/refresh", cookies={"refresh_token": refresh_cookie})
        record("Refresh - Old rotated cookie", res.status_code, 401, res.status_code == 401, res.text)


        # ==========================================
        # 5. LOGOUT SCENARIOS
        # ==========================================
        # 5a. Success: Without cookie (graceful)
        res = await client.post("/logout")
        record("Logout - No cookie", res.status_code, 200, res.status_code == 200, res.text)

        # 5b. Success: With valid cookie
        res = await client.post("/logout", cookies={"refresh_token": new_refresh_cookie})
        record("Logout - With valid cookie", res.status_code, 200, res.status_code == 200, "Cookie cleared")

        # Verify token is actually revoked by trying to refresh with it
        res = await client.post("/refresh", cookies={"refresh_token": new_refresh_cookie})
        record("Refresh - After logout", res.status_code, 401, res.status_code == 401, res.text)
        
        await conn.close()

if __name__ == "__main__":
    asyncio.run(run_tests())
    print("\n".join(results))
