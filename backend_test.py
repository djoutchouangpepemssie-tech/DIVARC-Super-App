#!/usr/bin/env python3
"""
DIVARC PHASE 2 Backend API Test Suite
Tests multi-user auth, messaging, friendship mechanics, and wallet isolation
"""
import requests
import json
import time

# Base URL from .env
BASE_URL = "https://divarc-hub.preview.emergentagent.com/api"

def log_test(name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{status} - {name}")
    if details:
        print(f"  {details}")
    return passed

def test_auth_flow():
    """Test 1-4: AUTH FLOW - OTP send/verify, negative cases, /me endpoint"""
    print("\n" + "="*80)
    print("TEST 1-4: AUTH FLOW")
    print("="*80)
    
    results = []
    
    # Test 1: POST /api/auth/otp/send for new user
    try:
        email = "userA@divarc.fr"
        resp = requests.post(f"{BASE_URL}/auth/otp/send", json={"email": email}, timeout=10)
        data = resp.json()
        
        passed = (
            resp.status_code == 200 and
            data.get("ok") == True and
            data.get("isNew") == True and
            "previewCode" in data and
            data.get("delivery") == "preview"
        )
        
        preview_code = data.get("previewCode", "")
        results.append(log_test(
            "1) POST /auth/otp/send (new user)",
            passed,
            f"isNew={data.get('isNew')}, previewCode={preview_code}, delivery={data.get('delivery')}"
        ))
        
        if not passed:
            print(f"  Response: {json.dumps(data, indent=2)}")
            return results
            
    except Exception as e:
        results.append(log_test("1) POST /auth/otp/send", False, f"Exception: {e}"))
        return results
    
    # Test 2: POST /api/auth/otp/verify with correct code
    try:
        resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={
            "email": email,
            "code": preview_code,
            "name": "User A"
        }, timeout=10)
        data = resp.json()
        
        passed = (
            resp.status_code == 200 and
            "token" in data and
            "user" in data and
            data.get("isNew") == True and
            data["user"].get("handle") and
            data["user"].get("initials")
        )
        
        token_a = data.get("token", "")
        user_a = data.get("user", {})
        results.append(log_test(
            "2) POST /auth/otp/verify (correct code)",
            passed,
            f"token={token_a[:16]}..., handle={user_a.get('handle')}, initials={user_a.get('initials')}, isNew={data.get('isNew')}"
        ))
        
        if not passed:
            print(f"  Response: {json.dumps(data, indent=2)}")
            return results
            
    except Exception as e:
        results.append(log_test("2) POST /auth/otp/verify", False, f"Exception: {e}"))
        return results
    
    # Test 3: Negative cases - wrong code and no auth header
    try:
        # Wrong code
        resp = requests.post(f"{BASE_URL}/auth/otp/send", json={"email": "test@wrong.com"}, timeout=10)
        wrong_resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={
            "email": "test@wrong.com",
            "code": "000000"
        }, timeout=10)
        
        wrong_code_fail = wrong_resp.status_code == 400
        
        # No auth header
        no_auth_resp = requests.get(f"{BASE_URL}/auth/me", timeout=10)
        no_auth_fail = no_auth_resp.status_code == 401
        
        # With auth header
        with_auth_resp = requests.get(f"{BASE_URL}/auth/me", headers={
            "Authorization": f"Bearer {token_a}"
        }, timeout=10)
        with_auth_data = with_auth_resp.json()
        with_auth_pass = with_auth_resp.status_code == 200 and with_auth_data.get("id")
        
        passed = wrong_code_fail and no_auth_fail and with_auth_pass
        results.append(log_test(
            "3) Negative cases",
            passed,
            f"Wrong code -> {wrong_resp.status_code}, No auth -> {no_auth_resp.status_code}, With auth -> {with_auth_resp.status_code}"
        ))
        
    except Exception as e:
        results.append(log_test("3) Negative cases", False, f"Exception: {e}"))
    
    # Test 4: Existing user login
    try:
        # Send OTP again for same email
        resp = requests.post(f"{BASE_URL}/auth/otp/send", json={"email": email}, timeout=10)
        data = resp.json()
        code2 = data.get("previewCode", "")
        
        is_existing = data.get("isNew") == False
        
        # Verify again
        verify_resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={
            "email": email,
            "code": code2
        }, timeout=10)
        verify_data = verify_resp.json()
        
        passed = (
            is_existing and
            verify_resp.status_code == 200 and
            "token" in verify_data and
            verify_data.get("isNew") == False
        )
        
        results.append(log_test(
            "4) Existing user login",
            passed,
            f"isNew={data.get('isNew')} on send, isNew={verify_data.get('isNew')} on verify"
        ))
        
    except Exception as e:
        results.append(log_test("4) Existing user login", False, f"Exception: {e}"))
    
    # Store token for next tests
    return results, token_a, user_a

