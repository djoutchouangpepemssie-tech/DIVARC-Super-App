#!/usr/bin/env python3
"""
DIVARC Backend Test Suite - PHASE 10: App Store Enriched (36 Real Market Apps)
Tests all App Store endpoints with 36 real market apps and brand logos
"""

import requests
import json
import sys
import re
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://divarc-hub.preview.emergentagent.com/api"
TEST_USER_A = "store10@divarc.fr"
TEST_USER_B = "store10b@divarc.fr"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(msg: str):
    print(f"{Colors.BLUE}[TEST]{Colors.END} {msg}")

def print_pass(msg: str):
    print(f"{Colors.GREEN}✅ PASS{Colors.END} - {msg}")

def print_fail(msg: str):
    print(f"{Colors.RED}❌ FAIL{Colors.END} - {msg}")

def print_info(msg: str):
    print(f"{Colors.YELLOW}ℹ INFO{Colors.END} - {msg}")

class APIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.token: Optional[str] = None
        self.user: Optional[Dict[str, Any]] = None

    def auth_otp_send(self, email: str) -> Dict[str, Any]:
        """Send OTP code"""
        resp = requests.post(f"{self.base_url}/auth/otp/send", json={"email": email})
        return resp.json()

    def auth_otp_verify(self, email: str, code: str) -> Dict[str, Any]:
        """Verify OTP and get token"""
        resp = requests.post(f"{self.base_url}/auth/otp/verify", json={"email": email, "code": code})
        data = resp.json()
        if "token" in data:
            self.token = data["token"]
            self.user = data.get("user")
        return data

    def get(self, path: str, params: Optional[Dict] = None) -> requests.Response:
        """GET request with auth"""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        return requests.get(f"{self.base_url}{path}", headers=headers, params=params or {})

    def post(self, path: str, data: Optional[Dict] = None) -> requests.Response:
        """POST request with auth"""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        return requests.post(f"{self.base_url}{path}", headers=headers, json=data or {})

def authenticate_user(client: APIClient, email: str) -> bool:
    """Authenticate a user via OTP flow"""
    try:
        print_test(f"Authenticating {email}")
        send_resp = client.auth_otp_send(email)
        if not send_resp.get("ok"):
            print_fail(f"OTP send failed for {email}")
            return False
        
        code = send_resp.get("previewCode")
        if not code:
            print_fail(f"No preview code for {email}")
            return False
        
        verify_resp = client.auth_otp_verify(email, code)
        if not verify_resp.get("token"):
            print_fail(f"OTP verify failed for {email}")
            return False
        
        print_pass(f"Authenticated {email} (token: {verify_resp['token'][:20]}...)")
        return True
    except Exception as e:
        print_fail(f"Auth error for {email}: {e}")
        return False

