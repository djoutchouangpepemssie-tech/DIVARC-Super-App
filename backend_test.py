#!/usr/bin/env python3
"""
DIVARC Marketplace Backend Test Suite - PHASE 4
Tests all marketplace endpoints: listings, filters, create, favorite, buy, mine
"""
import requests
import json
import sys

# Base URL from environment
BASE_URL = "https://divarc-hub.preview.emergentagent.com/api"

def print_test(num, desc):
    print(f"\n{'='*80}")
    print(f"TEST {num}: {desc}")
    print('='*80)

def print_pass(msg):
    print(f"✅ PASS: {msg}")

def print_fail(msg):
    print(f"❌ FAIL: {msg}")
    
def print_info(msg):
    print(f"ℹ️  INFO: {msg}")

# Auth helper
def auth_user(email, name=None):
    """Authenticate user via OTP preview mode"""
    # Send OTP
    r = requests.post(f"{BASE_URL}/auth/otp/send", json={"email": email})
    if r.status_code != 200:
        print_fail(f"OTP send failed: {r.status_code} {r.text}")
        return None
    data = r.json()
    code = data.get('previewCode')
    if not code:
        print_fail("No preview code returned")
        return None
    
    # Verify OTP
    payload = {"email": email, "code": code}
    if name:
        payload["name"] = name
    r = requests.post(f"{BASE_URL}/auth/otp/verify", json=payload)
    if r.status_code != 200:
        print_fail(f"OTP verify failed: {r.status_code} {r.text}")
        return None
    data = r.json()
    return data.get('token')

