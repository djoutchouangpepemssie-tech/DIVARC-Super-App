#!/usr/bin/env python3
"""
PHASE 11: AI Assistant DIVA - Execute Action Tests
Tests the execute functionality by manually inserting actions into the database
"""
import requests
import json
from pymongo import MongoClient
from uuid import uuid4
from datetime import datetime

BASE_URL = "https://divarc-hub.preview.emergentagent.com/api"
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "your_database_name"

def test_execute_actions():
    """Test execute functionality with manually created actions"""
    
    print("\n" + "="*80)
    print("PHASE 11: AI ASSISTANT DIVA - EXECUTE ACTION TESTS")
    print("="*80)
    
    # Connect to MongoDB
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Fresh user for testing
    email = "diva11-exec@divarc.fr"
    
    # ========== AUTH FLOW ==========
    print("\n[AUTH] Setting up fresh user...")
    
    # Send OTP
    r = requests.post(f"{BASE_URL}/auth/otp/send", json={"email": email})
    assert r.status_code == 200, f"OTP send failed: {r.status_code} {r.text}"
    data = r.json()
    preview_code = data.get("previewCode")
    print(f"✓ OTP sent, previewCode: {preview_code}")
    
    # Verify OTP
    r = requests.post(f"{BASE_URL}/auth/otp/verify", json={"email": email, "code": preview_code})
    assert r.status_code == 200, f"OTP verify failed: {r.status_code} {r.text}"
    data = r.json()
    token = data.get("token")
    user = data.get("user")
    user_id = user.get("id")
    print(f"✓ Authenticated as {user.get('name')} ({user.get('handle')}), userId={user_id}")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get wallet balance before tests
    r = requests.get(f"{BASE_URL}/wallet", headers=headers)
    assert r.status_code == 200, f"Wallet fetch failed: {r.status_code}"
    balance_before = r.json().get("balanceCents")
    print(f"✓ Initial wallet balance: {balance_before}c ({balance_before/100:.2f}€)")
    
    # Get contacts
    r = requests.get(f"{BASE_URL}/contacts", headers=headers)
    assert r.status_code == 200, f"Contacts fetch failed: {r.status_code}"
    contacts = r.json()
    contact = contacts[0]
    contact_name = contact.get("name")
    print(f"✓ Found contact: {contact_name} ({contact.get('handle')})")
    
    session_id = str(uuid4())
    print(f"✓ Using sessionId: {session_id}")
    
    # ========== TEST 1: Execute send_money action ==========
    print("\n[TEST 1] Execute send_money action (manually created)")
    
    try:
        # Create a message with send_money action in the database
        action_id = str(uuid4())
        user_msg = {
            "id": str(uuid4()),
            "userId": user_id,
            "sessionId": session_id,
            "role": "user",
            "content": f"Envoie 20 euros à {contact_name}",
            "createdAt": datetime.utcnow()
        }
        
        ai_msg = {
            "id": str(uuid4()),
            "userId": user_id,
            "sessionId": session_id,
            "role": "assistant",
            "content": f"D'accord, je prépare l'envoi de 20€ à {contact_name}.",
            "actions": [{
                "id": action_id,
                "type": "send_money",
                "title": f"Envoyer 20€ à {contact_name}",
                "summary": f"Transfert de 20.00€ vers {contact_name}",
                "payload": {
                    "toName": contact_name,
                    "amountCents": 2000,
                    "message": "Test via DIVA"
                },
                "risk": "high",
                "status": "pending"
            }],
            "createdAt": datetime.utcnow()
        }
        
        db.ai_messages.insert_many([user_msg, ai_msg])
        print(f"✓ Created AI message with send_money action (id={action_id})")
        
        # Execute the action
        r = requests.post(f"{BASE_URL}/ai/actions/{action_id}/execute",
                         headers=headers,
                         json={"sessionId": session_id})
        assert r.status_code == 200, f"Execute failed: {r.status_code} {r.text}"
        data = r.json()
        
        assert data.get("ok") == True, "Execute response ok is not True"
        result = data.get("result", {})
        
        assert result.get("kind") == "send_money", f"Result kind is {result.get('kind')}, expected 'send_money'"
        assert result.get("amountCents") == 2000, f"Result amountCents is {result.get('amountCents')}, expected 2000"
        assert result.get("to"), "Result has no 'to' field"
        balance_after = result.get("balanceCents")
        print(f"✓ send_money executed: amountCents=2000, to={result.get('to')}, balanceCents={balance_after}")
        
        # Verify wallet decreased
        expected_balance = balance_before - 2000
        assert balance_after == expected_balance, \
            f"Wallet balance is {balance_after}c, expected {expected_balance}c"
        print(f"✓ Wallet decreased correctly: {balance_before}c -> {balance_after}c (-2000c)")
        
        # Verify P2P transaction created
        r = requests.get(f"{BASE_URL}/transactions", headers=headers)
        assert r.status_code == 200, f"Transactions fetch failed: {r.status_code}"
        transactions = r.json()  # Returns array directly
        
        p2p_tx = next((tx for tx in transactions if "via DIVA" in tx.get("label", "")), None)
        assert p2p_tx, "No P2P transaction with 'via DIVA' label found"
        assert p2p_tx.get("category") == "P2P", f"Transaction category is {p2p_tx.get('category')}"
        assert p2p_tx.get("amountCents") == -2000, f"Transaction amount is {p2p_tx.get('amountCents')}"
        print(f"✓ P2P transaction created: label='{p2p_tx.get('label')}', category=P2P, amount=-2000c")
        
        print("✅ TEST 1 PASSED: send_money executed successfully")
        
        # Test idempotency
        print("\n[TEST 1b] Execute same action again - should return 409")
        r = requests.post(f"{BASE_URL}/ai/actions/{action_id}/execute",
                         headers=headers,
                         json={"sessionId": session_id})
        assert r.status_code == 409, f"Expected 409, got {r.status_code}"
        print(f"✓ Second execution returned 409 (already executed)")
        
        # Verify wallet didn't change
        r = requests.get(f"{BASE_URL}/wallet", headers=headers)
        balance_check = r.json().get("balanceCents")
        assert balance_check == balance_after, f"Wallet changed: {balance_after}c -> {balance_check}c"
        print(f"✓ Wallet unchanged: {balance_check}c")
        
        print("✅ TEST 1b PASSED: Idempotency verified (409 on re-execution)")
        
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        raise
    
    # ========== TEST 2: Execute create_listing action ==========
    print("\n[TEST 2] Execute create_listing action (manually created)")
    
    try:
        action_id = str(uuid4())
        ai_msg = {
            "id": str(uuid4()),
            "userId": user_id,
            "sessionId": session_id,
            "role": "assistant",
            "content": "Je crée ton annonce pour le vélo.",
            "actions": [{
                "id": action_id,
                "type": "create_listing",
                "title": "Créer annonce vélo",
                "summary": "Vélo à vendre 150€ à Lyon",
                "payload": {
                    "title": "Vélo de ville en excellent état",
                    "priceCents": 15000,
                    "category": "loisirs",
                    "description": "Vélo de ville, très bon état, peu utilisé",
                    "city": "Lyon"
                },
                "risk": "medium",
                "status": "pending"
            }],
            "createdAt": datetime.utcnow()
        }
        
        db.ai_messages.insert_one(ai_msg)
        print(f"✓ Created AI message with create_listing action (id={action_id})")
        
        # Execute the action
        r = requests.post(f"{BASE_URL}/ai/actions/{action_id}/execute",
                         headers=headers,
                         json={"sessionId": session_id})
        assert r.status_code == 200, f"Execute failed: {r.status_code} {r.text}"
        data = r.json()
        
        result = data.get("result", {})
        assert result.get("kind") == "create_listing", f"Result kind is {result.get('kind')}"
        listing_id = result.get("listingId")
        assert listing_id, "No listingId in result"
        print(f"✓ create_listing executed: listingId={listing_id}, title={result.get('title')}")
        
        # Verify listing exists
        r = requests.get(f"{BASE_URL}/market/listings", headers=headers)
        assert r.status_code == 200, f"Listings fetch failed: {r.status_code}"
        listings = r.json()  # Returns array directly
        
        created_listing = next((l for l in listings if l.get("id") == listing_id), None)
        assert created_listing, f"Listing {listing_id} not found"
        assert created_listing.get("priceCents") == 15000, f"Price is {created_listing.get('priceCents')}"
        print(f"✓ Listing found: title='{created_listing.get('title')}', priceCents=15000")
        
        print("✅ TEST 2 PASSED: create_listing executed successfully")
        
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        raise
    
    # ========== TEST 3: Execute launch_ad action ==========
    print("\n[TEST 3] Execute launch_ad action (manually created)")
    
    try:
        # Get balance before
        r = requests.get(f"{BASE_URL}/wallet", headers=headers)
        balance_before_ad = r.json().get("balanceCents")
        print(f"✓ Wallet balance before ad: {balance_before_ad}c")
        
        action_id = str(uuid4())
        ai_msg = {
            "id": str(uuid4()),
            "userId": user_id,
            "sessionId": session_id,
            "role": "assistant",
            "content": "Je lance ta campagne de notoriété.",
            "actions": [{
                "id": action_id,
                "type": "launch_ad",
                "title": "Lancer campagne pub",
                "summary": "Campagne de notoriété 50€",
                "payload": {
                    "name": "Campagne Test DIVA",
                    "type": "display",
                    "objective": "awareness",
                    "budgetCents": 5000
                },
                "risk": "high",
                "status": "pending"
            }],
            "createdAt": datetime.utcnow()
        }
        
        db.ai_messages.insert_one(ai_msg)
        print(f"✓ Created AI message with launch_ad action (id={action_id})")
        
        # Execute the action
        r = requests.post(f"{BASE_URL}/ai/actions/{action_id}/execute",
                         headers=headers,
                         json={"sessionId": session_id})
        assert r.status_code == 200, f"Execute failed: {r.status_code} {r.text}"
        data = r.json()
        
        result = data.get("result", {})
        assert result.get("kind") == "launch_ad", f"Result kind is {result.get('kind')}"
        campaign_id = result.get("campaignId")
        assert campaign_id, "No campaignId in result"
        balance_after_ad = result.get("balanceCents")
        print(f"✓ launch_ad executed: campaignId={campaign_id}, balanceCents={balance_after_ad}")
        
        # Verify wallet debited
        expected_balance = balance_before_ad - 5000
        assert balance_after_ad == expected_balance, \
            f"Wallet is {balance_after_ad}c, expected {expected_balance}c"
        print(f"✓ Wallet debited: {balance_before_ad}c -> {balance_after_ad}c (-5000c)")
        
        # Verify campaign exists
        r = requests.get(f"{BASE_URL}/ads/campaigns", headers=headers)
        assert r.status_code == 200, f"Campaigns fetch failed: {r.status_code}"
        campaigns_data = r.json()
        campaigns = campaigns_data.get("campaigns", []) if isinstance(campaigns_data, dict) else campaigns_data
        
        created_campaign = next((c for c in campaigns if c.get("id") == campaign_id), None)
        assert created_campaign, f"Campaign {campaign_id} not found"
        print(f"✓ Campaign found: name='{created_campaign.get('name')}', budgetCents=5000")
        
        print("✅ TEST 3 PASSED: launch_ad executed successfully")
        
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        raise
    
    # ========== TEST 4: Execute navigate action ==========
    print("\n[TEST 4] Execute navigate action (manually created)")
    
    try:
        action_id = str(uuid4())
        ai_msg = {
            "id": str(uuid4()),
            "userId": user_id,
            "sessionId": session_id,
            "role": "assistant",
            "content": "J'ouvre ton wallet.",
            "actions": [{
                "id": action_id,
                "type": "navigate",
                "title": "Ouvrir wallet",
                "summary": "Navigation vers l'écran wallet",
                "payload": {
                    "tab": "wallet"
                },
                "risk": "low",
                "status": "pending"
            }],
            "createdAt": datetime.utcnow()
        }
        
        db.ai_messages.insert_one(ai_msg)
        print(f"✓ Created AI message with navigate action (id={action_id})")
        
        # Execute the action
        r = requests.post(f"{BASE_URL}/ai/actions/{action_id}/execute",
                         headers=headers,
                         json={"sessionId": session_id})
        assert r.status_code == 200, f"Execute failed: {r.status_code} {r.text}"
        data = r.json()
        
        result = data.get("result", {})
        assert result.get("kind") == "navigate", f"Result kind is {result.get('kind')}"
        assert result.get("tab") == "wallet", f"Tab is {result.get('tab')}"
        print(f"✓ navigate executed: kind=navigate, tab=wallet")
        
        print("✅ TEST 4 PASSED: navigate executed successfully")
        
    except Exception as e:
        print(f"❌ TEST 4 FAILED: {e}")
        raise
    
    # ========== TEST 5: Execute with insufficient balance ==========
    print("\n[TEST 5] Execute send_money with insufficient balance - should return 402")
    
    try:
        action_id = str(uuid4())
        ai_msg = {
            "id": str(uuid4()),
            "userId": user_id,
            "sessionId": session_id,
            "role": "assistant",
            "content": "Je prépare l'envoi.",
            "actions": [{
                "id": action_id,
                "type": "send_money",
                "title": "Envoyer 1M€",
                "summary": "Transfert impossible",
                "payload": {
                    "toName": contact_name,
                    "amountCents": 100000000,  # 1 million euros
                    "message": "Test"
                },
                "risk": "high",
                "status": "pending"
            }],
            "createdAt": datetime.utcnow()
        }
        
        db.ai_messages.insert_one(ai_msg)
        print(f"✓ Created AI message with huge send_money action (id={action_id})")
        
        # Execute the action
        r = requests.post(f"{BASE_URL}/ai/actions/{action_id}/execute",
                         headers=headers,
                         json={"sessionId": session_id})
        assert r.status_code == 402, f"Expected 402, got {r.status_code}"
        print(f"✓ Execute returned 402 (insufficient balance)")
        
        print("✅ TEST 5 PASSED: Insufficient balance returns 402")
        
    except Exception as e:
        print(f"❌ TEST 5 FAILED: {e}")
        raise
    
    print("\n" + "="*80)
    print("ALL EXECUTE ACTION TESTS PASSED")
    print("="*80)
    print("\n✅ VERIFIED:")
    print("  1. send_money executes correctly (wallet debited, transaction created)")
    print("  2. Idempotency works (409 on re-execution)")
    print("  3. create_listing executes correctly (listing created)")
    print("  4. launch_ad executes correctly (wallet debited, campaign created)")
    print("  5. navigate executes correctly (returns tab)")
    print("  6. Insufficient balance returns 402")
    print("\n🎉 PHASE 11 EXECUTE FUNCTIONALITY FULLY WORKING")
    print("="*80 + "\n")

if __name__ == "__main__":
    try:
        test_execute_actions()
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
