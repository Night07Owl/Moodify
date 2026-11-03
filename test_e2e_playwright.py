import os
import sys
import time
import pymongo
import certifi
from dotenv import load_dotenv

if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def run_e2e_tests():
    from playwright.sync_api import sync_playwright

    load_dotenv('.env')

    mongo_uri = os.environ.get('MONGODB_URI', '').strip()
    mongo_name = os.environ.get('MONGODB_NAME', 'moodmusic_db').strip()

    print(f"Connecting to MongoDB Atlas database: '{mongo_name}'...")
    client = pymongo.MongoClient(mongo_uri, tlsCAFile=certifi.where())
    db = client[mongo_name]

    base_url = "http://127.0.0.1:8000"

    unique_id = str(int(time.time()))[-5:]
    test_username = f"verified_user_{unique_id}"
    test_email = f"user_{unique_id}@moodify.com"
    test_password = "SecurePassword123!"

    print("\n" + "="*65)
    print(f"STARTING PLAYWRIGHT FULL AUTOMATED E2E TEST SUITE")
    print(f"Testing User: {test_username} ({test_email})")
    print("="*65)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # --- TEST 1: SIGNUP VIA UI ---
        print("\n[STEP 1] Testing User Registration via Browser UI...")
        page.goto(f"{base_url}/signup/")
        page.wait_for_load_state("networkidle")
        assert "Sign up" in page.title(), f"Unexpected title: {page.title()}"

        page.fill('input[name="username"]', test_username)
        page.fill('input[name="email"]', test_email)
        page.fill('input[name="password"]', test_password)
        page.fill('input[name="confirm_password"]', test_password)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        time.sleep(2)
        user_in_mongo = db['users'].find_one({'username': test_username})
        assert user_in_mongo is not None, "FAILED: Registered user not found in MongoDB 'users' collection!"
        print(f"  ✓ User registered & confirmed in MongoDB 'users': {user_in_mongo.get('username')}")

        # Logout so we can test clean login
        print("\n[STEP 2] Logging out...")
        page.goto(f"{base_url}/logout/")
        page.wait_for_load_state("networkidle")

        # --- TEST 2: LOGIN VIA UI ---
        print(f"\n[STEP 3] Testing Login via Browser UI with '{test_username}'...")
        page.goto(f"{base_url}/login/")
        page.wait_for_load_state("networkidle")

        page.fill('input[name="username_or_email"]', test_username)
        page.fill('input[name="password"]', test_password)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        time.sleep(2)
        login_doc = db['login_history'].find_one({'username': test_username}, sort=[('timestamp', -1)])
        assert login_doc is not None, "FAILED: Login record not found in MongoDB 'login_history'!"
        print(f"  ✓ Login recorded in MongoDB 'login_history':")
        print(f"    - User:      {login_doc.get('username')}")
        print(f"    - Success:   {login_doc.get('success')}")
        print(f"    - IP:        {login_doc.get('ip_address')}")
        print(f"    - Details:   {login_doc.get('details')}")
        print(f"    - Timestamp: {login_doc.get('timestamp')}")

        # Check last_login and login_count update on users collection
        updated_user = db['users'].find_one({'username': test_username})
        assert updated_user.get('last_login') is not None, "FAILED: last_login was not set in MongoDB 'users'!"
        print(f"  ✓ User 'last_login' updated in MongoDB 'users': {updated_user.get('last_login')}")
        print(f"  ✓ User 'login_count' in MongoDB 'users': {updated_user.get('login_count')}")

        # --- TEST 3: AI ASSISTANT CHAT VIA UI ---
        print("\n[STEP 4] Testing AI Assistant Chat Widget via Browser UI...")
        page.goto(f"{base_url}/")
        page.wait_for_load_state("networkidle")

        # Open chat panel
        page.click('#chatLauncherBtn')
        page.wait_for_selector('#chatWindowPanel', state='visible')

        # Send test prompt regarding Error Code 488
        test_chat_msg = f"Explain error code 488 (Test run {unique_id})"
        print(f"  Sending message: '{test_chat_msg}'...")
        page.fill('#chatMessageInput', test_chat_msg)
        page.click('#chatSendBtn')

        print("  Waiting for AI bot response...")
        page.wait_for_selector('.chat-msg-row.bot:has-text("488")', timeout=20000)

        time.sleep(2)
        chat_doc = db['chat_logs'].find_one({'user_message': test_chat_msg})
        assert chat_doc is not None, "FAILED: Chat log not found in MongoDB 'chat_logs'!"
        print(f"  ✓ Chat successfully saved to MongoDB 'chat_logs':")
        print(f"    - User Query:  {chat_doc.get('user_message')}")
        print(f"    - Bot Summary: {chat_doc.get('bot_reply')[:90]}...")
        print(f"    - Error Code:  {chat_doc.get('error_code')}")
        print(f"    - Timestamp:   {chat_doc.get('timestamp')}")

        # --- TEST 4: SUBMIT SUPPORT TICKET VIA UI ---
        print("\n[STEP 5] Testing Support Ticket Submission via UI...")
        page.goto(f"{base_url}/support/")
        page.wait_for_load_state("networkidle")

        ticket_subject = f"Audio preview error on track 1 (Run {unique_id})"
        page.fill('input[name="user_name"]', 'Playwright Tester')
        page.fill('input[name="user_email"]', test_email)
        page.fill('input[name="subject"]', ticket_subject)
        page.select_option('select[name="category"]', 'Audio Playback Issue')
        page.select_option('select[name="priority"]', 'Medium')
        page.fill('textarea[name="description"]', 'This is an automated Playwright verification of ticket mirroring into MongoDB Atlas.')
        page.click('button:has-text("Submit Support Ticket")')
        page.wait_for_load_state("networkidle")

        time.sleep(2)
        ticket_doc = db['support_tickets'].find_one({'subject': ticket_subject})
        assert ticket_doc is not None, "FAILED: Ticket not found in MongoDB 'support_tickets'!"
        print(f"  ✓ Ticket mirrored to MongoDB 'support_tickets':")
        print(f"    - Ticket Number: {ticket_doc.get('ticket_number')}")
        print(f"    - Subject:       {ticket_doc.get('subject')}")
        print(f"    - Status:        {ticket_doc.get('status')}")
        print(f"    - Timestamp:     {ticket_doc.get('created_at')}")

        browser.close()

    print("\n" + "="*65)
    print("ALL PLAYWRIGHT TESTS PASSED 100%! VERIFIED IN LIVE MONGODB ATLAS!")
    print("="*65)


if __name__ == '__main__':
    run_e2e_tests()