def get_wallet_balance(token):
    """Get current wallet balance"""
    r = requests.get(f"{BASE_URL}/wallet", headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        return None
    return r.json().get('balanceCents')

def main():
    print("\n" + "="*80)
    print("DIVARC MARKETPLACE BACKEND TEST SUITE - PHASE 4")
    print("="*80)
    
    # Setup: Create BUYER user (buyer4@divarc.fr with wallet 480000c)
    print_test("SETUP", "Create BUYER user buyer4@divarc.fr")
    buyer_token = auth_user("buyer4@divarc.fr", "Buyer Four")
    if not buyer_token:
        print_fail("Failed to create buyer user")
        sys.exit(1)
    print_pass(f"Buyer authenticated, token: {buyer_token[:20]}...")
    
    buyer_balance = get_wallet_balance(buyer_token)
    print_info(f"Buyer wallet balance: {buyer_balance} cents")
    if buyer_balance != 480000:
        print_fail(f"Expected 480000 cents, got {buyer_balance}")
        sys.exit(1)
    print_pass("Buyer wallet has 480000 cents (480000c)")
    
    headers_buyer = {"Authorization": f"Bearer {buyer_token}"}
    
    # Setup: Create SELLER user (seller4@divarc.fr)
    print_test("SETUP", "Create SELLER user seller4@divarc.fr")
    seller_token = auth_user("seller4@divarc.fr", "Seller Four")
    if not seller_token:
        print_fail("Failed to create seller user")
        sys.exit(1)
    print_pass(f"Seller authenticated, token: {seller_token[:20]}...")
    
    seller_balance = get_wallet_balance(seller_token)
    print_info(f"Seller wallet balance: {seller_balance} cents")
    if seller_balance != 480000:
        print_fail(f"Expected 480000 cents, got {seller_balance}")
        sys.exit(1)
    print_pass("Seller wallet has 480000 cents (480000c)")
    
    headers_seller = {"Authorization": f"Bearer {seller_token}"}
    
    # TEST 1: GET /api/market/listings -> array of 6 seeded listings
    print_test(1, "GET /api/market/listings - verify 6 seeded listings")
    try:
        r = requests.get(f"{BASE_URL}/market/listings", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
            sys.exit(1)
        
        listings = r.json()
        print_info(f"Received {len(listings)} listings")
        
        if len(listings) != 6:
            print_fail(f"Expected 6 seeded listings, got {len(listings)}")
        else:
            print_pass("Received 6 seeded listings")
        
        # Verify first listing structure
        if listings:
            listing = listings[0]
            required_fields = ['id', 'sellerId', 'title', 'description', 'priceCents', 'category', 
                             'condition', 'type', 'images', 'location', 'status', 'favorites', 
                             'views', 'favorited', 'seller']
            missing = [f for f in required_fields if f not in listing]
            if missing:
                print_fail(f"Missing fields in listing: {missing}")
            else:
                print_pass("All required fields present in listing")
            
            # Verify seller structure
            if 'seller' in listing and listing['seller']:
                seller = listing['seller']
                seller_fields = ['name', 'handle', 'verified']
                missing_seller = [f for f in seller_fields if f not in seller]
                if missing_seller:
                    print_fail(f"Missing seller fields: {missing_seller}")
                else:
                    print_pass(f"Seller info complete: {seller['name']} ({seller['handle']}) verified={seller['verified']}")
            
            # Verify images non-empty
            if 'images' in listing and len(listing['images']) > 0:
                print_pass(f"Images array non-empty: {len(listing['images'])} image(s)")
            else:
                print_fail("Images array is empty")
            
            # Verify favorited is false initially
            if listing.get('favorited') == False:
                print_pass("favorited: false (initial state)")
            else:
                print_fail(f"Expected favorited=false, got {listing.get('favorited')}")
            
            # Verify status is active
            if listing.get('status') == 'active':
                print_pass("status: 'active'")
            else:
                print_fail(f"Expected status='active', got {listing.get('status')}")
            
            print_info(f"Sample listing: {listing['title']} - {listing['priceCents']}c - {listing['category']}")
    
    except Exception as e:
        print_fail(f"Exception: {e}")
        sys.exit(1)
    
    # TEST 2: Filters - category, search, sorting
    print_test(2, "GET /api/market/listings with filters")
    
    # 2a: Category filter (Tech)
    print_info("Testing category filter: cat=Tech")
    try:
        r = requests.get(f"{BASE_URL}/market/listings?cat=Tech", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            tech_listings = r.json()
            print_info(f"Tech category: {len(tech_listings)} listing(s)")
            # Verify all are Tech category
            non_tech = [l for l in tech_listings if l.get('category') != 'Tech']
            if non_tech:
                print_fail(f"Found {len(non_tech)} non-Tech listings in Tech filter")
            else:
                print_pass(f"Category filter working: all {len(tech_listings)} listings are Tech")
                if tech_listings:
                    print_info(f"Tech listing: {tech_listings[0]['title']}")
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # 2b: Search query (velo or vélo)
    print_info("Testing search query: q=velo")
    try:
        r = requests.get(f"{BASE_URL}/market/listings?q=velo", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            velo_listings = r.json()
            print_info(f"Search 'velo': {len(velo_listings)} listing(s)")
            if len(velo_listings) > 0:
                print_pass(f"Search query working: found {len(velo_listings)} listing(s) matching 'velo'")
                print_info(f"Matched: {velo_listings[0]['title']}")
            else:
                print_fail("Expected at least 1 listing matching 'velo' (Vélo de ville)")
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # Test with accent: vélo
    print_info("Testing search query: q=vélo")
    try:
        r = requests.get(f"{BASE_URL}/market/listings?q=vélo", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            velo_listings2 = r.json()
            print_info(f"Search 'vélo': {len(velo_listings2)} listing(s)")
            if len(velo_listings2) > 0:
                print_pass(f"Search with accent working: found {len(velo_listings2)} listing(s)")
            else:
                print_fail("Expected at least 1 listing matching 'vélo'")
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # 2c: Sorting - price_asc
    print_info("Testing sort: price_asc")
    try:
        r = requests.get(f"{BASE_URL}/market/listings?sort=price_asc", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            sorted_asc = r.json()
            prices_asc = [l['priceCents'] for l in sorted_asc]
            print_info(f"Prices ascending: {prices_asc}")
            # Verify ascending order
            is_sorted_asc = all(prices_asc[i] <= prices_asc[i+1] for i in range(len(prices_asc)-1))
            if is_sorted_asc:
                print_pass(f"Sort price_asc working: {prices_asc[0]}c -> {prices_asc[-1]}c")
            else:
                print_fail(f"Prices not in ascending order: {prices_asc}")
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # 2d: Sorting - price_desc
    print_info("Testing sort: price_desc")
    try:
        r = requests.get(f"{BASE_URL}/market/listings?sort=price_desc", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            sorted_desc = r.json()
            prices_desc = [l['priceCents'] for l in sorted_desc]
            print_info(f"Prices descending: {prices_desc}")
            # Verify descending order
            is_sorted_desc = all(prices_desc[i] >= prices_desc[i+1] for i in range(len(prices_desc)-1))
            if is_sorted_desc:
                print_pass(f"Sort price_desc working: {prices_desc[0]}c -> {prices_desc[-1]}c")
            else:
                print_fail(f"Prices not in descending order: {prices_desc}")
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # TEST 3: CREATE listing as seller
    print_test(3, "POST /api/market/listings - create listing as seller")
    guitare_id = None
    try:
        new_listing = {
            "title": "Guitare",
            "description": "nickel",
            "priceCents": 5000,
            "category": "Autre",
            "condition": "Bon état",
            "type": "item",
            "emoji": "🎸",
            "location": "Paris"
        }
        r = requests.post(f"{BASE_URL}/market/listings", json=new_listing, headers=headers_seller)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
            sys.exit(1)
        
        created = r.json()
        guitare_id = created.get('id')
        print_info(f"Created listing ID: {guitare_id}")
        
        # Verify fields
        if created.get('title') == 'Guitare':
            print_pass("Title: 'Guitare'")
        else:
            print_fail(f"Expected title 'Guitare', got {created.get('title')}")
        
        if created.get('priceCents') == 5000:
            print_pass("priceCents: 5000")
        else:
            print_fail(f"Expected priceCents 5000, got {created.get('priceCents')}")
        
        # Verify sellerId matches seller
        r_me = requests.get(f"{BASE_URL}/auth/me", headers=headers_seller)
        if r_me.status_code == 200:
            seller_user = r_me.json()
            if created.get('sellerId') == seller_user.get('id'):
                print_pass(f"sellerId matches seller: {seller_user.get('handle')}")
            else:
                print_fail(f"sellerId mismatch: {created.get('sellerId')} != {seller_user.get('id')}")
        
        # Verify it appears in GET /api/market/listings
        r = requests.get(f"{BASE_URL}/market/listings", headers=headers_buyer)
        if r.status_code == 200:
            all_listings = r.json()
            guitare_in_list = any(l.get('id') == guitare_id for l in all_listings)
            if guitare_in_list:
                print_pass("Created listing appears in GET /api/market/listings")
            else:
                print_fail("Created listing NOT found in GET /api/market/listings")
        
    except Exception as e:
        print_fail(f"Exception: {e}")
        sys.exit(1)
    
    # TEST 4: FAVORITE toggle as buyer
    print_test(4, "POST /api/market/listings/:id/favorite - toggle favorite")
    
    # Pick a listing (use first from seeded listings)
    try:
        r = requests.get(f"{BASE_URL}/market/listings", headers=headers_buyer)
        listings = r.json()
        if not listings:
            print_fail("No listings available for favorite test")
            sys.exit(1)
        
        test_listing = listings[0]
        listing_id = test_listing['id']
        print_info(f"Testing favorite on listing: {test_listing['title']} (ID: {listing_id})")
        
        # First favorite (should set favorited=true)
        r = requests.post(f"{BASE_URL}/market/listings/{listing_id}/favorite", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            fav_result = r.json()
            if fav_result.get('favorited') == True:
                print_pass(f"First favorite: favorited=true, favorites={fav_result.get('favorites')}")
                initial_fav_count = fav_result.get('favorites')
            else:
                print_fail(f"Expected favorited=true, got {fav_result.get('favorited')}")
        
        # Second favorite (should toggle to favorited=false)
        r = requests.post(f"{BASE_URL}/market/listings/{listing_id}/favorite", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            unfav_result = r.json()
            if unfav_result.get('favorited') == False:
                print_pass(f"Second favorite (toggle): favorited=false, favorites={unfav_result.get('favorites')}")
                # Verify count decreased
                if unfav_result.get('favorites') == initial_fav_count - 1:
                    print_pass("Favorites count decreased by 1")
                else:
                    print_fail(f"Expected favorites={initial_fav_count-1}, got {unfav_result.get('favorites')}")
            else:
                print_fail(f"Expected favorited=false, got {unfav_result.get('favorited')}")
    
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # TEST 5: DETAIL view with views increment
    print_test(5, "GET /api/market/listings/:id - detail view with views increment")
    try:
        # Get initial views count
        r = requests.get(f"{BASE_URL}/market/listings/{listing_id}", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            detail1 = r.json()
            views1 = detail1.get('views', 0)
            print_info(f"Initial views: {views1}")
            print_pass(f"Detail view returned listing with seller info")
            
            # View again to increment
            r = requests.get(f"{BASE_URL}/market/listings/{listing_id}", headers=headers_buyer)
            if r.status_code == 200:
                detail2 = r.json()
                views2 = detail2.get('views', 0)
                print_info(f"After second view: {views2}")
                if views2 == views1 + 1:
                    print_pass(f"Views incremented correctly: {views1} -> {views2}")
                else:
                    print_fail(f"Views not incremented correctly: {views1} -> {views2}")
    
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # TEST 6: BUY - CRITICAL money flow test
    print_test(6, "POST /api/market/listings/:id/buy - CRITICAL money flow")
    
    if not guitare_id:
        print_fail("Guitare listing ID not available, skipping buy test")
        sys.exit(1)
    
    try:
        # Record buyer balance B0
        B0 = get_wallet_balance(buyer_token)
        print_info(f"Buyer balance BEFORE: {B0}c")
        
        # Record seller balance S0
        S0 = get_wallet_balance(seller_token)
        print_info(f"Seller balance BEFORE: {S0}c")
        
        # Buy the Guitare (priceCents 5000)
        r = requests.post(f"{BASE_URL}/market/listings/{guitare_id}/buy", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Buy failed: {r.status_code} {r.text}")
            sys.exit(1)
        
        buy_result = r.json()
        print_info(f"Buy result: {buy_result}")
        
        # Verify ok: true
        if buy_result.get('ok') == True:
            print_pass("Buy response: ok=true")
        else:
            print_fail(f"Expected ok=true, got {buy_result.get('ok')}")
        
        # Verify buyer balance decreased by 5000
        buyer_balance_after = buy_result.get('balanceCents')
        expected_buyer_balance = B0 - 5000
        if buyer_balance_after == expected_buyer_balance:
            print_pass(f"Buyer balance: {B0}c -> {buyer_balance_after}c (-5000c) ✓")
        else:
            print_fail(f"Buyer balance incorrect: expected {expected_buyer_balance}c, got {buyer_balance_after}c")
        
        # Verify buyer transaction created
        r = requests.get(f"{BASE_URL}/transactions", headers=headers_buyer)
        if r.status_code == 200:
            buyer_txs = r.json()
            marketplace_tx = next((tx for tx in buyer_txs if tx.get('category') == 'Marketplace' and tx.get('amountCents') == -5000), None)
            if marketplace_tx:
                print_pass(f"Buyer transaction created: category='Marketplace', amount=-5000c, label='{marketplace_tx.get('label')}'")
            else:
                print_fail("Buyer Marketplace transaction not found")
        
        # Verify seller wallet increased by 5000
        S1 = get_wallet_balance(seller_token)
        expected_seller_balance = S0 + 5000
        if S1 == expected_seller_balance:
            print_pass(f"Seller balance: {S0}c -> {S1}c (+5000c) ✓")
        else:
            print_fail(f"Seller balance incorrect: expected {expected_seller_balance}c, got {S1}c")
        
        # Verify listing status now 'sold'
        r = requests.get(f"{BASE_URL}/market/listings/{guitare_id}", headers=headers_buyer)
        if r.status_code == 200:
            listing_detail = r.json()
            if listing_detail.get('status') == 'sold':
                print_pass("Listing status: 'sold' ✓")
            else:
                print_fail(f"Expected status='sold', got {listing_detail.get('status')}")
        
        # Try buying it AGAIN -> should return 410 'Déjà vendu'
        r = requests.post(f"{BASE_URL}/market/listings/{guitare_id}/buy", headers=headers_buyer)
        if r.status_code == 410:
            error_msg = r.json().get('error', '')
            if 'Déjà vendu' in error_msg or 'vendu' in error_msg.lower():
                print_pass(f"Buying again returns 410: '{error_msg}' ✓")
            else:
                print_fail(f"Expected 'Déjà vendu' error, got: {error_msg}")
        else:
            print_fail(f"Expected status 410, got {r.status_code}")
    
    except Exception as e:
        print_fail(f"Exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # TEST 7: OWN LISTING - seller cannot buy their own listing
    print_test(7, "POST /api/market/listings/:id/buy - cannot buy own listing")
    
    try:
        # Create another listing as seller
        new_listing2 = {
            "title": "Piano numérique",
            "description": "88 touches, excellent état",
            "priceCents": 25000,
            "category": "Musique",
            "condition": "Très bon état",
            "type": "item",
            "emoji": "🎹",
            "location": "Lyon"
        }
        r = requests.post(f"{BASE_URL}/market/listings", json=new_listing2, headers=headers_seller)
        if r.status_code != 200:
            print_fail(f"Failed to create second listing: {r.status_code} {r.text}")
        else:
            piano_listing = r.json()
            piano_id = piano_listing.get('id')
            print_info(f"Created second listing: {piano_listing['title']} (ID: {piano_id})")
            
            # Seller tries to buy their own listing
            r = requests.post(f"{BASE_URL}/market/listings/{piano_id}/buy", headers=headers_seller)
            if r.status_code == 400:
                error_msg = r.json().get('error', '')
                if 'propre' in error_msg.lower() or 'own' in error_msg.lower():
                    print_pass(f"Seller cannot buy own listing: 400 '{error_msg}' ✓")
                else:
                    print_fail(f"Expected 'cannot buy own' error, got: {error_msg}")
            else:
                print_fail(f"Expected status 400, got {r.status_code}: {r.text}")
    
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # TEST 8: INSUFFICIENT balance
    print_test(8, "POST /api/market/listings/:id/buy - insufficient balance (402)")
    
    try:
        # Create an expensive listing as seller
        expensive_listing = {
            "title": "Voiture de collection",
            "description": "Très rare",
            "priceCents": 99999999,
            "category": "Auto",
            "condition": "Bon état",
            "type": "item",
            "emoji": "🚗",
            "location": "Monaco"
        }
        r = requests.post(f"{BASE_URL}/market/listings", json=expensive_listing, headers=headers_seller)
        if r.status_code != 200:
            print_fail(f"Failed to create expensive listing: {r.status_code} {r.text}")
        else:
            expensive = r.json()
            expensive_id = expensive.get('id')
            print_info(f"Created expensive listing: {expensive['title']} - {expensive['priceCents']}c")
            
            # Buyer tries to buy (should fail with 402)
            r = requests.post(f"{BASE_URL}/market/listings/{expensive_id}/buy", headers=headers_buyer)
            if r.status_code == 402:
                error_msg = r.json().get('error', '')
                print_pass(f"Insufficient balance returns 402: '{error_msg}' ✓")
            else:
                print_fail(f"Expected status 402, got {r.status_code}: {r.text}")
    
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # TEST 9: MINE - buyer purchases and seller listings
    print_test(9, "GET /api/market/mine - buyer purchases and seller listings")
    
    try:
        # Buyer GET /api/market/mine
        r = requests.get(f"{BASE_URL}/market/mine", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Buyer mine failed: {r.status_code} {r.text}")
        else:
            buyer_mine = r.json()
            purchases = buyer_mine.get('purchases', [])
            print_info(f"Buyer purchases: {len(purchases)}")
            
            # Verify Guitare is in purchases
            guitare_purchase = next((p for p in purchases if p.get('listingId') == guitare_id), None)
            if guitare_purchase:
                print_pass(f"Buyer purchases includes Guitare: {guitare_purchase.get('title')} - {guitare_purchase.get('priceCents')}c ✓")
            else:
                print_fail("Guitare not found in buyer purchases")
        
        # Seller GET /api/market/mine
        r = requests.get(f"{BASE_URL}/market/mine", headers=headers_seller)
        if r.status_code != 200:
            print_fail(f"Seller mine failed: {r.status_code} {r.text}")
        else:
            seller_mine = r.json()
            selling = seller_mine.get('selling', [])
            print_info(f"Seller listings: {len(selling)}")
            
            # Verify Guitare is in selling and marked sold
            guitare_selling = next((l for l in selling if l.get('id') == guitare_id), None)
            if guitare_selling:
                if guitare_selling.get('status') == 'sold':
                    print_pass(f"Seller listings includes Guitare marked 'sold' ✓")
                else:
                    print_fail(f"Guitare status should be 'sold', got {guitare_selling.get('status')}")
            else:
                print_fail("Guitare not found in seller listings")
    
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    print("\n" + "="*80)
    print("PHASE 4 MARKETPLACE TESTING COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