def test_user_provisioning(token):
    """Test 5: USER PROVISIONING - wallet setup and welcome transaction"""
    print("\n" + "="*80)
    print("TEST 5: USER PROVISIONING")
    print("="*80)
    
    results = []
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        # GET /api/wallet
        wallet_resp = requests.get(f"{BASE_URL}/wallet", headers=headers, timeout=10)
        wallet_data = wallet_resp.json()
        
        wallet_ok = (
            wallet_resp.status_code == 200 and
            wallet_data.get("balanceCents") == 480000 and
            wallet_data.get("currency") == "EUR" and
            len(wallet_data.get("coffres", [])) == 2
        )
        
        # GET /api/transactions
        tx_resp = requests.get(f"{BASE_URL}/transactions", headers=headers, timeout=10)
        tx_data = tx_resp.json()
        
        has_welcome = any("Bienvenue" in tx.get("label", "") for tx in tx_data)
        welcome_tx = next((tx for tx in tx_data if "Bienvenue" in tx.get("label", "")), {})
        welcome_amount = welcome_tx.get("amountCents") == 480000
        
        passed = wallet_ok and has_welcome and welcome_amount
        
        results.append(log_test(
            "5) User provisioning",
            passed,
            f"Balance={wallet_data.get('balanceCents')}, Currency={wallet_data.get('currency')}, Coffres={len(wallet_data.get('coffres', []))}, Welcome tx={has_welcome} ({welcome_tx.get('amountCents')}c)"
        ))
        
        return results, wallet_data
        
    except Exception as e:
        results.append(log_test("5) User provisioning", False, f"Exception: {e}"))
        return results, {}

