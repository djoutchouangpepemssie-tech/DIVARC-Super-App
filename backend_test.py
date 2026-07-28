#!/usr/bin/env python3
"""
DIVARC App Store Backend Test - PHASE 6
Tests all app store endpoints with comprehensive verification
"""

import requests
import json
import sys
import re

BASE_URL = "https://divarc-hub.preview.emergentagent.com/api"

def log(msg):
    print(f"[TEST] {msg}")

def create_user(email, name):
    """Helper to create and authenticate a user"""
    # Send OTP
    res = requests.post(f"{BASE_URL}/auth/otp/send", json={"email": email})
    assert res.status_code == 200, f"OTP send failed: {res.status_code} {res.text}"
    data = res.json()
    assert data.get("ok") == True, f"OTP send not ok: {data}"
    assert "previewCode" in data, f"No previewCode in response: {data}"
    code = data["previewCode"]
    
    # Verify OTP
    res = requests.post(f"{BASE_URL}/auth/otp/verify", json={
        "email": email,
        "code": code,
        "name": name
    })
    assert res.status_code == 200, f"OTP verify failed: {res.status_code} {res.text}"
    data = res.json()
    assert "token" in data, f"No token in response: {data}"
    token = data["token"]
    user = data.get("user", {})
    log(f"✓ Created user: {user.get('name')} ({user.get('handle')})")
    return token, user

