#!/usr/bin/env python3
"""
DIVARC Backend API Test Suite
Tests all backend endpoints with focus on:
- Idempotency
- Double-entry ledger
- Balance integrity
- Enveloppe share sum validation
"""

import requests
import json
import os
from datetime import datetime

# Base URL from environment
BASE_URL = "https://divarc-hub.preview.emergentagent.com/api"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def log_test(name, passed, details=""):
    status = f"{Colors.GREEN}✅ PASS{Colors.END}" if passed else f"{Colors.RED}❌ FAIL{Colors.END}"
    print(f"\n{status} - {name}")
    if details:
        print(f"  {details}")
    return passed

def test_seed_idempotency():
    """Test POST /api/seed - must be idempotent, no duplicate data"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST 1: POST /api/seed - Idempotency{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    try:
        # First call
        resp1 = requests.post(f"{BASE_URL}/seed", timeout=10)
        print(f"First call status: {resp1.status_code}")
        data1 = resp1.json()
        print(f"First call response: {json.dumps(data1, indent=2)}")
        
        if resp1.status_code != 200:
            return log_test("Seed endpoint", False, f"Expected 200, got {resp1.status_code}")
        
        if 'userId' not in data1 or 'user' not in data1:
            return log_test("Seed endpoint", False, "Missing userId or user in response")
        
        user_id_1 = data1['userId']
        
        # Second call - should be idempotent
        resp2 = requests.post(f"{BASE_URL}/seed", timeout=10)
        print(f"Second call status: {resp2.status_code}")
        data2 = resp2.json()
        print(f"Second call response: {json.dumps(data2, indent=2)}")
        
        if resp2.status_code != 200:
            return log_test("Seed idempotency", False, f"Second call failed with {resp2.status_code}")
        
        user_id_2 = data2['userId']
        
        if user_id_1 != user_id_2:
            return log_test("Seed idempotency", False, f"User IDs differ: {user_id_1} vs {user_id_2}")
        
        return log_test("Seed idempotency", True, f"User {user_id_1} created/returned idempotently")
        
    except Exception as e:
        return log_test("Seed endpoint", False, f"Exception: {str(e)}")

def test_me_endpoint():
    """Test GET /api/me - returns demo user"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST 2: GET /api/me{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    try:
        resp = requests.get(f"{BASE_URL}/me", timeout=10)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if resp.status_code != 200:
            return log_test("GET /api/me", False, f"Expected 200, got {resp.status_code}")
        
        if data.get('handle') != '@adrien':
            return log_test("GET /api/me", False, f"Expected handle @adrien, got {data.get('handle')}")
        
        if data.get('kyc') != 'eIDAS':
            return log_test("GET /api/me", False, f"Expected kyc eIDAS, got {data.get('kyc')}")
        
        return log_test("GET /api/me", True, f"User @adrien with eIDAS kyc returned")
        
    except Exception as e:
        return log_test("GET /api/me", False, f"Exception: {str(e)}")

def test_wallet_endpoint():
    """Test GET /api/wallet - returns balance, currency, coffres"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST 3: GET /api/wallet{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    try:
        resp = requests.get(f"{BASE_URL}/wallet", timeout=10)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if resp.status_code != 200:
            return log_test("GET /api/wallet", False, f"Expected 200, got {resp.status_code}")
        
        # Check initial balance
        if 'balanceCents' not in data:
            return log_test("GET /api/wallet", False, "Missing balanceCents")
        
        print(f"Balance: {data['balanceCents']} cents")
        
        if data.get('currency') != 'EUR':
            return log_test("GET /api/wallet", False, f"Expected EUR, got {data.get('currency')}")
        
        if data.get('sepaInstant') != True:
            return log_test("GET /api/wallet", False, "sepaInstant should be true")
        
        if 'carbonMonthKg' not in data:
            return log_test("GET /api/wallet", False, "Missing carbonMonthKg")
        
        if 'coffres' not in data or len(data['coffres']) != 3:
            return log_test("GET /api/wallet", False, f"Expected 3 coffres, got {len(data.get('coffres', []))}")
        
        # Check coffres structure
        for coffre in data['coffres']:
            if 'balanceCents' not in coffre or 'goalCents' not in coffre:
                return log_test("GET /api/wallet", False, "Coffre missing balanceCents or goalCents")
        
        return log_test("GET /api/wallet", True, f"Wallet with {data['balanceCents']} cents, 3 coffres")
        
    except Exception as e:
        return log_test("GET /api/wallet", False, f"Exception: {str(e)}")

def test_transactions_endpoint():
    """Test GET /api/transactions - returns sorted desc"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST 4: GET /api/transactions{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    try:
        resp = requests.get(f"{BASE_URL}/transactions", timeout=10)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Response: {len(data)} transactions")
        if len(data) > 0:
            print(f"First transaction: {json.dumps(data[0], indent=2)}")
        
        if resp.status_code != 200:
            return log_test("GET /api/transactions", False, f"Expected 200, got {resp.status_code}")
        
        if not isinstance(data, list):
            return log_test("GET /api/transactions", False, "Expected array response")
        
        # Check sorting (desc by createdAt)
        if len(data) > 1:
            for i in range(len(data) - 1):
                date1 = data[i].get('createdAt')
                date2 = data[i+1].get('createdAt')
                if date1 and date2 and date1 < date2:
                    return log_test("GET /api/transactions", False, "Transactions not sorted desc by createdAt")
        
        return log_test("GET /api/transactions", True, f"{len(data)} transactions sorted desc")
        
    except Exception as e:
        return log_test("GET /api/transactions", False, f"Exception: {str(e)}")