def test_messaging_friendship(token):
    """Test 6-9: MESSAGING + FRIENDSHIP - conversations, messages, XP, reactions"""
    print("\n" + "="*80)
    print("TEST 6-9: MESSAGING + FRIENDSHIP")
    print("="*80)
    
    results = []
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 6: GET /api/conversations - welcome DM with Marie
    try:
        resp = requests.get(f"{BASE_URL}/conversations", headers=headers, timeout=10)
        convos = resp.json()
        
        marie_dm = next((c for c in convos if c.get("type") == "dm" and c.get("other", {}).get("handle") == "@marie"), None)
        
        has_friendship = marie_dm and "friendship" in marie_dm
        friendship = marie_dm.get("friendship", {}) if marie_dm else {}
        
        passed = (
            resp.status_code == 200 and
            marie_dm is not None and
            has_friendship and
            "xp" in friendship and
            "level" in friendship and
            "name" in friendship and
            "emoji" in friendship and
            "pct" in friendship
        )
        
        conv_id = marie_dm.get("id") if marie_dm else None
        
        results.append(log_test(
            "6) GET /conversations (welcome DM with Marie)",
            passed,
            f"Found Marie DM: {marie_dm is not None}, Friendship: streak={friendship.get('streak')}, xp={friendship.get('xp')}, level={friendship.get('level')}, name={friendship.get('name')}, emoji={friendship.get('emoji')}"
        ))
        
        if not passed or not conv_id:
            print(f"  Conversations: {json.dumps(convos, indent=2)[:500]}")
            return results
            
    except Exception as e:
        results.append(log_test("6) GET /conversations", False, f"Exception: {e}"))
        return results
    
    # Test 7: GET /api/conversations/<id>/messages
    try:
        resp = requests.get(f"{BASE_URL}/conversations/{conv_id}/messages", headers=headers, timeout=10)
        data = resp.json()
        
        conv = data.get("conversation", {})
        messages = data.get("messages", [])
        friendship = conv.get("friendship", {})
        
        has_welcome_msg = any("Bienvenue" in m.get("text", "") or "bienvenue" in m.get("text", "") for m in messages)
        
        passed = (
            resp.status_code == 200 and
            "friendship" in conv and
            len(messages) > 0 and
            has_welcome_msg
        )
        
        results.append(log_test(
            "7) GET /conversations/<id>/messages",
            passed,
            f"Friendship: {friendship}, Messages: {len(messages)}, Welcome msg: {has_welcome_msg}"
        ))
        
        initial_xp = friendship.get("xp", 0)
        
    except Exception as e:
        results.append(log_test("7) GET /conversations/<id>/messages", False, f"Exception: {e}"))
        return results
    
    # Test 8: POST /api/conversations/<id>/messages - send messages and verify XP increase
    try:
        # Send first message
        resp1 = requests.post(f"{BASE_URL}/conversations/{conv_id}/messages", 
                             headers=headers, 
                             json={"text": "Coucou"}, 
                             timeout=10)
        data1 = resp1.json()
        friendship1 = data1.get("friendship", {})
        xp1 = friendship1.get("xp", 0)
        level1 = friendship1.get("name", "")
        
        time.sleep(1)  # Wait for bot reply
        
        # Send more messages to increase XP
        messages_sent = 1
        for i in range(5):
            resp = requests.post(f"{BASE_URL}/conversations/{conv_id}/messages", 
                               headers=headers, 
                               json={"text": f"Message {i+2}"}, 
                               timeout=10)
            messages_sent += 1
            time.sleep(0.5)
        
        # Get final state
        resp_final = requests.get(f"{BASE_URL}/conversations/{conv_id}/messages", headers=headers, timeout=10)
        data_final = resp_final.json()
        friendship_final = data_final.get("conversation", {}).get("friendship", {})
        xp_final = friendship_final.get("xp", 0)
        level_final = friendship_final.get("name", "")
        
        # Check messages for bot auto-reply
        messages_final = data_final.get("messages", [])
        has_bot_reply = any(m.get("senderId") == "bot-marie" for m in messages_final)
        
        xp_increased = xp_final > initial_xp
        level_changed = level_final != level1 if xp_final >= 100 else True
        
        passed = (
            resp1.status_code == 200 and
            "friendship" in data1 and
            xp_increased and
            has_bot_reply
        )
        
        results.append(log_test(
            "8) POST /conversations/<id>/messages (XP increase)",
            passed,
            f"Initial XP: {initial_xp}, After 1st msg: {xp1} ({level1}), Final XP: {xp_final} ({level_final}), Bot reply: {has_bot_reply}"
        ))
        
    except Exception as e:
        results.append(log_test("8) POST messages (XP)", False, f"Exception: {e}"))
    
    # Test 9: POST /api/messages/<mid>/react - reactions toggle
    try:
        # Get a message to react to
        resp = requests.get(f"{BASE_URL}/conversations/{conv_id}/messages", headers=headers, timeout=10)
        messages = resp.json().get("messages", [])
        
        if len(messages) > 0:
            msg_id = messages[0].get("id")
            
            # React with emoji
            react_resp1 = requests.post(f"{BASE_URL}/messages/{msg_id}/react", 
                                       headers=headers, 
                                       json={"emoji": "🔥"}, 
                                       timeout=10)
            reactions1 = react_resp1.json().get("reactions", [])
            has_reaction = any(r.get("emoji") == "🔥" for r in reactions1)
            
            # React again to toggle off
            react_resp2 = requests.post(f"{BASE_URL}/messages/{msg_id}/react", 
                                       headers=headers, 
                                       json={"emoji": "🔥"}, 
                                       timeout=10)
            reactions2 = react_resp2.json().get("reactions", [])
            reaction_removed = not any(r.get("emoji") == "🔥" for r in reactions2)
            
            passed = (
                react_resp1.status_code == 200 and
                has_reaction and
                react_resp2.status_code == 200 and
                reaction_removed
            )
            
            results.append(log_test(
                "9) POST /messages/<id>/react (toggle)",
                passed,
                f"First react: {len(reactions1)} reactions (has 🔥: {has_reaction}), Second react: {len(reactions2)} reactions (removed: {reaction_removed})"
            ))
        else:
            results.append(log_test("9) POST /messages/<id>/react", False, "No messages to react to"))
            
    except Exception as e:
        results.append(log_test("9) POST /messages/<id>/react", False, f"Exception: {e}"))
    
    return results