def test_1_get_apps_36_count(client: APIClient) -> bool:
    """Test 1: GET /store/apps returns 37 apps with all required fields"""
    print_test("Test 1: GET /store/apps - verify 37 apps with all required fields")
    try:
        resp = client.get("/store/apps")
        if resp.status_code != 200:
            print_fail(f"Expected 200, got {resp.status_code}")
            return False
        
        apps = resp.json()
        if not isinstance(apps, list):
            print_fail(f"Expected array, got {type(apps)}")
            return False
        
        if len(apps) != 37:
            print_fail(f"Expected 37 apps, got {len(apps)}")
            return False
        
        print_pass(f"Got 37 apps")
        
        # Verify first app has all required fields
        app = apps[0]
        required_fields = ['id', 'name', 'slug', 'color', 'cat', 'logo', 'emoji', 'desc', 'perms', 'featured', 'rating', 'users', 'reviews']
        missing = [f for f in required_fields if f not in app]
        if missing:
            print_fail(f"Missing fields in app: {missing}")
            return False
        
        # Verify color is hex string starting with #
        if not app['color'].startswith('#'):
            print_fail(f"Color should start with #, got: {app['color']}")
            return False
        
        # Verify logo is URL from cdn.simpleicons.org
        if not app['logo'].startswith('https://cdn.simpleicons.org/'):
            print_fail(f"Logo should be from cdn.simpleicons.org, got: {app['logo']}")
            return False
        
        # Verify perms is non-empty array
        if not isinstance(app['perms'], list) or len(app['perms']) == 0:
            print_fail(f"Perms should be non-empty array, got: {app['perms']}")
            return False
        
        # Verify featured is boolean
        if not isinstance(app['featured'], bool):
            print_fail(f"Featured should be boolean, got: {type(app['featured'])}")
            return False
        
        # Verify rating is between 4 and 5
        if not (4 <= app['rating'] <= 5):
            print_fail(f"Rating should be between 4 and 5, got: {app['rating']}")
            return False
        
        # Verify users is a large number
        if not isinstance(app['users'], (int, float)) or app['users'] < 1000000:
            print_fail(f"Users should be a large number (millions), got: {app['users']}")
            return False
        
        # Verify reviews is a number
        if not isinstance(app['reviews'], (int, float)):
            print_fail(f"Reviews should be a number, got: {type(app['reviews'])}")
            return False
        
        print_pass(f"All required fields present and valid in first app: {app['name']}")
        print_info(f"Sample app: {app['name']} ({app['id']}) - {app['cat']} - {app['color']} - {app['logo']}")
        print_info(f"  Perms: {app['perms']}, Featured: {app['featured']}, Rating: {app['rating']}, Users: {app['users']:,}, Reviews: {app['reviews']:,}")
        
        return True
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

def test_2_verify_specific_apps(client: APIClient) -> bool:
    """Test 2: Verify specific apps exist by id"""
    print_test("Test 2: Verify specific apps exist (instagram, tiktok, linkedin, whatsapp, netflix, spotify, uber, youtube, paypal, amazon)")
    try:
        resp = client.get("/store/apps")
        apps = resp.json()
        
        required_ids = ['instagram', 'tiktok', 'linkedin', 'whatsapp', 'netflix', 'spotify', 'uber', 'youtube', 'paypal', 'amazon']
        app_ids = [app['id'] for app in apps]
        
        missing = [id for id in required_ids if id not in app_ids]
        if missing:
            print_fail(f"Missing required apps: {missing}")
            return False
        
        print_pass(f"All 10 required apps found: {', '.join(required_ids)}")
        
        # Print details of each required app
        for app_id in required_ids:
            app = next(a for a in apps if a['id'] == app_id)
            print_info(f"  {app['name']} ({app['id']}) - {app['cat']} - Featured: {app['featured']}")
        
        return True
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

def test_3_verify_sorting_featured_first(client: APIClient) -> bool:
    """Test 3: Verify sorting - featured apps appear first"""
    print_test("Test 3: Verify sorting - featured apps (featured:true) appear before non-featured")
    try:
        resp = client.get("/store/apps")
        apps = resp.json()
        
        # Find the index of the last featured app and first non-featured app
        last_featured_idx = -1
        first_non_featured_idx = -1
        
        for i, app in enumerate(apps):
            if app['featured']:
                last_featured_idx = i
            elif first_non_featured_idx == -1:
                first_non_featured_idx = i
        
        if last_featured_idx == -1:
            print_fail("No featured apps found")
            return False
        
        if first_non_featured_idx == -1:
            print_info("All apps are featured")
            return True
        
        if last_featured_idx >= first_non_featured_idx:
            print_fail(f"Featured apps not sorted first. Last featured at index {last_featured_idx}, first non-featured at {first_non_featured_idx}")
            return False
        
        featured_apps = [app for app in apps if app['featured']]
        featured_ids = [app['id'] for app in featured_apps]
        
        print_pass(f"Featured apps appear first. {len(featured_apps)} featured apps found")
        print_info(f"Featured app IDs: {', '.join(featured_ids)}")
        
        # Verify expected featured apps
        expected_featured = ['instagram', 'tiktok', 'linkedin', 'youtube', 'whatsapp', 'netflix', 'spotify', 'uber']
        for app_id in expected_featured:
            if app_id not in featured_ids:
                print_fail(f"Expected {app_id} to be featured, but it's not")
                return False
        
        print_pass(f"All expected featured apps verified: {', '.join(expected_featured)}")
        
        return True
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