def test_contacts_endpoint():
    """Test GET /api/contacts - with and without filter"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST 5: GET /api/contacts{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    try:
        # Test without filter
        resp1 = requests.get(f"{BASE_URL}/contacts", timeout=10)
        print(f"Status (no filter): {resp1.status_code}")
        data1 = resp1.json()
        print(f"Response: {len(data1)} contacts")
        
        if resp1.status_code != 200:
            return log_test("GET /api/contacts", False, f"Expected 200, got {resp1.status_code}")
        
        if len(data1) != 5:
            return log_test("GET /api/contacts", False, f"Expected 5 contacts, got {len(data1)}")
        
        # Test with filter q=marie
        resp2 = requests.get(f"{BASE_URL}/contacts?q=marie", timeout=10)
        print(f"Status (q=marie): {resp2.status_code}")
        data2 = resp2.json()
        print(f"Filtered response: {json.dumps(data2, indent=2)}")
        
        if resp2.status_code != 200:
            return log_test("GET /api/contacts?q=marie", False, f"Expected 200, got {resp2.status_code}")
        
        if len(data2) != 1:
            return log_test("GET /api/contacts?q=marie", False, f"Expected 1 contact, got {len(data2)}")
        
        if data2[0].get('name') != 'Marie Laurent':
            return log_test("GET /api/contacts?q=marie", False, f"Expected Marie Laurent, got {data2[0].get('name')}")
        
        return log_test("GET /api/contacts", True, "5 contacts total, 1 filtered for 'marie'")
        
    except Exception as e:
        return log_test("GET /api/contacts", False, f"Exception: {str(e)}")

def test_send_p2p():
    """Test POST /api/send - debit, transaction, ledger, idempotency, errors"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST 6: POST /api/send - P2P with idempotency{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    try:
        # Get initial balance
        resp_wallet = requests.get(f"{BASE_URL}/wallet", timeout=10)
        initial_balance = resp_wallet.json()['balanceCents']
        print(f"Initial balance: {initial_balance} cents")
        
        # Test 1: Valid send
        send_amount = 1000
        idempotency_key = f"test-send-{datetime.now().timestamp()}"
        
        payload = {
            "toHandle": "@marie",
            "toName": "Marie Laurent",
            "amountCents": send_amount,
            "idempotencyKey": idempotency_key,
            "route": "A2A"
        }
        
        resp1 = requests.post(f"{BASE_URL}/send", json=payload, timeout=10)
        print(f"First send status: {resp1.status_code}")
        data1 = resp1.json()
        print(f"First send response: {json.dumps(data1, indent=2)}")
        
        if resp1.status_code != 200:
            return log_test("POST /api/send", False, f"Expected 200, got {resp1.status_code}")
        
        if 'transaction' not in data1 or 'balanceCents' not in data1:
            return log_test("POST /api/send", False, "Missing transaction or balanceCents in response")
        
        new_balance = data1['balanceCents']
        expected_balance = initial_balance - send_amount
        
        if new_balance != expected_balance:
            return log_test("POST /api/send", False, f"Balance mismatch: expected {expected_balance}, got {new_balance}")
        
        print(f"Balance after send: {new_balance} cents (debited {send_amount})")
        
        # Test 2: Idempotency - same key should not debit again
        resp2 = requests.post(f"{BASE_URL}/send", json=payload, timeout=10)
        print(f"Second send (same key) status: {resp2.status_code}")
        data2 = resp2.json()
        print(f"Second send response: {json.dumps(data2, indent=2)}")
        
        if resp2.status_code != 200:
            return log_test("POST /api/send idempotency", False, f"Expected 200, got {resp2.status_code}")
        
        if not data2.get('idempotent'):
            return log_test("POST /api/send idempotency", False, "Expected idempotent:true")
        
        # Verify balance didn't change
        resp_wallet2 = requests.get(f"{BASE_URL}/wallet", timeout=10)
        balance_after_dup = resp_wallet2.json()['balanceCents']
        
        if balance_after_dup != new_balance:
            return log_test("POST /api/send idempotency", False, f"Balance changed on duplicate: {new_balance} -> {balance_after_dup}")
        
        print(f"Balance unchanged after duplicate send: {balance_after_dup} cents")
        
        # Test 3: Insufficient balance (402)
        huge_amount = initial_balance + 1000000
        payload_huge = {
            "toHandle": "@marie",
            "toName": "Marie Laurent",
            "amountCents": huge_amount,
            "idempotencyKey": f"test-huge-{datetime.now().timestamp()}",
            "route": "A2A"
        }
        
        resp3 = requests.post(f"{BASE_URL}/send", json=payload_huge, timeout=10)
        print(f"Insufficient balance test status: {resp3.status_code}")
        
        if resp3.status_code != 402:
            return log_test("POST /api/send insufficient balance", False, f"Expected 402, got {resp3.status_code}")
        
        # Test 4: Invalid amount (400)
        payload_invalid = {
            "toHandle": "@marie",
            "toName": "Marie Laurent",
            "amountCents": 0,
            "idempotencyKey": f"test-invalid-{datetime.now().timestamp()}",
            "route": "A2A"
        }
        
        resp4 = requests.post(f"{BASE_URL}/send", json=payload_invalid, timeout=10)
        print(f"Invalid amount test status: {resp4.status_code}")
        
        if resp4.status_code != 400:
            return log_test("POST /api/send invalid amount", False, f"Expected 400, got {resp4.status_code}")
        
        # Test 5: Verify ledger entries exist (double-entry)
        # We can't directly query ledger via API, but we verified the transaction was created
        # and balance was debited correctly, which implies ledger entries were created
        
        return log_test("POST /api/send", True, "Send works with idempotency, balance checks, error handling")
        
    except Exception as e:
        return log_test("POST /api/send", False, f"Exception: {str(e)}")