def test_groups_communities(token):
    """Test 10-12: GROUP and COMMUNITIES - create group, join community, DM dedupe"""
    print("\n" + "="*80)
    print("TEST 10-12: GROUPS & COMMUNITIES")
    print("="*80)
    
    results = []
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 10: POST /api/conversations (group)
    try:
        resp = requests.post(f"{BASE_URL}/conversations", 
                           headers=headers, 
                           json={
                               "type": "group",
                               "name": "Team",
                               "memberHandles": ["@thomas", "@lena"]
                           }, 
                           timeout=10)
        data = resp.json()
        group_id = data.get("id")
        
        # Verify group appears in conversations
        convos_resp = requests.get(f"{BASE_URL}/conversations", headers=headers, timeout=10)
        convos = convos_resp.json()
        group_conv = next((c for c in convos if c.get("id") == group_id), None)
        
        passed = (
            resp.status_code == 200 and
            group_id and
            group_conv is not None and
            group_conv.get("memberCount") == 3
        )
        
        results.append(log_test(
            "10) POST /conversations (group)",
            passed,
            f"Group ID: {group_id}, Member count: {group_conv.get('memberCount') if group_conv else 'N/A'}"
        ))
        
    except Exception as e:
        results.append(log_test("10) POST /conversations (group)", False, f"Exception: {e}"))
    
    # Test 11: GET /api/communities and join
    try:
        # Get communities
        resp = requests.get(f"{BASE_URL}/communities", headers=headers, timeout=10)
        communities = resp.json()
        
        paris_comm = next((c for c in communities if c.get("id") == "comm-paris"), None)
        initially_joined = paris_comm.get("joined") if paris_comm else None
        
        # Join community
        join_resp = requests.post(f"{BASE_URL}/conversations/comm-paris/join", 
                                 headers=headers, 
                                 json={}, 
                                 timeout=10)
        
        # Verify joined
        resp2 = requests.get(f"{BASE_URL}/communities", headers=headers, timeout=10)
        communities2 = resp2.json()
        paris_comm2 = next((c for c in communities2 if c.get("id") == "comm-paris"), None)
        now_joined = paris_comm2.get("joined") if paris_comm2 else None
        
        # Verify in conversations
        convos_resp = requests.get(f"{BASE_URL}/conversations", headers=headers, timeout=10)
        convos = convos_resp.json()
        has_paris = any(c.get("id") == "comm-paris" for c in convos)
        
        passed = (
            resp.status_code == 200 and
            paris_comm is not None and
            join_resp.status_code == 200 and
            now_joined == True and
            has_paris
        )
        
        results.append(log_test(
            "11) GET /communities and join",
            passed,
            f"Paris community found: {paris_comm is not None}, Initially joined: {initially_joined}, After join: {now_joined}, In conversations: {has_paris}"
        ))
        
    except Exception as e:
        results.append(log_test("11) GET /communities and join", False, f"Exception: {e}"))
    
    # Test 12: DM dedupe
    try:
        # Create DM with @thomas
        resp1 = requests.post(f"{BASE_URL}/conversations", 
                            headers=headers, 
                            json={
                                "type": "dm",
                                "memberHandles": ["@thomas"]
                            }, 
                            timeout=10)
        data1 = resp1.json()
        dm_id1 = data1.get("id")
        
        # Create again
        resp2 = requests.post(f"{BASE_URL}/conversations", 
                            headers=headers, 
                            json={
                                "type": "dm",
                                "memberHandles": ["@thomas"]
                            }, 
                            timeout=10)
        data2 = resp2.json()
        dm_id2 = data2.get("id")
        is_existing = data2.get("existing")
        
        passed = (
            resp1.status_code == 200 and
            resp2.status_code == 200 and
            dm_id1 == dm_id2 and
            is_existing == True
        )
        
        results.append(log_test(
            "12) DM dedupe",
            passed,
            f"First DM: {dm_id1}, Second DM: {dm_id2}, existing={is_existing}, Same ID: {dm_id1 == dm_id2}"
        ))
        
    except Exception as e:
        results.append(log_test("12) DM dedupe", False, f"Exception: {e}"))
    
    return results