def test_4_filter_cat_social(client: APIClient) -> bool:
    """Test 4: Filter cat=Social returns only Social apps"""
    print_test("Test 4: Filter cat=Social - should include instagram, tiktok, facebook, x, snapchat, pinterest, reddit, threads")
    try:
        resp = client.get("/store/apps", params={"cat": "Social"})
        apps = resp.json()
        
        # Verify all apps have cat='Social'
        non_social = [app['id'] for app in apps if app['cat'] != 'Social']
        if non_social:
            print_fail(f"Non-Social apps in results: {non_social}")
            return False
        
        app_ids = [app['id'] for app in apps]
        expected_social = ['instagram', 'tiktok', 'facebook', 'x', 'snapchat', 'pinterest', 'reddit', 'threads']
        
        missing = [id for id in expected_social if id not in app_ids]
        if missing:
            print_fail(f"Missing expected Social apps: {missing}")
            return False
        
        print_pass(f"Filter cat=Social works. Found {len(apps)} Social apps including: {', '.join(expected_social)}")
        
        return True
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

def test_5_filter_cat_messagerie(client: APIClient) -> bool:
    """Test 5: Filter cat=Messagerie"""
    print_test("Test 5: Filter cat=Messagerie - should include whatsapp, telegram, messenger, signal, discord")
    try:
        resp = client.get("/store/apps", params={"cat": "Messagerie"})
        apps = resp.json()
        
        app_ids = [app['id'] for app in apps]
        expected = ['whatsapp', 'telegram', 'messenger', 'signal', 'discord']
        
        missing = [id for id in expected if id not in app_ids]
        if missing:
            print_fail(f"Missing expected Messagerie apps: {missing}")
            return False
        
        print_pass(f"Filter cat=Messagerie works. Found {len(apps)} apps including: {', '.join(expected)}")
        
        return True
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

def test_6_filter_cat_finance(client: APIClient) -> bool:
    """Test 6: Filter cat=Finance"""
    print_test("Test 6: Filter cat=Finance - should include paypal, revolut, coinbase")
    try:
        resp = client.get("/store/apps", params={"cat": "Finance"})
        apps = resp.json()
        
        app_ids = [app['id'] for app in apps]
        expected = ['paypal', 'revolut', 'coinbase']
        
        missing = [id for id in expected if id not in app_ids]
        if missing:
            print_fail(f"Missing expected Finance apps: {missing}")
            return False
        
        print_pass(f"Filter cat=Finance works. Found {len(apps)} apps including: {', '.join(expected)}")
        
        return True
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

def test_7_search_linked(client: APIClient) -> bool:
    """Test 7: Search q=linked matches LinkedIn"""
    print_test("Test 7: Search q=linked - should match LinkedIn")
    try:
        resp = client.get("/store/apps", params={"q": "linked"})
        apps = resp.json()
        
        app_ids = [app['id'] for app in apps]
        if 'linkedin' not in app_ids:
            print_fail(f"LinkedIn not found in search results for q=linked. Found: {app_ids}")
            return False
        
        print_pass(f"Search q=linked matches LinkedIn. Found {len(apps)} apps")
        
        return True
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

def test_8_search_net(client: APIClient) -> bool:
    """Test 8: Search q=net matches Netflix"""
    print_test("Test 8: Search q=net - should match Netflix (and maybe others by desc)")
    try:
        resp = client.get("/store/apps", params={"q": "net"})
        apps = resp.json()
        
        app_ids = [app['id'] for app in apps]
        if 'netflix' not in app_ids:
            print_fail(f"Netflix not found in search results for q=net. Found: {app_ids}")
            return False
        
        print_pass(f"Search q=net matches Netflix. Found {len(apps)} apps: {', '.join(app_ids)}")
        
        return True
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