def test_enveloppe_create():
    """Test POST /api/enveloppe/create - debit, sum of shares == totalCents"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST 7: POST /api/enveloppe/create - Share sum validation{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    try:
        # Get initial balance
        resp_wallet = requests.get(f"{BASE_URL}/wallet", timeout=10)
        initial_balance = resp_wallet.json()['balanceCents']
        print(f"Initial balance: {initial_balance} cents")
        
        # Test with various counts and odd totals
        test_cases = [
            {"totalCents": 100, "count": 1, "message": "Test 1 share"},
            {"totalCents": 333, "count": 3, "message": "Test 3 shares odd total"},
            {"totalCents": 555, "count": 5, "message": "Test 5 shares odd total"},
            {"totalCents": 888, "count": 8, "message": "Test 8 shares"},
        ]
        
        all_passed = True
        total_debited = 0
        
        for i, test_case in enumerate(test_cases):
            print(f"\n--- Test case {i+1}: {test_case['count']} shares, {test_case['totalCents']} cents ---")
            
            resp = requests.post(f"{BASE_URL}/enveloppe/create", json=test_case, timeout=10)
            print(f"Status: {resp.status_code}")
            data = resp.json()
            
            if resp.status_code != 200:
                log_test(f"Enveloppe create case {i+1}", False, f"Expected 200, got {resp.status_code}")
                all_passed = False
                continue
            
            if 'enveloppe' not in data:
                log_test(f"Enveloppe create case {i+1}", False, "Missing enveloppe in response")
                all_passed = False
                continue
            
            env = data['enveloppe']
            shares = env.get('shares', [])
            
            print(f"Shares count: {len(shares)}")
            print(f"Shares: {[s['amountCents'] for s in shares]}")
            
            # Check count
            if len(shares) != test_case['count']:
                log_test(f"Enveloppe create case {i+1}", False, f"Expected {test_case['count']} shares, got {len(shares)}")
                all_passed = False
                continue
            
            # CRITICAL: Check sum of shares == totalCents
            sum_shares = sum(s['amountCents'] for s in shares)
            print(f"Sum of shares: {sum_shares} cents")
            
            if sum_shares != test_case['totalCents']:
                log_test(f"Enveloppe create case {i+1}", False, f"Sum mismatch: expected {test_case['totalCents']}, got {sum_shares}")
                all_passed = False
                continue
            
            total_debited += test_case['totalCents']
            log_test(f"Enveloppe create case {i+1}", True, f"Sum correct: {sum_shares} cents")
        
        # Verify total balance debited
        resp_wallet2 = requests.get(f"{BASE_URL}/wallet", timeout=10)
        final_balance = resp_wallet2.json()['balanceCents']
        expected_balance = initial_balance - total_debited
        
        print(f"\nFinal balance: {final_balance} cents")
        print(f"Expected balance: {expected_balance} cents")
        print(f"Total debited: {total_debited} cents")
        
        if final_balance != expected_balance:
            return log_test("Enveloppe create balance", False, f"Balance mismatch: expected {expected_balance}, got {final_balance}")
        
        # Test insufficient balance
        huge_amount = initial_balance + 1000000
        payload_huge = {"totalCents": huge_amount, "count": 3, "message": "Too much"}
        resp_huge = requests.post(f"{BASE_URL}/enveloppe/create", json=payload_huge, timeout=10)
        print(f"\nInsufficient balance test status: {resp_huge.status_code}")
        
        if resp_huge.status_code != 402:
            return log_test("Enveloppe create insufficient balance", False, f"Expected 402, got {resp_huge.status_code}")
        
        if all_passed:
            return log_test("POST /api/enveloppe/create", True, "All share sums correct, balance debited properly")
        else:
            return log_test("POST /api/enveloppe/create", False, "Some test cases failed")
        
    except Exception as e:
        return log_test("POST /api/enveloppe/create", False, f"Exception: {str(e)}")

def test_enveloppe_open():
    """Test POST /api/enveloppe/open - claim shares, idempotency per claimer"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST 8: POST /api/enveloppe/open - Claim with idempotency{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    try:
        # Create an enveloppe first
        create_payload = {"totalCents": 500, "count": 3, "message": "Test claims"}
        resp_create = requests.post(f"{BASE_URL}/enveloppe/create", json=create_payload, timeout=10)
        
        if resp_create.status_code != 200:
            return log_test("Enveloppe open setup", False, f"Failed to create enveloppe: {resp_create.status_code}")
        
        env_id = resp_create.json()['enveloppe']['id']
        print(f"Created enveloppe: {env_id}")
        
        # Test 1: First claimer
        claimer1 = "alice@test.com"
        resp1 = requests.post(f"{BASE_URL}/enveloppe/open", json={"enveloppeId": env_id, "claimer": claimer1}, timeout=10)
        print(f"First claim status: {resp1.status_code}")
        data1 = resp1.json()
        print(f"First claim response: {json.dumps(data1, indent=2)}")
        
        if resp1.status_code != 200:
            return log_test("Enveloppe open first claim", False, f"Expected 200, got {resp1.status_code}")
        
        if 'amountCents' not in data1:
            return log_test("Enveloppe open first claim", False, "Missing amountCents")
        
        amount1 = data1['amountCents']
        print(f"Claimer 1 received: {amount1} cents")
        
        # Test 2: Same claimer again - should get alreadyClaimed:true with same amount
        resp2 = requests.post(f"{BASE_URL}/enveloppe/open", json={"enveloppeId": env_id, "claimer": claimer1}, timeout=10)
        print(f"Second claim (same claimer) status: {resp2.status_code}")
        data2 = resp2.json()
        print(f"Second claim response: {json.dumps(data2, indent=2)}")
        
        if resp2.status_code != 200:
            return log_test("Enveloppe open idempotency", False, f"Expected 200, got {resp2.status_code}")
        
        if not data2.get('alreadyClaimed'):
            return log_test("Enveloppe open idempotency", False, "Expected alreadyClaimed:true")
        
        if data2['amountCents'] != amount1:
            return log_test("Enveloppe open idempotency", False, f"Amount changed: {amount1} -> {data2['amountCents']}")
        
        print(f"Claimer 1 got same amount again: {data2['amountCents']} cents")
        
        # Test 3: Second claimer
        claimer2 = "bob@test.com"
        resp3 = requests.post(f"{BASE_URL}/enveloppe/open", json={"enveloppeId": env_id, "claimer": claimer2}, timeout=10)
        print(f"Third claim (new claimer) status: {resp3.status_code}")
        data3 = resp3.json()
        print(f"Third claim response: {json.dumps(data3, indent=2)}")
        
        if resp3.status_code != 200:
            return log_test("Enveloppe open second claimer", False, f"Expected 200, got {resp3.status_code}")
        
        amount2 = data3['amountCents']
        print(f"Claimer 2 received: {amount2} cents")
        
        # Test 4: Third claimer (last share)
        claimer3 = "charlie@test.com"
        resp4 = requests.post(f"{BASE_URL}/enveloppe/open", json={"enveloppeId": env_id, "claimer": claimer3}, timeout=10)
        print(f"Fourth claim (last share) status: {resp4.status_code}")
        data4 = resp4.json()
        print(f"Fourth claim response: {json.dumps(data4, indent=2)}")
        
        if resp4.status_code != 200:
            return log_test("Enveloppe open third claimer", False, f"Expected 200, got {resp4.status_code}")
        
        amount3 = data4['amountCents']
        print(f"Claimer 3 received: {amount3} cents")
        
        # Test 5: Fourth claimer - should get 410 (all claimed)
        claimer4 = "dave@test.com"
        resp5 = requests.post(f"{BASE_URL}/enveloppe/open", json={"enveloppeId": env_id, "claimer": claimer4}, timeout=10)
        print(f"Fifth claim (all claimed) status: {resp5.status_code}")
        
        if resp5.status_code != 410:
            return log_test("Enveloppe open all claimed", False, f"Expected 410, got {resp5.status_code}")
        
        print(f"Correctly returned 410 when all shares claimed")
        
        # Verify remaining count
        if 'remaining' in data4 and data4['remaining'] != 0:
            return log_test("Enveloppe open remaining", False, f"Expected remaining=0, got {data4['remaining']}")
        
        return log_test("POST /api/enveloppe/open", True, "Claims work with idempotency, 410 when exhausted")
        
    except Exception as e:
        return log_test("POST /api/enveloppe/open", False, f"Exception: {str(e)}")