def test_phase6_app_store():
    """Test PHASE 6: App Store directory + consented connect/disconnect"""
    
    log("=" * 80)
    log("PHASE 6: APP STORE - COMPREHENSIVE BACKEND TEST")
    log("=" * 80)
    
    # ========================================================================
    # SETUP: Create user store6@divarc.fr
    # ========================================================================
    log("\n[SETUP] Creating user store6@divarc.fr")
    token, user = create_user("store6@divarc.fr", "Store Six")
    headers = {"Authorization": f"Bearer {token}"}
    
    # ========================================================================
    # TEST 1: GET /api/store/apps - Verify 12 seeded apps with all fields
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 1: GET /api/store/apps - Verify 12 seeded apps with all required fields")
    log("=" * 80)
    
    res = requests.get(f"{BASE_URL}/store/apps", headers=headers)
    assert res.status_code == 200, f"GET /store/apps failed: {res.status_code} {res.text}"
    apps = res.json()
    
    log(f"✓ GET /store/apps returned {len(apps)} apps")
    assert len(apps) == 12, f"Expected 12 apps, got {len(apps)}"
    
    # Verify each app has required fields
    required_fields = ['id', 'name', 'cat', 'emoji', 'color', 'desc', 'perms', 'rating', 'users', 'connected', 'pseudonym']
    for app in apps:
        for field in required_fields:
            assert field in app, f"App {app.get('name')} missing field: {field}"
        
        # Verify initial state: connected=false, pseudonym=null
        assert app['connected'] == False, f"App {app['name']} should have connected=false initially"
        assert app['pseudonym'] == None, f"App {app['name']} should have pseudonym=null initially"
        
        # Verify perms is an array
        assert isinstance(app['perms'], list), f"App {app['name']} perms should be an array"
    
    log(f"✓ All 12 apps have required fields: {', '.join(required_fields)}")
    log(f"✓ All apps have connected=false and pseudonym=null initially")
    
    # Find specific apps for later tests
    spotly = next((a for a in apps if a['id'] == 'spotly'), None)
    bankly = next((a for a in apps if a['id'] == 'bankly'), None)
    flixo = next((a for a in apps if a['id'] == 'flixo'), None)
    
    assert spotly is not None, "Spotly app not found"
    assert bankly is not None, "Bankly app not found"
    assert flixo is not None, "Flixo app not found"
    
    log(f"✓ Found Spotly: {spotly['name']} (cat: {spotly['cat']}, perms: {spotly['perms']})")
    log(f"✓ Found Bankly: {bankly['name']} (cat: {bankly['cat']}, perms: {bankly['perms']})")
    log(f"✓ Found Flixo: {flixo['name']} (cat: {flixo['cat']}, perms: {flixo['perms']})")
    
    log("\n✅ TEST 1 PASSED: 12 apps with all required fields verified")
    
    # ========================================================================
    # TEST 2: FILTER BY CATEGORY - GET /api/store/apps?cat=Finance
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 2: FILTER BY CATEGORY - GET /api/store/apps?cat=Finance")
    log("=" * 80)
    
    res = requests.get(f"{BASE_URL}/store/apps?cat=Finance", headers=headers)
    assert res.status_code == 200, f"GET /store/apps?cat=Finance failed: {res.status_code} {res.text}"
    finance_apps = res.json()
    
    log(f"✓ GET /store/apps?cat=Finance returned {len(finance_apps)} apps")
    
    # Verify only Finance category apps
    for app in finance_apps:
        assert app['cat'] == 'Finance', f"App {app['name']} has category {app['cat']}, expected Finance"
    
    # Verify Bankly is in the list
    bankly_found = any(a['id'] == 'bankly' for a in finance_apps)
    assert bankly_found, "Bankly not found in Finance category filter"
    
    log(f"✓ All returned apps are Finance category")
    log(f"✓ Bankly found in Finance filter")
    
    log("\n✅ TEST 2 PASSED: Category filter working correctly")
    
    # ========================================================================
    # TEST 3: FILTER BY SEARCH - GET /api/store/apps?q=music and q=musi
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 3: FILTER BY SEARCH - GET /api/store/apps?q=music and q=musi")
    log("=" * 80)
    
    # Test with full word "music"
    res = requests.get(f"{BASE_URL}/store/apps?q=music", headers=headers)
    assert res.status_code == 200, f"GET /store/apps?q=music failed: {res.status_code} {res.text}"
    music_apps = res.json()
    
    log(f"✓ GET /store/apps?q=music returned {len(music_apps)} apps")
    
    # Verify Spotly is in the results (Musique category)
    spotly_found = any(a['id'] == 'spotly' for a in music_apps)
    assert spotly_found, "Spotly not found in search for 'music'"
    
    log(f"✓ Spotly found in search for 'music'")
    
    # Test with partial word "musi"
    res = requests.get(f"{BASE_URL}/store/apps?q=musi", headers=headers)
    assert res.status_code == 200, f"GET /store/apps?q=musi failed: {res.status_code} {res.text}"
    musi_apps = res.json()
    
    log(f"✓ GET /store/apps?q=musi returned {len(musi_apps)} apps")
    
    # Verify Spotly is in the results
    spotly_found = any(a['id'] == 'spotly' for a in musi_apps)
    assert spotly_found, "Spotly not found in search for 'musi'"
    
    log(f"✓ Spotly found in search for 'musi'")
    
    log("\n✅ TEST 3 PASSED: Search filter working correctly")
    
    # ========================================================================
    # TEST 4: CONNECT - POST /api/store/apps/spotly/connect
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 4: CONNECT - POST /api/store/apps/spotly/connect")
    log("=" * 80)
    
    res = requests.post(f"{BASE_URL}/store/apps/spotly/connect", headers=headers)
    assert res.status_code == 200, f"POST /store/apps/spotly/connect failed: {res.status_code} {res.text}"
    data = res.json()
    
    assert "connection" in data, f"No connection in response: {data}"
    connection = data["connection"]
    
    log(f"✓ Connection created:")
    log(f"  - App ID: {connection.get('appId')}")
    log(f"  - App Name: {connection.get('appName')}")
    log(f"  - Pseudonym: {connection.get('pseudonym')}")
    log(f"  - Scopes: {connection.get('scopes')}")
    
    # Verify pseudonym format: divarc-[0-9a-f]{4}
    pseudonym = connection.get('pseudonym')
    assert pseudonym is not None, "Pseudonym is None"
    
    pseudonym_pattern = r'^divarc-[0-9a-f]{4}$'
    assert re.match(pseudonym_pattern, pseudonym), f"Pseudonym '{pseudonym}' does not match pattern {pseudonym_pattern}"
    
    log(f"✓ Pseudonym matches pattern /^divarc-[0-9a-f]{{4}}$/")
    
    # Verify scopes match app perms
    assert connection.get('scopes') == spotly['perms'], f"Scopes {connection.get('scopes')} do not match app perms {spotly['perms']}"
    
    log(f"✓ Scopes match app permissions: {spotly['perms']}")
    
    # Store pseudonym for later verification
    spotly_pseudonym = pseudonym
    
    log("\n✅ TEST 4 PASSED: Connection created with correct pseudonym format and scopes")
    
    # ========================================================================
    # TEST 5: CONNECTED FLAG - GET /api/store/apps shows Spotly connected
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 5: CONNECTED FLAG - GET /api/store/apps shows Spotly connected:true")
    log("=" * 80)
    
    res = requests.get(f"{BASE_URL}/store/apps", headers=headers)
    assert res.status_code == 200, f"GET /store/apps failed: {res.status_code} {res.text}"
    apps = res.json()
    
    spotly_app = next((a for a in apps if a['id'] == 'spotly'), None)
    assert spotly_app is not None, "Spotly not found in apps list"
    
    log(f"✓ Spotly app:")
    log(f"  - Connected: {spotly_app['connected']}")
    log(f"  - Pseudonym: {spotly_app['pseudonym']}")
    
    assert spotly_app['connected'] == True, f"Spotly should have connected=true, got {spotly_app['connected']}"
    assert spotly_app['pseudonym'] == spotly_pseudonym, f"Spotly pseudonym {spotly_app['pseudonym']} does not match {spotly_pseudonym}"
    
    log(f"✓ Spotly now shows connected=true with pseudonym {spotly_pseudonym}")
    
    log("\n✅ TEST 5 PASSED: Connected flag and pseudonym correctly reflected in apps list")
    
    # ========================================================================
    # TEST 6: IDEMPOTENT - POST /api/store/apps/spotly/connect again
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 6: IDEMPOTENT - POST /api/store/apps/spotly/connect again (should return existing)")
    log("=" * 80)
    
    res = requests.post(f"{BASE_URL}/store/apps/spotly/connect", headers=headers)
    assert res.status_code == 200, f"POST /store/apps/spotly/connect failed: {res.status_code} {res.text}"
    data = res.json()
    
    assert "connection" in data, f"No connection in response: {data}"
    assert "existing" in data, f"No existing flag in response: {data}"
    assert data["existing"] == True, f"Expected existing=true, got {data.get('existing')}"
    
    connection = data["connection"]
    log(f"✓ Connection returned with existing=true")
    log(f"  - Pseudonym: {connection.get('pseudonym')}")
    
    # Verify SAME pseudonym
    assert connection.get('pseudonym') == spotly_pseudonym, f"Pseudonym changed! Expected {spotly_pseudonym}, got {connection.get('pseudonym')}"
    
    log(f"✓ Pseudonym unchanged: {spotly_pseudonym}")
    
    # Verify GET /api/store/connections has exactly 1 entry for spotly
    res = requests.get(f"{BASE_URL}/store/connections", headers=headers)
    assert res.status_code == 200, f"GET /store/connections failed: {res.status_code} {res.text}"
    connections = res.json()
    
    spotly_connections = [c for c in connections if c['appId'] == 'spotly']
    assert len(spotly_connections) == 1, f"Expected exactly 1 spotly connection, got {len(spotly_connections)}"
    
    log(f"✓ GET /store/connections has exactly 1 entry for spotly (no duplicate)")
    
    log("\n✅ TEST 6 PASSED: Idempotent connect - same pseudonym, no duplicate")
    
    # ========================================================================
    # TEST 7: GET /api/store/connections - List connected apps
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 7: GET /api/store/connections - List connected apps")
    log("=" * 80)
    
    res = requests.get(f"{BASE_URL}/store/connections", headers=headers)
    assert res.status_code == 200, f"GET /store/connections failed: {res.status_code} {res.text}"
    connections = res.json()
    
    log(f"✓ GET /store/connections returned {len(connections)} connections")
    
    assert len(connections) >= 1, f"Expected at least 1 connection, got {len(connections)}"
    
    # Verify connection structure
    for conn in connections:
        assert 'appName' in conn, f"Connection missing appName: {conn}"
        assert 'pseudonym' in conn, f"Connection missing pseudonym: {conn}"
        assert 'scopes' in conn, f"Connection missing scopes: {conn}"
        assert 'since' in conn, f"Connection missing since: {conn}"
        
        log(f"  - {conn['appName']}: {conn['pseudonym']} (scopes: {conn['scopes']})")
    
    log(f"✓ All connections have required fields: appName, pseudonym, scopes, since")
    
    log("\n✅ TEST 7 PASSED: Connections list working correctly")
    
    # ========================================================================
    # TEST 8: DISCONNECT - POST /api/store/apps/spotly/disconnect
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 8: DISCONNECT - POST /api/store/apps/spotly/disconnect")
    log("=" * 80)
    
    res = requests.post(f"{BASE_URL}/store/apps/spotly/disconnect", headers=headers)
    assert res.status_code == 200, f"POST /store/apps/spotly/disconnect failed: {res.status_code} {res.text}"
    data = res.json()
    
    assert data.get("ok") == True, f"Expected ok=true, got {data}"
    log(f"✓ Disconnect returned ok=true")
    
    # Verify GET /api/store/apps shows Spotly connected=false
    res = requests.get(f"{BASE_URL}/store/apps", headers=headers)
    assert res.status_code == 200, f"GET /store/apps failed: {res.status_code} {res.text}"
    apps = res.json()
    
    spotly_app = next((a for a in apps if a['id'] == 'spotly'), None)
    assert spotly_app is not None, "Spotly not found in apps list"
    
    log(f"✓ Spotly app after disconnect:")
    log(f"  - Connected: {spotly_app['connected']}")
    log(f"  - Pseudonym: {spotly_app['pseudonym']}")
    
    assert spotly_app['connected'] == False, f"Spotly should have connected=false after disconnect, got {spotly_app['connected']}"
    
    log(f"✓ Spotly now shows connected=false")
    
    # Verify GET /api/store/connections is empty (or doesn't include spotly)
    res = requests.get(f"{BASE_URL}/store/connections", headers=headers)
    assert res.status_code == 200, f"GET /store/connections failed: {res.status_code} {res.text}"
    connections = res.json()
    
    spotly_connections = [c for c in connections if c['appId'] == 'spotly']
    assert len(spotly_connections) == 0, f"Expected 0 spotly connections after disconnect, got {len(spotly_connections)}"
    
    log(f"✓ GET /store/connections no longer includes spotly")
    
    log("\n✅ TEST 8 PASSED: Disconnect working correctly")
    
    # ========================================================================
    # TEST 9: INVALID - POST /api/store/apps/doesnotexist/connect
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 9: INVALID - POST /api/store/apps/doesnotexist/connect (should return 404)")
    log("=" * 80)
    
    res = requests.post(f"{BASE_URL}/store/apps/doesnotexist/connect", headers=headers)
    assert res.status_code == 404, f"Expected 404 for invalid app, got {res.status_code}: {res.text}"
    
    log(f"✓ Correctly returned 404 for non-existent app")
    
    log("\n✅ TEST 9 PASSED: Invalid app returns 404")
    
    # ========================================================================
    # TEST 10: MULTI-USER ISOLATION - Create store6b@divarc.fr
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 10: MULTI-USER ISOLATION - Create store6b@divarc.fr and verify isolation")
    log("=" * 80)
    
    # Create second user
    token_b, user_b = create_user("store6b@divarc.fr", "Store Six B")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    # User B connects to flixo
    log(f"\n[User B] Connecting to flixo")
    res = requests.post(f"{BASE_URL}/store/apps/flixo/connect", headers=headers_b)
    assert res.status_code == 200, f"POST /store/apps/flixo/connect failed: {res.status_code} {res.text}"
    data = res.json()
    
    flixo_pseudonym = data["connection"]["pseudonym"]
    log(f"✓ User B connected to flixo with pseudonym: {flixo_pseudonym}")
    
    # User A (store6) reconnects to spotly for isolation test
    log(f"\n[User A] Reconnecting to spotly")
    res = requests.post(f"{BASE_URL}/store/apps/spotly/connect", headers=headers)
    assert res.status_code == 200, f"POST /store/apps/spotly/connect failed: {res.status_code} {res.text}"
    data = res.json()
    
    spotly_pseudonym_new = data["connection"]["pseudonym"]
    log(f"✓ User A connected to spotly with pseudonym: {spotly_pseudonym_new}")
    
    # Verify User A connections do NOT include flixo
    log(f"\n[User A] Verifying connections do NOT include flixo")
    res = requests.get(f"{BASE_URL}/store/connections", headers=headers)
    assert res.status_code == 200, f"GET /store/connections failed: {res.status_code} {res.text}"
    connections_a = res.json()
    
    flixo_in_a = any(c['appId'] == 'flixo' for c in connections_a)
    assert not flixo_in_a, f"User A should NOT see flixo connection (belongs to User B)"
    
    spotly_in_a = any(c['appId'] == 'spotly' for c in connections_a)
    assert spotly_in_a, f"User A should see spotly connection"
    
    log(f"✓ User A connections: {[c['appName'] for c in connections_a]}")
    log(f"✓ User A does NOT see flixo (User B's connection)")
    
    # Verify User B connections do NOT include spotly
    log(f"\n[User B] Verifying connections do NOT include spotly")
    res = requests.get(f"{BASE_URL}/store/connections", headers=headers_b)
    assert res.status_code == 200, f"GET /store/connections failed: {res.status_code} {res.text}"
    connections_b = res.json()
    
    spotly_in_b = any(c['appId'] == 'spotly' for c in connections_b)
    assert not spotly_in_b, f"User B should NOT see spotly connection (belongs to User A)"
    
    flixo_in_b = any(c['appId'] == 'flixo' for c in connections_b)
    assert flixo_in_b, f"User B should see flixo connection"
    
    log(f"✓ User B connections: {[c['appName'] for c in connections_b]}")
    log(f"✓ User B does NOT see spotly (User A's connection)")
    
    log("\n✅ TEST 10 PASSED: Multi-user isolation working correctly")
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    log("\n" + "=" * 80)
    log("PHASE 6 APP STORE - ALL TESTS PASSED ✅")
    log("=" * 80)
    log("\nSummary:")
    log("  1. ✅ GET /store/apps - 12 seeded apps with all required fields")
    log("  2. ✅ FILTER BY CATEGORY - cat=Finance returns only Finance apps (Bankly)")
    log("  3. ✅ FILTER BY SEARCH - q=music and q=musi both match Spotly (Musique)")
    log("  4. ✅ CONNECT - pseudonym matches /^divarc-[0-9a-f]{4}$/, scopes match perms")
    log("  5. ✅ CONNECTED FLAG - Spotly shows connected:true with pseudonym")
    log("  6. ✅ IDEMPOTENT - reconnect returns existing:true with SAME pseudonym, no duplicate")
    log("  7. ✅ GET /store/connections - lists connected apps with all fields")
    log("  8. ✅ DISCONNECT - Spotly shows connected:false, removed from connections")
    log("  9. ✅ INVALID - non-existent app returns 404")
    log(" 10. ✅ MULTI-USER ISOLATION - User A and User B have independent connections")
    log("\n" + "=" * 80)
    log("NO CRITICAL ISSUES FOUND - ALL APP STORE ENDPOINTS WORKING")
    log("=" * 80)

if __name__ == "__main__":
    try:
        test_phase6_app_store()
        sys.exit(0)
    except AssertionError as e:
        log(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        log(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