def test_9_connect_instagram(client: APIClient) -> Dict[str, Any]:
    """Test 9: Connect instagram - verify pseudonym and scopes"""
    print_test("Test 9: POST /store/apps/instagram/connect - verify pseudonym divarc-xxxx and scopes")
    try:
        resp = client.post("/store/apps/instagram/connect")
        if resp.status_code != 200:
            print_fail(f"Expected 200, got {resp.status_code}: {resp.text}")
            return {}
        
        data = resp.json()
        if 'connection' not in data:
            print_fail(f"No connection in response: {data}")
            return {}
        
        conn = data['connection']
        
        # Verify pseudonym matches pattern divarc-xxxx
        pseudonym = conn.get('pseudonym', '')
        if not re.match(r'^divarc-[0-9a-f]{4}$', pseudonym):
            print_fail(f"Pseudonym doesn't match pattern divarc-xxxx: {pseudonym}")
            return {}
        
        # Verify scopes match instagram perms (Social category)
        expected_scopes = ['Profil', 'Photos', 'Contacts']
        if conn.get('scopes') != expected_scopes:
            print_fail(f"Expected scopes {expected_scopes}, got {conn.get('scopes')}")
            return {}
        
        print_pass(f"Connected to instagram with pseudonym {pseudonym} and scopes {expected_scopes}")
        
        return conn
    except Exception as e:
        print_fail(f"Exception: {e}")
        return {}

def test_10_verify_connected_flag(client: APIClient, expected_pseudonym: str) -> bool:
    """Test 10: Verify instagram shows connected:true with pseudonym"""
    print_test("Test 10: GET /store/apps - verify instagram shows connected:true with pseudonym")
    try:
        resp = client.get("/store/apps")
        apps = resp.json()
        
        instagram = next((app for app in apps if app['id'] == 'instagram'), None)
        if not instagram:
            print_fail("Instagram not found in apps list")
            return False
        
        if not instagram.get('connected'):
            print_fail(f"Instagram connected flag is False, expected True")
            return False
        
        if instagram.get('pseudonym') != expected_pseudonym:
            print_fail(f"Instagram pseudonym mismatch. Expected {expected_pseudonym}, got {instagram.get('pseudonym')}")
            return False
        
        print_pass(f"Instagram shows connected:true with pseudonym {expected_pseudonym}")
        
        return True
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

def test_11_idempotent_connect(client: APIClient, expected_pseudonym: str) -> bool:
    """Test 11: Connect instagram again - should return existing:true with same pseudonym"""
    print_test("Test 11: POST /store/apps/instagram/connect again - verify idempotent (existing:true, same pseudonym)")
    try:
        resp = client.post("/store/apps/instagram/connect")
        data = resp.json()
        
        if not data.get('existing'):
            print_fail(f"Expected existing:true, got {data}")
            return False
        
        conn = data.get('connection', {})
        if conn.get('pseudonym') != expected_pseudonym:
            print_fail(f"Pseudonym changed! Expected {expected_pseudonym}, got {conn.get('pseudonym')}")
            return False
        
        print_pass(f"Idempotent connect verified: existing:true with same pseudonym {expected_pseudonym}")
        
        # Verify GET /store/connections has exactly 1 entry
        resp = client.get("/store/connections")
        conns = resp.json()
        if len(conns) != 1:
            print_fail(f"Expected exactly 1 connection, got {len(conns)}")
            return False
        
        print_pass(f"GET /store/connections has exactly 1 entry (no duplicate)")
        
        return True
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

def test_12_disconnect_instagram(client: APIClient) -> bool:
    """Test 12: Disconnect instagram"""
    print_test("Test 12: POST /store/apps/instagram/disconnect - verify connected:false and removed from connections")
    try:
        resp = client.post("/store/apps/instagram/disconnect")
        data = resp.json()
        
        if not data.get('ok'):
            print_fail(f"Disconnect failed: {data}")
            return False
        
        print_pass("Disconnected instagram")
        
        # Verify instagram shows connected:false
        resp = client.get("/store/apps")
        apps = resp.json()
        instagram = next((app for app in apps if app['id'] == 'instagram'), None)
        
        if instagram.get('connected'):
            print_fail(f"Instagram still shows connected:true after disconnect")
            return False
        
        print_pass("Instagram shows connected:false")
        
        # Verify removed from connections
        resp = client.get("/store/connections")
        conns = resp.json()
        if len(conns) != 0:
            print_fail(f"Expected 0 connections after disconnect, got {len(conns)}")
            return False
        
        print_pass("Instagram removed from /store/connections")
        
        return True
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

