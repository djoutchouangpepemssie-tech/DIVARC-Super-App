#!/usr/bin/env python3
"""
DIVARC Social Backend Test Suite - PHASE 3
Tests all social feed, posts, like, comment, follow, buy, tip endpoints
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
    print("DIVARC SOCIAL BACKEND TEST SUITE - PHASE 3")
    print("="*80)
    
    # Setup: Create BUYER user
    print_test("SETUP", "Create BUYER user buyer@divarc.fr")
    buyer_token = auth_user("buyer@divarc.fr", "Buyer User")
    if not buyer_token:
        print_fail("Failed to create buyer user")
        sys.exit(1)
    print_pass(f"Buyer authenticated, token: {buyer_token[:20]}...")
    
    buyer_balance = get_wallet_balance(buyer_token)
    print_info(f"Buyer wallet balance: {buyer_balance} cents")
    if buyer_balance != 480000:
        print_fail(f"Expected 480000 cents, got {buyer_balance}")
        sys.exit(1)
    print_pass("Buyer wallet has 480000 cents")
    
    headers_buyer = {"Authorization": f"Bearer {buyer_token}"}
    
    # TEST 1: GET feed foryou mode
    print_test(1, "GET /api/social/feed?mode=foryou&scope=all")
    try:
        r = requests.get(f"{BASE_URL}/social/feed?mode=foryou&scope=all", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            posts = r.json()
            print_info(f"Received {len(posts)} posts")
            if len(posts) != 8:
                print_fail(f"Expected 8 posts, got {len(posts)}")
            else:
                print_pass("Received 8 seeded posts")
            
            # Verify first post structure
            if posts:
                p = posts[0]
                required_fields = ['id', 'author', 'caption', 'mediaUrl', 'hashtags', 'likes', 'comments', 'saves', 'views', 'liked', 'saved', 'following', 'reason']
                missing = [f for f in required_fields if f not in p]
                if missing:
                    print_fail(f"Missing fields: {missing}")
                else:
                    print_pass("All required fields present")
                
                # Check author structure
                if 'author' in p and p['author']:
                    author = p['author']
                    author_fields = ['id', 'name', 'handle', 'verified']
                    missing_author = [f for f in author_fields if f not in author]
                    if missing_author:
                        print_fail(f"Missing author fields: {missing_author}")
                    else:
                        print_pass(f"Author structure correct: {author['name']} ({author['handle']}) verified={author['verified']}")
                
                # Check reason is non-empty
                if p.get('reason'):
                    print_pass(f"Reason present: '{p['reason']}'")
                else:
                    print_fail("Reason is empty")
                
                # Check for product in some posts
                posts_with_product = [p for p in posts if p.get('product')]
                print_info(f"Posts with product: {len(posts_with_product)}")
                if posts_with_product:
                    prod = posts_with_product[0]['product']
                    if 'title' in prod and 'priceCents' in prod and 'emoji' in prod:
                        print_pass(f"Product structure correct: {prod['title']} - {prod['priceCents']}c {prod['emoji']}")
                    else:
                        print_fail(f"Product missing fields: {prod}")
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # TEST 2: GET feed chrono mode
    print_test(2, "GET /api/social/feed?mode=chrono&scope=all")
    try:
        r = requests.get(f"{BASE_URL}/social/feed?mode=chrono&scope=all", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            posts = r.json()
            print_info(f"Received {len(posts)} posts")
            
            # Check chronological order
            if len(posts) >= 2:
                dates = [p['createdAt'] for p in posts]
                is_desc = all(dates[i] >= dates[i+1] for i in range(len(dates)-1))
                if is_desc:
                    print_pass("Posts sorted by createdAt desc")
                else:
                    print_fail("Posts NOT in chronological order")
            
            # Check reason
            if posts and posts[0].get('reason') == "Ordre chronologique":
                print_pass("Reason is 'Ordre chronologique'")
            else:
                print_fail(f"Reason is '{posts[0].get('reason') if posts else 'N/A'}', expected 'Ordre chronologique'")
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # Get a post ID for subsequent tests
    r = requests.get(f"{BASE_URL}/social/feed?mode=foryou&scope=all", headers=headers_buyer)
    posts = r.json()
    if not posts:
        print_fail("No posts available for testing")
        sys.exit(1)
    
    test_post_id = posts[0]['id']
    original_likes = posts[0]['likes']
    original_saves = posts[0]['saves']
    original_comments = posts[0]['comments']
    
    # TEST 3: LIKE toggle
    print_test(3, f"POST /api/social/posts/{test_post_id}/like (toggle)")
    try:
        # First like
        r = requests.post(f"{BASE_URL}/social/posts/{test_post_id}/like", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            data = r.json()
            if data.get('liked') == True and data.get('likes') == original_likes + 1:
                print_pass(f"Liked: {data['liked']}, likes: {data['likes']} (was {original_likes})")
            else:
                print_fail(f"Expected liked=True, likes={original_likes+1}, got {data}")
        
        # Unlike
        r = requests.post(f"{BASE_URL}/social/posts/{test_post_id}/like", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            data = r.json()
            if data.get('liked') == False and data.get('likes') == original_likes:
                print_pass(f"Unliked: {data['liked']}, likes back to {data['likes']}")
            else:
                print_fail(f"Expected liked=False, likes={original_likes}, got {data}")
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # TEST 4: SAVE toggle
    print_test(4, f"POST /api/social/posts/{test_post_id}/save (toggle)")
    try:
        # First save
        r = requests.post(f"{BASE_URL}/social/posts/{test_post_id}/save", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            data = r.json()
            if data.get('saved') == True and data.get('saves') == original_saves + 1:
                print_pass(f"Saved: {data['saved']}, saves: {data['saves']} (was {original_saves})")
            else:
                print_fail(f"Expected saved=True, saves={original_saves+1}, got {data}")
        
        # Unsave
        r = requests.post(f"{BASE_URL}/social/posts/{test_post_id}/save", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            data = r.json()
            if data.get('saved') == False and data.get('saves') == original_saves:
                print_pass(f"Unsaved: {data['saved']}, saves back to {data['saves']}")
            else:
                print_fail(f"Expected saved=False, saves={original_saves}, got {data}")
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # TEST 5: COMMENTS
    print_test(5, f"POST /api/social/posts/{test_post_id}/comments")
    try:
        # Post comment
        r = requests.post(f"{BASE_URL}/social/posts/{test_post_id}/comments", 
                         json={"text": "Super!"}, headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            comment = r.json()
            if 'id' in comment and comment.get('text') == "Super!":
                print_pass(f"Comment created: id={comment['id']}, name={comment.get('name')}")
            else:
                print_fail(f"Comment structure incorrect: {comment}")
        
        # Get comments
        r = requests.get(f"{BASE_URL}/social/posts/{test_post_id}/comments", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            comments = r.json()
            found = any(c.get('text') == "Super!" for c in comments)
            if found:
                print_pass(f"Comment 'Super!' found in {len(comments)} comments")
            else:
                print_fail("Comment not found in GET response")
        
        # Verify post comments count incremented
        r = requests.get(f"{BASE_URL}/social/feed?mode=foryou&scope=all", headers=headers_buyer)
        posts = r.json()
        post = next((p for p in posts if p['id'] == test_post_id), None)
        if post and post['comments'] == original_comments + 1:
            print_pass(f"Post comments count incremented: {original_comments} -> {post['comments']}")
        else:
            print_fail(f"Comments count not incremented correctly: expected {original_comments+1}, got {post['comments'] if post else 'N/A'}")
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # TEST 6: FOLLOW
    print_test(6, "POST /api/social/follow/{authorId} and feed filtering")
    try:
        # Get an author ID
        r = requests.get(f"{BASE_URL}/social/feed?mode=foryou&scope=all", headers=headers_buyer)
        posts = r.json()
        author_id = posts[0]['author']['id']
        author_name = posts[0]['author']['name']
        
        # Follow
        r = requests.post(f"{BASE_URL}/social/follow/{author_id}", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            data = r.json()
            if data.get('following') == True:
                print_pass(f"Following {author_name}: {data['following']}")
            else:
                print_fail(f"Expected following=True, got {data}")
        
        # Get feed with scope=following
        r = requests.get(f"{BASE_URL}/social/feed?mode=foryou&scope=following", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            following_posts = r.json()
            if following_posts:
                all_from_author = all(p['author']['id'] == author_id for p in following_posts)
                if all_from_author:
                    print_pass(f"Feed scope=following includes only posts by {author_name} ({len(following_posts)} posts)")
                else:
                    print_fail("Feed scope=following includes posts from other authors")
            else:
                print_fail("Feed scope=following returned no posts")
        
        # Unfollow
        r = requests.post(f"{BASE_URL}/social/follow/{author_id}", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            data = r.json()
            if data.get('following') == False:
                print_pass(f"Unfollowed {author_name}: {data['following']}")
            else:
                print_fail(f"Expected following=False, got {data}")
        
        # Verify feed scope=following excludes author
        r = requests.get(f"{BASE_URL}/social/feed?mode=foryou&scope=following", headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            following_posts = r.json()
            if len(following_posts) == 0:
                print_pass("Feed scope=following now empty after unfollow")
            else:
                print_fail(f"Feed scope=following still has {len(following_posts)} posts after unfollow")
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # TEST 7: NOT INTERESTED
    print_test(7, "POST /api/social/posts/{id}/notinterested")
    try:
        # Get a different post
        r = requests.get(f"{BASE_URL}/social/feed?mode=foryou&scope=all", headers=headers_buyer)
        posts = r.json()
        if len(posts) < 2:
            print_fail("Not enough posts for notinterested test")
        else:
            ni_post_id = posts[1]['id']
            ni_post_caption = posts[1]['caption']
            
            # Mark not interested
            r = requests.post(f"{BASE_URL}/social/posts/{ni_post_id}/notinterested", headers=headers_buyer)
            if r.status_code != 200:
                print_fail(f"Status {r.status_code}: {r.text}")
            else:
                print_pass("Marked post as not interested")
            
            # Verify post excluded from feed
            r = requests.get(f"{BASE_URL}/social/feed?mode=foryou&scope=all", headers=headers_buyer)
            posts_after = r.json()
            found = any(p['id'] == ni_post_id for p in posts_after)
            if not found:
                print_pass(f"Post '{ni_post_caption[:30]}...' excluded from feed")
            else:
                print_fail("Post still appears in feed after marking not interested")
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # TEST 8: BUY (money flow - CRITICAL)
    print_test(8, "POST /api/social/posts/{id}/buy (money flow)")
    try:
        # Find a post with product
        r = requests.get(f"{BASE_URL}/social/feed?mode=foryou&scope=all", headers=headers_buyer)
        posts = r.json()
        product_posts = [p for p in posts if p.get('product')]
        
        if not product_posts:
            print_fail("No posts with products found")
        else:
            buy_post = product_posts[0]
            buy_post_id = buy_post['id']
            product = buy_post['product']
            price = product['priceCents']
            creator_id = buy_post['author']['id']
            
            print_info(f"Buying: {product['title']} for {price}c from {buy_post['author']['name']}")
            
            # Get buyer balance before
            balance_before = get_wallet_balance(buyer_token)
            print_info(f"Buyer balance before: {balance_before}c")
            
            # Buy
            r = requests.post(f"{BASE_URL}/social/posts/{buy_post_id}/buy", headers=headers_buyer)
            if r.status_code != 200:
                print_fail(f"Status {r.status_code}: {r.text}")
            else:
                data = r.json()
                if data.get('ok') == True and data.get('amountCents') == price:
                    print_pass(f"Buy successful: amountCents={data['amountCents']}")
                else:
                    print_fail(f"Buy response incorrect: {data}")
                
                # Verify buyer balance
                balance_after = data.get('balanceCents')
                expected_balance = balance_before - price
                if balance_after == expected_balance:
                    print_pass(f"Buyer balance correct: {balance_before} - {price} = {balance_after}")
                else:
                    print_fail(f"Buyer balance incorrect: expected {expected_balance}, got {balance_after}")
            
            # Verify transaction created
            r = requests.get(f"{BASE_URL}/transactions", headers=headers_buyer)
            if r.status_code != 200:
                print_fail(f"Failed to get transactions: {r.status_code}")
            else:
                txs = r.json()
                social_tx = next((t for t in txs if t.get('category') == 'Social' and t.get('amountCents') == -price), None)
                if social_tx:
                    print_pass(f"Transaction created: {social_tx['label']} {social_tx['amountCents']}c")
                else:
                    print_fail("No Social transaction found for purchase")
            
            # For creator wallet verification, we need to create a real creator user
            # Since bot users don't have accessible wallets, create a second user as creator
            print_info("Creating second user as creator to verify wallet credit...")
            creator_token = auth_user("creator@divarc.fr", "Creator User")
            if not creator_token:
                print_fail("Failed to create creator user")
            else:
                headers_creator = {"Authorization": f"Bearer {creator_token}"}
                creator_balance_before = get_wallet_balance(creator_token)
                print_info(f"Creator balance before: {creator_balance_before}c")
                
                # Creator posts a shoppable post
                r = requests.post(f"{BASE_URL}/social/posts", 
                                json={
                                    "caption": "Test product post",
                                    "mediaUrl": "https://example.com/video.mp4",
                                    "hashtags": ["#test"],
                                    "product": {
                                        "title": "Test Product",
                                        "priceCents": 1500,
                                        "emoji": "🎁"
                                    }
                                }, headers=headers_creator)
                if r.status_code != 200:
                    print_fail(f"Creator post failed: {r.status_code} {r.text}")
                else:
                    creator_post = r.json()
                    creator_post_id = creator_post['id']
                    print_pass(f"Creator posted shoppable item: {creator_post_id}")
                    
                    # Buyer buys from creator
                    r = requests.post(f"{BASE_URL}/social/posts/{creator_post_id}/buy", headers=headers_buyer)
                    if r.status_code != 200:
                        print_fail(f"Buy from creator failed: {r.status_code} {r.text}")
                    else:
                        print_pass("Buyer purchased from creator")
                        
                        # Verify creator earnings
                        r = requests.get(f"{BASE_URL}/social/creator", headers=headers_creator)
                        if r.status_code != 200:
                            print_fail(f"Creator dashboard failed: {r.status_code}")
                        else:
                            creator_data = r.json()
                            earnings = creator_data.get('earningsCents', 0)
                            if earnings >= 1500:
                                print_pass(f"Creator earningsCents: {earnings}c (>= 1500c)")
                            else:
                                print_fail(f"Creator earningsCents: {earnings}c (expected >= 1500c)")
                        
                        # Verify creator wallet increased
                        creator_balance_after = get_wallet_balance(creator_token)
                        if creator_balance_after == creator_balance_before + 1500:
                            print_pass(f"Creator wallet increased: {creator_balance_before} + 1500 = {creator_balance_after}")
                        else:
                            print_fail(f"Creator wallet incorrect: expected {creator_balance_before + 1500}, got {creator_balance_after}")
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # TEST 9: TIP
    print_test(9, "POST /api/social/posts/{id}/tip")
    try:
        # Get creator post
        r = requests.get(f"{BASE_URL}/social/feed?mode=foryou&scope=all", headers=headers_buyer)
        posts = r.json()
        # Use the creator's post from previous test
        creator_token = auth_user("creator@divarc.fr", "Creator User")
        headers_creator = {"Authorization": f"Bearer {creator_token}"}
        
        r = requests.get(f"{BASE_URL}/social/creator", headers=headers_creator)
        creator_posts = r.json().get('posts', [])
        if not creator_posts:
            print_fail("No creator posts found")
        else:
            tip_post_id = creator_posts[0]['id']
            tip_amount = 200
            
            # Get balances before
            buyer_balance_before = get_wallet_balance(buyer_token)
            creator_balance_before = get_wallet_balance(creator_token)
            creator_earnings_before = r.json().get('earningsCents', 0)
            
            print_info(f"Buyer balance before tip: {buyer_balance_before}c")
            print_info(f"Creator balance before tip: {creator_balance_before}c")
            print_info(f"Creator earnings before tip: {creator_earnings_before}c")
            
            # Tip
            r = requests.post(f"{BASE_URL}/social/posts/{tip_post_id}/tip", 
                            json={"amountCents": tip_amount}, headers=headers_buyer)
            if r.status_code != 200:
                print_fail(f"Status {r.status_code}: {r.text}")
            else:
                data = r.json()
                if data.get('ok') == True:
                    print_pass(f"Tip successful: {tip_amount}c")
                else:
                    print_fail(f"Tip response incorrect: {data}")
            
            # Verify buyer balance
            buyer_balance_after = get_wallet_balance(buyer_token)
            if buyer_balance_after == buyer_balance_before - tip_amount:
                print_pass(f"Buyer balance decreased: {buyer_balance_before} - {tip_amount} = {buyer_balance_after}")
            else:
                print_fail(f"Buyer balance incorrect: expected {buyer_balance_before - tip_amount}, got {buyer_balance_after}")
            
            # Verify creator earnings
            r = requests.get(f"{BASE_URL}/social/creator", headers=headers_creator)
            creator_data = r.json()
            creator_earnings_after = creator_data.get('earningsCents', 0)
            if creator_earnings_after >= creator_earnings_before + tip_amount:
                print_pass(f"Creator earnings increased: {creator_earnings_before} + {tip_amount} = {creator_earnings_after}")
            else:
                print_fail(f"Creator earnings incorrect: expected >= {creator_earnings_before + tip_amount}, got {creator_earnings_after}")
            
            # Verify creator wallet
            creator_balance_after = get_wallet_balance(creator_token)
            if creator_balance_after == creator_balance_before + tip_amount:
                print_pass(f"Creator wallet increased: {creator_balance_before} + {tip_amount} = {creator_balance_after}")
            else:
                print_fail(f"Creator wallet incorrect: expected {creator_balance_before + tip_amount}, got {creator_balance_after}")
            
            # Verify Pourboire transaction
            r = requests.get(f"{BASE_URL}/transactions", headers=headers_buyer)
            txs = r.json()
            tip_tx = next((t for t in txs if 'Pourboire' in t.get('label', '') and t.get('amountCents') == -tip_amount), None)
            if tip_tx:
                print_pass(f"Pourboire transaction created: {tip_tx['label']}")
            else:
                print_fail("No Pourboire transaction found")
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # TEST 10: INSUFFICIENT BALANCE
    print_test(10, "POST /api/social/posts/{id}/tip with insufficient balance (402)")
    try:
        r = requests.get(f"{BASE_URL}/social/feed?mode=foryou&scope=all", headers=headers_buyer)
        posts = r.json()
        if posts:
            huge_amount = 99999999
            r = requests.post(f"{BASE_URL}/social/posts/{posts[0]['id']}/tip", 
                            json={"amountCents": huge_amount}, headers=headers_buyer)
            if r.status_code == 402:
                print_pass(f"Insufficient balance returns 402: {r.json().get('error')}")
            else:
                print_fail(f"Expected 402, got {r.status_code}: {r.text}")
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # TEST 11: CREATE POST
    print_test(11, "POST /api/social/posts (create new post)")
    try:
        r = requests.post(f"{BASE_URL}/social/posts", 
                         json={
                             "caption": "hi",
                             "mediaUrl": "u",
                             "hashtags": ["#x"]
                         }, headers=headers_buyer)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            post = r.json()
            if 'id' in post and post.get('caption') == 'hi' and post.get('likes') == 0:
                print_pass(f"Post created: id={post['id']}, likes={post['likes']}")
            else:
                print_fail(f"Post structure incorrect: {post}")
            
            # Verify it appears in feed (chrono first)
            r = requests.get(f"{BASE_URL}/social/feed?mode=chrono&scope=all", headers=headers_buyer)
            posts = r.json()
            if posts and posts[0]['id'] == post['id']:
                print_pass("New post appears first in chrono feed")
            else:
                print_fail("New post not first in chrono feed")
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    # TEST 12: GET CREATOR DASHBOARD
    print_test(12, "GET /api/social/creator")
    try:
        creator_token = auth_user("creator@divarc.fr", "Creator User")
        headers_creator = {"Authorization": f"Bearer {creator_token}"}
        
        r = requests.get(f"{BASE_URL}/social/creator", headers=headers_creator)
        if r.status_code != 200:
            print_fail(f"Status {r.status_code}: {r.text}")
        else:
            data = r.json()
            required_fields = ['posts', 'followers', 'earningsCents', 'views', 'likes']
            missing = [f for f in required_fields if f not in data]
            if missing:
                print_fail(f"Missing fields: {missing}")
            else:
                print_pass(f"Creator dashboard: {len(data['posts'])} posts, {data['followers']} followers, {data['earningsCents']}c earnings, {data['views']} views, {data['likes']} likes")
    except Exception as e:
        print_fail(f"Exception: {e}")
    
    print("\n" + "="*80)
    print("PHASE 3 BACKEND TESTS COMPLETE")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