def test_multi_user_isolation():
    """Test 13: MULTI-USER ISOLATION - create second user and verify separation"""
    print("\n" + "="*80)
    print("TEST 13: MULTI-USER ISOLATION")
    print("="*80)
    
    results = []
    
    try:
        # Create userB
        email_b = "userB@divarc.fr"
        send_resp = requests.post(f"{BASE_URL}/auth/otp/send", json={"email": email_b}, timeout=10)
        code_b = send_resp.json().get("previewCode")
        
        verify_resp = requests.post(f"{BASE_URL}/auth/otp/verify", json={
            "email": email_b,
            "code": code_b,
            "name": "User B"
        }, timeout=10)
        token_b = verify_resp.json().get("token")
        
        headers_b = {"Authorization": f"Bearer {token_b}"}
        
        # Check userB wallet
        wallet_resp = requests.get(f"{BASE_URL}/wallet", headers=headers_b, timeout=10)
        wallet_b = wallet_resp.json()
        
        wallet_independent = wallet_b.get("balanceCents") == 480000
        
        # Check userB conversations
        convos_resp = requests.get(f"{BASE_URL}/conversations", headers=headers_b, timeout=10)
        convos_b = convos_resp.json()
        
        # UserB should NOT see userA's "Team" group
        has_team_group = any(c.get("title") == "Team" or c.get("name") == "Team" for c in convos_b)
        
        # UserB should have welcome DM with Marie
        has_marie = any(c.get("type") == "dm" and c.get("other", {}).get("handle") == "@marie" for c in convos_b)
        
        passed = (
            verify_resp.status_code == 200 and
            wallet_independent and
            not has_team_group and
            has_marie
        )
        
        results.append(log_test(
            "13) Multi-user isolation",
            passed,
            f"UserB balance: {wallet_b.get('balanceCents')}, Has Team group: {has_team_group}, Has Marie DM: {has_marie}"
        ))
        
        return results, token_b
        
    except Exception as e:
        results.append(log_test("13) Multi-user isolation", False, f"Exception: {e}"))
        return results, None