def test_13_invalid_app(client: APIClient) -> bool:
    """Test 13: Connect to non-existent app returns 404"""
    print_test("Test 13: POST /store/apps/doesnotexist/connect - should return 404")
    try:
        resp = client.post("/store/apps/doesnotexist/connect")
        if resp.status_code != 404:
            print_fail(f"Expected 404, got {resp.status_code}")
            return False
        
        print_pass("Invalid app returns 404")
        
        return True
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

def test_14_multi_user_isolation(client_a: APIClient, client_b: APIClient) -> bool:
    """Test 14: Multi-user isolation - each user has independent connections"""
    print_test("Test 14: Multi-user isolation - store10 connects spotify, store10b connects netflix")
    try:
        # User A connects to spotify
        resp_a = client_a.post("/store/apps/spotify/connect")
        if resp_a.status_code != 200:
            print_fail(f"User A spotify connect failed: {resp_a.status_code}")
            return False
        
        conn_a = resp_a.json().get('connection', {})
        pseudonym_a = conn_a.get('pseudonym', '')
        print_pass(f"User A connected to spotify with pseudonym {pseudonym_a}")
        
        # User B connects to netflix
        resp_b = client_b.post("/store/apps/netflix/connect")
        if resp_b.status_code != 200:
            print_fail(f"User B netflix connect failed: {resp_b.status_code}")
            return False
        
        conn_b = resp_b.json().get('connection', {})
        pseudonym_b = conn_b.get('pseudonym', '')
        print_pass(f"User B connected to netflix with pseudonym {pseudonym_b}")
        
        # Verify different pseudonyms
        if pseudonym_a == pseudonym_b:
            print_fail(f"Pseudonyms should be different, both are {pseudonym_a}")
            return False
        
        print_pass(f"Different pseudonyms generated: {pseudonym_a} vs {pseudonym_b}")
        
        # Verify User A sees only spotify
        resp_a = client_a.get("/store/connections")
        conns_a = resp_a.json()
        if len(conns_a) != 1:
            print_fail(f"User A should have 1 connection, got {len(conns_a)}")
            return False
        if conns_a[0].get('appId') != 'spotify':
            print_fail(f"User A should be connected to spotify, got {conns_a[0].get('appId')}")
            return False
        
        print_pass(f"User A sees only their own connection (spotify)")
        
        # Verify User B sees only netflix
        resp_b = client_b.get("/store/connections")
        conns_b = resp_b.json()
        if len(conns_b) != 1:
            print_fail(f"User B should have 1 connection, got {len(conns_b)}")
            return False
        if conns_b[0].get('appId') != 'netflix':
            print_fail(f"User B should be connected to netflix, got {conns_b[0].get('appId')}")
            return False
        
        print_pass(f"User B sees only their own connection (netflix)")
        
        return True
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

def test_15_auth_required(client: APIClient) -> bool:
    """Test 15: GET /store/apps without Bearer returns 401"""
    print_test("Test 15: GET /store/apps without Bearer - should return 401")
    try:
        # Create client without token
        unauth_client = APIClient(BASE_URL)
        resp = unauth_client.get("/store/apps")
        
        if resp.status_code != 401:
            print_fail(f"Expected 401, got {resp.status_code}")
            return False
        
        print_pass("GET /store/apps without Bearer returns 401")
        
        return True
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