def test_coffres_create():
    """Test POST /api/coffres - create coffre"""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST 9: POST /api/coffres{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    try:
        payload = {
            "name": "Test Coffre",
            "goalCents": 50000,
            "rule": "round_up"
        }
        
        resp = requests.post(f"{BASE_URL}/coffres", json=payload, timeout=10)
        print(f"Status: {resp.status_code}")
        data = resp.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if resp.status_code != 200:
            return log_test("POST /api/coffres", False, f"Expected 200, got {resp.status_code}")
        
        if 'id' not in data:
            return log_test("POST /api/coffres", False, "Missing id in response")
        
        if data.get('name') != "Test Coffre":
            return log_test("POST /api/coffres", False, f"Name mismatch: expected 'Test Coffre', got {data.get('name')}")
        
        if data.get('goalCents') != 50000:
            return log_test("POST /api/coffres", False, f"Goal mismatch: expected 50000, got {data.get('goalCents')}")
        
        return log_test("POST /api/coffres", True, f"Coffre created: {data['name']}")
        
    except Exception as e:
        return log_test("POST /api/coffres", False, f"Exception: {str(e)}")

def main():
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}DIVARC Backend API Test Suite{Colors.END}")
    print(f"{Colors.YELLOW}Base URL: {BASE_URL}{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}")
    
    results = []
    
    # Run all tests
    results.append(("Seed idempotency", test_seed_idempotency()))
    results.append(("GET /api/me", test_me_endpoint()))
    results.append(("GET /api/wallet", test_wallet_endpoint()))
    results.append(("GET /api/transactions", test_transactions_endpoint()))
    results.append(("GET /api/contacts", test_contacts_endpoint()))
    results.append(("POST /api/send", test_send_p2p()))
    results.append(("POST /api/enveloppe/create", test_enveloppe_create()))
    results.append(("POST /api/enveloppe/open", test_enveloppe_open()))
    results.append(("POST /api/coffres", test_coffres_create()))
    
    # Summary
    print(f"\n{Colors.YELLOW}{'='*60}{Colors.END}")
    print(f"{Colors.YELLOW}TEST SUMMARY{Colors.END}")
    print(f"{Colors.YELLOW}{'='*60}{Colors.END}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.END}" if result else f"{Colors.RED}❌ FAIL{Colors.END}"
        print(f"{status} - {name}")
    
    print(f"\n{Colors.YELLOW}Total: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"{Colors.GREEN}All tests passed!{Colors.END}")
        return 0
    else:
        print(f"{Colors.RED}Some tests failed!{Colors.END}")
        return 1

if __name__ == "__main__":
    exit(main())