def test_wallet_under_auth(token):
    """Test 14-15: RE-VERIFY WALLET - send and enveloppe under auth"""
    print("\n" + "="*80)
    print("TEST 14-15: WALLET UNDER AUTH")
    print("="*80)
    
    results = []
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 14: POST /api/send with idempotency
    try:
        # Get initial balance
        wallet_resp = requests.get(f"{BASE_URL}/wallet", headers=headers, timeout=10)
        initial_balance = wallet_resp.json().get("balanceCents")
        
        # Send money
        send_resp = requests.post(f"{BASE_URL}/send", 
                                 headers=headers, 
                                 json={
                                     "toHandle": "@thomas",
                                     "toName": "Thomas",
                                     "amountCents": 2000,
                                     "idempotencyKey": "k1"
                                 }, 
                                 timeout=10)
        send_data = send_resp.json()
        new_balance = send_data.get("balanceCents")
        
        balance_debited = new_balance == initial_balance - 2000
        
        # Repeat with same idempotencyKey
        send_resp2 = requests.post(f"{BASE_URL}/send", 
                                  headers=headers, 
                                  json={
                                      "toHandle": "@thomas",
                                      "toName": "Thomas",
                                      "amountCents": 2000,
                                      "idempotencyKey": "k1"
                                  }, 
                                  timeout=10)
        send_data2 = send_resp2.json()
        is_idempotent = send_data2.get("idempotent")
        
        # Verify balance unchanged
        wallet_resp2 = requests.get(f"{BASE_URL}/wallet", headers=headers, timeout=10)
        final_balance = wallet_resp2.json().get("balanceCents")
        
        balance_unchanged = final_balance == new_balance
        
        passed = (
            send_resp.status_code == 200 and
            balance_debited and
            send_resp2.status_code == 200 and
            is_idempotent == True and
            balance_unchanged
        )
        
        results.append(log_test(
            "14) POST /send with idempotency",
            passed,
            f"Initial: {initial_balance}, After send: {new_balance} (debited: {balance_debited}), After repeat: {final_balance} (idempotent: {is_idempotent}, unchanged: {balance_unchanged})"
        ))
        
    except Exception as e:
        results.append(log_test("14) POST /send with idempotency", False, f"Exception: {e}"))
    
    # Test 15: POST /api/enveloppe/create - verify share sum
    try:
        # Create enveloppe
        env_resp = requests.post(f"{BASE_URL}/enveloppe/create", 
                                headers=headers, 
                                json={
                                    "totalCents": 3333,
                                    "count": 5
                                }, 
                                timeout=10)
        env_data = env_resp.json()
        enveloppe = env_data.get("enveloppe", {})
        shares = enveloppe.get("shares", [])
        
        share_sum = sum(s.get("amountCents", 0) for s in shares)
        sum_exact = share_sum == 3333
        
        # Test insufficient balance
        huge_resp = requests.post(f"{BASE_URL}/enveloppe/create", 
                                 headers=headers, 
                                 json={
                                     "totalCents": 99999999,
                                     "count": 1
                                 }, 
                                 timeout=10)
        
        insufficient_error = huge_resp.status_code == 402
        
        passed = (
            env_resp.status_code == 200 and
            len(shares) == 5 and
            sum_exact and
            insufficient_error
        )
        
        results.append(log_test(
            "15) POST /enveloppe/create (share sum)",
            passed,
            f"Shares: {len(shares)}, Sum: {share_sum} (expected 3333, exact: {sum_exact}), Insufficient balance error: {insufficient_error} (status {huge_resp.status_code})"
        ))
        
    except Exception as e:
        results.append(log_test("15) POST /enveloppe/create", False, f"Exception: {e}"))
    
    return results

def main():
    print("\n" + "="*80)
    print("DIVARC PHASE 2 BACKEND API TEST SUITE")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Testing: Auth, Messaging, Friendship, Multi-user, Wallet isolation")
    print("="*80)
    
    all_results = []
    
    # Test 1-4: Auth flow
    auth_results = test_auth_flow()
    if isinstance(auth_results, tuple):
        results, token_a, user_a = auth_results
        all_results.extend(results)
    else:
        all_results.extend(auth_results)
        print("\n❌ Auth flow failed, cannot continue")
        return
    
    # Test 5: User provisioning
    prov_results = test_user_provisioning(token_a)
    if isinstance(prov_results, tuple):
        results, wallet = prov_results
        all_results.extend(results)
    else:
        all_results.extend(prov_results)
    
    # Test 6-9: Messaging + Friendship
    msg_results = test_messaging_friendship(token_a)
    all_results.extend(msg_results)
    
    # Test 10-12: Groups & Communities
    group_results = test_groups_communities(token_a)
    all_results.extend(group_results)
    
    # Test 13: Multi-user isolation
    isolation_results = test_multi_user_isolation()
    if isinstance(isolation_results, tuple):
        results, token_b = isolation_results
        all_results.extend(results)
    else:
        all_results.extend(isolation_results)
    
    # Test 14-15: Wallet under auth
    wallet_results = test_wallet_under_auth(token_a)
    all_results.extend(wallet_results)
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    passed = sum(1 for r in all_results if r)
    total = len(all_results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED")
    else:
        print(f"\n❌ {total - passed} test(s) failed")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