def main():
    print("\n" + "="*80)
    print("DIVARC BACKEND TEST SUITE - PHASE 10: App Store Enriched (36 Real Market Apps)")
    print("="*80 + "\n")
    
    # Initialize clients
    client_a = APIClient(BASE_URL)
    client_b = APIClient(BASE_URL)
    
    # Authenticate users
    if not authenticate_user(client_a, TEST_USER_A):
        print_fail("Failed to authenticate User A")
        sys.exit(1)
    
    if not authenticate_user(client_b, TEST_USER_B):
        print_fail("Failed to authenticate User B")
        sys.exit(1)
    
    print("\n" + "-"*80)
    print("RUNNING TESTS")
    print("-"*80 + "\n")
    
    results = []
    
    # Test 1: GET /store/apps - 37 apps with all fields
    results.append(("Test 1: GET /store/apps (37 apps, all fields)", test_1_get_apps_36_count(client_a)))
    
    # Test 2: Verify specific apps exist
    results.append(("Test 2: Verify specific apps exist", test_2_verify_specific_apps(client_a)))
    
    # Test 3: Verify sorting (featured first)
    results.append(("Test 3: Verify sorting (featured first)", test_3_verify_sorting_featured_first(client_a)))
    
    # Test 4: Filter cat=Social
    results.append(("Test 4: Filter cat=Social", test_4_filter_cat_social(client_a)))
    
    # Test 5: Filter cat=Messagerie
    results.append(("Test 5: Filter cat=Messagerie", test_5_filter_cat_messagerie(client_a)))
    
    # Test 6: Filter cat=Finance
    results.append(("Test 6: Filter cat=Finance", test_6_filter_cat_finance(client_a)))
    
    # Test 7: Search q=linked
    results.append(("Test 7: Search q=linked", test_7_search_linked(client_a)))
    
    # Test 8: Search q=net
    results.append(("Test 8: Search q=net", test_8_search_net(client_a)))
    
    # Test 9: Connect instagram
    conn = test_9_connect_instagram(client_a)
    results.append(("Test 9: Connect instagram", bool(conn)))
    pseudonym_a = conn.get('pseudonym', '') if conn else ''
    
    # Test 10: Verify connected flag
    if pseudonym_a:
        results.append(("Test 10: Verify connected flag", test_10_verify_connected_flag(client_a, pseudonym_a)))
    else:
        results.append(("Test 10: Verify connected flag", False))
    
    # Test 11: Idempotent connect
    if pseudonym_a:
        results.append(("Test 11: Idempotent connect", test_11_idempotent_connect(client_a, pseudonym_a)))
    else:
        results.append(("Test 11: Idempotent connect", False))
    
    # Test 12: Disconnect
    results.append(("Test 12: Disconnect instagram", test_12_disconnect_instagram(client_a)))
    
    # Test 13: Invalid app
    results.append(("Test 13: Invalid app (404)", test_13_invalid_app(client_a)))
    
    # Test 14: Multi-user isolation (run after disconnect to avoid interference)
    results.append(("Test 14: Multi-user isolation", test_14_multi_user_isolation(client_a, client_b)))
    
    # Test 15: Auth required
    results.append(("Test 15: Auth required (401)", test_15_auth_required(client_a)))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80 + "\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.END}" if result else f"{Colors.RED}❌ FAIL{Colors.END}"
        print(f"{status} - {test_name}")
    
    print(f"\n{Colors.BLUE}Total: {passed}/{total} tests passed{Colors.END}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}🎉 ALL TESTS PASSED!{Colors.END}\n")
        
        # Print final report
        print("="*80)
        print("PHASE 10 REPORT")
        print("="*80)
        print(f"✅ Total app count: 37")
        print(f"✅ Featured apps: instagram, tiktok, linkedin, youtube, whatsapp, netflix, spotify, uber")
        print(f"✅ Pseudonyms generated: {pseudonym_a} (User A)")
        print(f"✅ All filters working: cat=Social, cat=Messagerie, cat=Finance")
        print(f"✅ Search working: q=linked, q=net")
        print(f"✅ Connect/disconnect working with idempotency")
        print(f"✅ Multi-user isolation verified")
        print(f"✅ Auth required (401 without Bearer)")
        print("="*80 + "\n")
        
        sys.exit(0)
    else:
        print(f"\n{Colors.RED}❌ {total - passed} test(s) failed{Colors.END}\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
