#!/usr/bin/env python3
"""
DIVARC Ads Manager Backend Test - PHASE 5
Tests all ads campaign endpoints with comprehensive money flow verification
"""

import requests
import json
import sys

BASE_URL = "https://divarc-hub.preview.emergentagent.com/api"

def log(msg):
    print(f"[TEST] {msg}")

def test_phase5_ads_manager():
    """Test PHASE 5: Ads Manager campaigns + tracking + sponsored feed injection"""
    
    log("=" * 80)
    log("PHASE 5: ADS MANAGER - COMPREHENSIVE BACKEND TEST")
    log("=" * 80)
    
    # Step 0: Create advertiser account ad5@divarc.fr
    log("\n[SETUP] Creating advertiser account ad5@divarc.fr with 480000c wallet")
    
    # Send OTP
    res = requests.post(f"{BASE_URL}/auth/otp/send", json={"email": "ad5@divarc.fr"})
    assert res.status_code == 200, f"OTP send failed: {res.status_code} {res.text}"
    data = res.json()
    assert data.get("ok") == True, f"OTP send not ok: {data}"
    assert "previewCode" in data, f"No previewCode in response: {data}"
    code = data["previewCode"]
    log(f"✓ OTP sent, previewCode: {code}")
    
    # Verify OTP
    res = requests.post(f"{BASE_URL}/auth/otp/verify", json={
        "email": "ad5@divarc.fr",
        "code": code,
        "name": "Advertiser Five"
    })
    assert res.status_code == 200, f"OTP verify failed: {res.status_code} {res.text}"
    data = res.json()
    assert "token" in data, f"No token in response: {data}"
    token = data["token"]
    user = data.get("user", {})
    log(f"✓ Authenticated as {user.get('name')} ({user.get('handle')})")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Verify initial wallet balance
    res = requests.get(f"{BASE_URL}/wallet", headers=headers)
    assert res.status_code == 200, f"Wallet fetch failed: {res.status_code} {res.text}"
    wallet = res.json()
    initial_balance = wallet.get("balanceCents")
    assert initial_balance == 480000, f"Expected initial balance 480000c, got {initial_balance}c"
    log(f"✓ Initial wallet balance: {initial_balance}c")
    
    # ========================================================================
    # TEST 1: CREATE CAMPAIGN - Verify wallet debit and transaction
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 1: CREATE CAMPAIGN - Wallet debit + transaction verification")
    log("=" * 80)
    
    campaign_data = {
        "name": "Test Camp",
        "objective": "Ventes",
        "budgetCents": 5000,
        "color": "#F15BB5",
        "audience": {
            "interests": ["#mode"],
            "age": "18-34",
            "locations": ["France"]
        },
        "creative": {
            "headline": "Promo",
            "body": "-30%",
            "cta": "Acheter",
            "emoji": "👟"
        }
    }
    
    res = requests.post(f"{BASE_URL}/ads/campaigns", json=campaign_data, headers=headers)
    assert res.status_code == 200, f"Campaign creation failed: {res.status_code} {res.text}"
    data = res.json()
    assert "campaign" in data, f"No campaign in response: {data}"
    assert "balanceCents" in data, f"No balanceCents in response: {data}"
    
    campaign = data["campaign"]
    campaign_id = campaign.get("id")
    new_balance = data["balanceCents"]
    
    log(f"✓ Campaign created: {campaign.get('name')} (ID: {campaign_id})")
    log(f"  - Budget: {campaign.get('budgetCents')}c")
    log(f"  - Status: {campaign.get('status')}")
    log(f"  - Objective: {campaign.get('objective')}")
    log(f"  - Color: {campaign.get('color')}")
    
    # Verify wallet debited by 5000 (480000 -> 475000)
    expected_balance = initial_balance - 5000
    assert new_balance == expected_balance, f"Expected balance {expected_balance}c, got {new_balance}c"
    log(f"✓ Wallet debited correctly: {initial_balance}c -> {new_balance}c (-5000c)")
    
    # Verify transaction exists
    res = requests.get(f"{BASE_URL}/transactions", headers=headers)
    assert res.status_code == 200, f"Transactions fetch failed: {res.status_code} {res.text}"
    transactions = res.json()
    
    pub_tx = None
    for tx in transactions:
        if tx.get("category") == "Publicité" and tx.get("amountCents") == -5000:
            pub_tx = tx
            break
    
    assert pub_tx is not None, f"No 'Publicité' transaction of -5000c found in transactions"
    log(f"✓ 'Publicité' transaction created: {pub_tx.get('label')} ({pub_tx.get('amountCents')}c)")
    
    log("\n✅ TEST 1 PASSED: Campaign created, wallet debited, transaction recorded")
    
    # ========================================================================
    # TEST 2: INSUFFICIENT FUNDS - Try to create campaign with huge budget
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 2: INSUFFICIENT FUNDS - Attempt to create campaign with 99999999c budget")
    log("=" * 80)
    
    huge_campaign = {
        "name": "Huge Campaign",
        "budgetCents": 99999999
    }
    
    res = requests.post(f"{BASE_URL}/ads/campaigns", json=huge_campaign, headers=headers)
    assert res.status_code == 402, f"Expected 402, got {res.status_code}: {res.text}"
    log(f"✓ Correctly returned 402 for insufficient balance")
    
    log("\n✅ TEST 2 PASSED: Insufficient funds check working")
    
    # ========================================================================
    # TEST 3: LIST CAMPAIGNS - Verify metrics
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 3: LIST CAMPAIGNS - Verify metrics (impressions, clicks, spentCents, ctr, status)")
    log("=" * 80)
    
    res = requests.get(f"{BASE_URL}/ads/campaigns", headers=headers)
    assert res.status_code == 200, f"Campaigns list failed: {res.status_code} {res.text}"
    campaigns = res.json()
    
    assert len(campaigns) >= 1, f"Expected at least 1 campaign, got {len(campaigns)}"
    
    test_camp = None
    for c in campaigns:
        if c.get("id") == campaign_id:
            test_camp = c
            break
    
    assert test_camp is not None, f"Test Camp not found in campaigns list"
    
    log(f"✓ Campaign found in list: {test_camp.get('name')}")
    log(f"  - Impressions: {test_camp.get('impressions')}")
    log(f"  - Clicks: {test_camp.get('clicks')}")
    log(f"  - SpentCents: {test_camp.get('spentCents')}")
    log(f"  - CTR: {test_camp.get('ctr')}")
    log(f"  - Status: {test_camp.get('status')}")
    
    assert test_camp.get("impressions") == 0, f"Expected impressions 0, got {test_camp.get('impressions')}"
    assert test_camp.get("clicks") == 0, f"Expected clicks 0, got {test_camp.get('clicks')}"
    assert test_camp.get("spentCents") == 0, f"Expected spentCents 0, got {test_camp.get('spentCents')}"
    assert test_camp.get("ctr") == 0, f"Expected ctr 0, got {test_camp.get('ctr')}"
    assert test_camp.get("status") == "active", f"Expected status 'active', got {test_camp.get('status')}"
    
    log("\n✅ TEST 3 PASSED: Campaign metrics correct (all zeros, status active)")
    
    # ========================================================================
    # TEST 4: FEED INJECTION - Verify sponsored posts in foryou, NOT in chrono
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 4: FEED INJECTION - Verify sponsored posts appear in foryou mode only")
    log("=" * 80)
    
    # Test foryou mode
    res = requests.get(f"{BASE_URL}/social/feed?mode=foryou&scope=all", headers=headers)
    assert res.status_code == 200, f"Feed foryou failed: {res.status_code} {res.text}"
    feed_foryou = res.json()
    
    sponsored_items = [item for item in feed_foryou if item.get("sponsored") == True]
    log(f"✓ Feed foryou mode returned {len(feed_foryou)} items, {len(sponsored_items)} sponsored")
    
    assert len(sponsored_items) >= 1, f"Expected at least 1 sponsored item in foryou feed, got {len(sponsored_items)}"
    
    # Find our campaign in sponsored items
    our_sponsored = None
    for item in sponsored_items:
        if item.get("campaignId") == campaign_id:
            our_sponsored = item
            break
    
    assert our_sponsored is not None, f"Our campaign {campaign_id} not found in sponsored items"
    log(f"✓ Our campaign found in sponsored feed:")
    log(f"  - Campaign ID: {our_sponsored.get('campaignId')}")
    log(f"  - Sponsored: {our_sponsored.get('sponsored')}")
    log(f"  - CTA: {our_sponsored.get('cta')}")
    log(f"  - Reason: {our_sponsored.get('reason')}")
    
    assert our_sponsored.get("cta") == "Acheter", f"Expected cta 'Acheter', got {our_sponsored.get('cta')}"
    assert our_sponsored.get("reason") == "Sponsorisé", f"Expected reason 'Sponsorisé', got {our_sponsored.get('reason')}"
    
    # Test chrono mode - should NOT contain sponsored items
    res = requests.get(f"{BASE_URL}/social/feed?mode=chrono&scope=all", headers=headers)
    assert res.status_code == 200, f"Feed chrono failed: {res.status_code} {res.text}"
    feed_chrono = res.json()
    
    sponsored_chrono = [item for item in feed_chrono if item.get("sponsored") == True]
    log(f"✓ Feed chrono mode returned {len(feed_chrono)} items, {len(sponsored_chrono)} sponsored")
    
    assert len(sponsored_chrono) == 0, f"Expected 0 sponsored items in chrono feed, got {len(sponsored_chrono)}"
    
    log("\n✅ TEST 4 PASSED: Sponsored posts appear in foryou mode only, not in chrono")
    
    # ========================================================================
    # TEST 5: TRACK IMPRESSION - 3 times, verify spend
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 5: TRACK IMPRESSION - Track 3 impressions, verify spend (3c each)")
    log("=" * 80)
    
    for i in range(3):
        res = requests.post(f"{BASE_URL}/ads/campaigns/{campaign_id}/track", 
                          json={"type": "impression"}, headers=headers)
        assert res.status_code == 200, f"Track impression {i+1} failed: {res.status_code} {res.text}"
        data = res.json()
        assert data.get("ok") == True, f"Track impression {i+1} not ok: {data}"
        log(f"✓ Impression {i+1} tracked")
    
    # Verify campaign metrics
    res = requests.get(f"{BASE_URL}/ads/campaigns", headers=headers)
    assert res.status_code == 200, f"Campaigns list failed: {res.status_code} {res.text}"
    campaigns = res.json()
    
    test_camp = None
    for c in campaigns:
        if c.get("id") == campaign_id:
            test_camp = c
            break
    
    assert test_camp is not None, f"Test Camp not found"
    
    log(f"✓ Campaign metrics after 3 impressions:")
    log(f"  - Impressions: {test_camp.get('impressions')}")
    log(f"  - SpentCents: {test_camp.get('spentCents')}")
    
    assert test_camp.get("impressions") == 3, f"Expected impressions 3, got {test_camp.get('impressions')}"
    assert test_camp.get("spentCents") == 9, f"Expected spentCents 9 (3x3c), got {test_camp.get('spentCents')}"
    
    log("\n✅ TEST 5 PASSED: 3 impressions tracked, spend = 9c (3c each)")
    
    # ========================================================================
    # TEST 6: TRACK CLICK - 2 times, verify spend and CTR
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 6: TRACK CLICK - Track 2 clicks, verify spend (25c each) and CTR")
    log("=" * 80)
    
    for i in range(2):
        res = requests.post(f"{BASE_URL}/ads/campaigns/{campaign_id}/track", 
                          json={"type": "click"}, headers=headers)
        assert res.status_code == 200, f"Track click {i+1} failed: {res.status_code} {res.text}"
        data = res.json()
        assert data.get("ok") == True, f"Track click {i+1} not ok: {data}"
        log(f"✓ Click {i+1} tracked")
    
    # Verify campaign metrics
    res = requests.get(f"{BASE_URL}/ads/campaigns", headers=headers)
    assert res.status_code == 200, f"Campaigns list failed: {res.status_code} {res.text}"
    campaigns = res.json()
    
    test_camp = None
    for c in campaigns:
        if c.get("id") == campaign_id:
            test_camp = c
            break
    
    assert test_camp is not None, f"Test Camp not found"
    
    log(f"✓ Campaign metrics after 2 clicks:")
    log(f"  - Impressions: {test_camp.get('impressions')}")
    log(f"  - Clicks: {test_camp.get('clicks')}")
    log(f"  - SpentCents: {test_camp.get('spentCents')}")
    log(f"  - CTR: {test_camp.get('ctr')}")
    
    assert test_camp.get("clicks") == 2, f"Expected clicks 2, got {test_camp.get('clicks')}"
    expected_spent = 9 + 50  # 9 from impressions + 2*25 from clicks
    assert test_camp.get("spentCents") == expected_spent, f"Expected spentCents {expected_spent}, got {test_camp.get('spentCents')}"
    
    # CTR = clicks / impressions * 100 = 2 / 3 * 100 = 66.7
    expected_ctr = round(2 / 3 * 100, 1)
    assert test_camp.get("ctr") == expected_ctr, f"Expected ctr {expected_ctr}, got {test_camp.get('ctr')}"
    
    log("\n✅ TEST 6 PASSED: 2 clicks tracked, spend = 59c (9+50), CTR = 66.7%")
    
    # ========================================================================
    # TEST 7: AUTO-END ON BUDGET - Create tiny campaign and exhaust it
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 7: AUTO-END ON BUDGET - Create 6c campaign, exhaust it, verify auto-end")
    log("=" * 80)
    
    tiny_campaign = {
        "name": "Tiny Campaign",
        "budgetCents": 6,
        "creative": {
            "headline": "Tiny",
            "body": "Test",
            "cta": "Click"
        }
    }
    
    res = requests.post(f"{BASE_URL}/ads/campaigns", json=tiny_campaign, headers=headers)
    assert res.status_code == 200, f"Tiny campaign creation failed: {res.status_code} {res.text}"
    data = res.json()
    tiny_id = data["campaign"]["id"]
    log(f"✓ Tiny campaign created (ID: {tiny_id}, budget: 6c)")
    
    # Track 1st impression (spend 3c, total 3c)
    res = requests.post(f"{BASE_URL}/ads/campaigns/{tiny_id}/track", 
                      json={"type": "impression"}, headers=headers)
    assert res.status_code == 200, f"Track impression 1 failed: {res.status_code} {res.text}"
    log(f"✓ Impression 1 tracked (spend 3c, total 3c)")
    
    # Verify still active
    res = requests.get(f"{BASE_URL}/ads/campaigns/{tiny_id}", headers=headers)
    assert res.status_code == 200, f"Campaign fetch failed: {res.status_code} {res.text}"
    tiny = res.json()
    assert tiny.get("status") == "active", f"Expected status 'active', got {tiny.get('status')}"
    assert tiny.get("spentCents") == 3, f"Expected spentCents 3, got {tiny.get('spentCents')}"
    log(f"✓ Campaign still active (spent 3c / 6c)")
    
    # Track 2nd impression (spend 3c, total 6c - should auto-end)
    res = requests.post(f"{BASE_URL}/ads/campaigns/{tiny_id}/track", 
                      json={"type": "impression"}, headers=headers)
    assert res.status_code == 200, f"Track impression 2 failed: {res.status_code} {res.text}"
    log(f"✓ Impression 2 tracked (spend 3c, total 6c)")
    
    # Verify auto-ended
    res = requests.get(f"{BASE_URL}/ads/campaigns/{tiny_id}", headers=headers)
    assert res.status_code == 200, f"Campaign fetch failed: {res.status_code} {res.text}"
    tiny = res.json()
    assert tiny.get("status") == "ended", f"Expected status 'ended', got {tiny.get('status')}"
    assert tiny.get("spentCents") == 6, f"Expected spentCents 6, got {tiny.get('spentCents')}"
    log(f"✓ Campaign auto-ended (spent 6c / 6c)")
    
    # Verify no longer in sponsored feed
    res = requests.get(f"{BASE_URL}/social/feed?mode=foryou&scope=all", headers=headers)
    assert res.status_code == 200, f"Feed fetch failed: {res.status_code} {res.text}"
    feed = res.json()
    
    tiny_in_feed = any(item.get("campaignId") == tiny_id for item in feed if item.get("sponsored"))
    assert not tiny_in_feed, f"Ended campaign should not appear in sponsored feed"
    log(f"✓ Ended campaign not in sponsored feed")
    
    # Try to track another impression - should return ok:false
    res = requests.post(f"{BASE_URL}/ads/campaigns/{tiny_id}/track", 
                      json={"type": "impression"}, headers=headers)
    assert res.status_code == 200, f"Track impression 3 failed: {res.status_code} {res.text}"
    data = res.json()
    assert data.get("ok") == False, f"Expected ok:false for ended campaign, got {data}"
    log(f"✓ Tracking on ended campaign returns ok:false")
    
    log("\n✅ TEST 7 PASSED: Campaign auto-ended when budget exhausted, no longer in feed")
    
    # ========================================================================
    # TEST 8: PAUSE/RESUME - Verify feed injection stops/starts
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 8: PAUSE/RESUME - Verify feed injection stops when paused, resumes when active")
    log("=" * 80)
    
    # Pause the main campaign
    res = requests.patch(f"{BASE_URL}/ads/campaigns/{campaign_id}", 
                        json={"status": "paused"}, headers=headers)
    assert res.status_code == 200, f"Pause campaign failed: {res.status_code} {res.text}"
    data = res.json()
    assert data.get("status") == "paused", f"Expected status 'paused', got {data.get('status')}"
    log(f"✓ Campaign paused")
    
    # Verify not in feed
    res = requests.get(f"{BASE_URL}/social/feed?mode=foryou&scope=all", headers=headers)
    assert res.status_code == 200, f"Feed fetch failed: {res.status_code} {res.text}"
    feed = res.json()
    
    paused_in_feed = any(item.get("campaignId") == campaign_id for item in feed if item.get("sponsored"))
    assert not paused_in_feed, f"Paused campaign should not appear in sponsored feed"
    log(f"✓ Paused campaign not in sponsored feed")
    
    # Resume the campaign
    res = requests.patch(f"{BASE_URL}/ads/campaigns/{campaign_id}", 
                        json={"status": "active"}, headers=headers)
    assert res.status_code == 200, f"Resume campaign failed: {res.status_code} {res.text}"
    data = res.json()
    assert data.get("status") == "active", f"Expected status 'active', got {data.get('status')}"
    log(f"✓ Campaign resumed (active)")
    
    # Verify back in feed
    res = requests.get(f"{BASE_URL}/social/feed?mode=foryou&scope=all", headers=headers)
    assert res.status_code == 200, f"Feed fetch failed: {res.status_code} {res.text}"
    feed = res.json()
    
    active_in_feed = any(item.get("campaignId") == campaign_id for item in feed if item.get("sponsored"))
    assert active_in_feed, f"Active campaign should appear in sponsored feed"
    log(f"✓ Active campaign back in sponsored feed")
    
    log("\n✅ TEST 8 PASSED: Pause/resume working, feed injection stops/starts correctly")
    
    # ========================================================================
    # TEST 9: END + REFUND - Verify wallet refund and transaction
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 9: END + REFUND - End campaign, verify wallet refund and transaction")
    log("=" * 80)
    
    # Get current wallet balance
    res = requests.get(f"{BASE_URL}/wallet", headers=headers)
    assert res.status_code == 200, f"Wallet fetch failed: {res.status_code} {res.text}"
    wallet_before = res.json()
    balance_before = wallet_before.get("balanceCents")
    log(f"✓ Wallet balance before ending campaign: {balance_before}c")
    
    # Get campaign current spend
    res = requests.get(f"{BASE_URL}/ads/campaigns/{campaign_id}", headers=headers)
    assert res.status_code == 200, f"Campaign fetch failed: {res.status_code} {res.text}"
    camp_before = res.json()
    budget = camp_before.get("budgetCents")
    spent = camp_before.get("spentCents")
    expected_refund = budget - spent
    log(f"✓ Campaign budget: {budget}c, spent: {spent}c, expected refund: {expected_refund}c")
    
    # End the campaign
    res = requests.patch(f"{BASE_URL}/ads/campaigns/{campaign_id}", 
                        json={"status": "ended"}, headers=headers)
    assert res.status_code == 200, f"End campaign failed: {res.status_code} {res.text}"
    data = res.json()
    assert data.get("status") == "ended", f"Expected status 'ended', got {data.get('status')}"
    log(f"✓ Campaign ended")
    
    # Verify wallet refunded
    res = requests.get(f"{BASE_URL}/wallet", headers=headers)
    assert res.status_code == 200, f"Wallet fetch failed: {res.status_code} {res.text}"
    wallet_after = res.json()
    balance_after = wallet_after.get("balanceCents")
    
    expected_balance = balance_before + expected_refund
    assert balance_after == expected_balance, f"Expected balance {expected_balance}c, got {balance_after}c"
    log(f"✓ Wallet refunded: {balance_before}c -> {balance_after}c (+{expected_refund}c)")
    
    # Verify refund transaction exists
    res = requests.get(f"{BASE_URL}/transactions", headers=headers)
    assert res.status_code == 200, f"Transactions fetch failed: {res.status_code} {res.text}"
    transactions = res.json()
    
    refund_tx = None
    for tx in transactions:
        if "Remboursement pub" in tx.get("label", "") and tx.get("amountCents") == expected_refund:
            refund_tx = tx
            break
    
    assert refund_tx is not None, f"No 'Remboursement pub' transaction of {expected_refund}c found"
    log(f"✓ 'Remboursement pub' transaction created: {refund_tx.get('label')} (+{refund_tx.get('amountCents')}c)")
    
    log("\n✅ TEST 9 PASSED: Campaign ended, wallet refunded, transaction recorded")
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    log("\n" + "=" * 80)
    log("PHASE 5 ADS MANAGER - ALL TESTS PASSED ✅")
    log("=" * 80)
    log("\nSummary:")
    log("  1. ✅ CREATE campaign - wallet debited, transaction created")
    log("  2. ✅ INSUFFICIENT funds - 402 returned correctly")
    log("  3. ✅ LIST campaigns - metrics correct (impressions, clicks, spend, CTR, status)")
    log("  4. ✅ FEED INJECTION - sponsored posts in foryou mode only, not chrono")
    log("  5. ✅ TRACK IMPRESSION - 3 impressions tracked, spend = 9c (3c each)")
    log("  6. ✅ TRACK CLICK - 2 clicks tracked, spend = 59c (9+50), CTR = 66.7%")
    log("  7. ✅ AUTO-END ON BUDGET - tiny campaign exhausted, auto-ended, removed from feed")
    log("  8. ✅ PAUSE/RESUME - feed injection stops/starts correctly")
    log("  9. ✅ END + REFUND - wallet refunded by (budget - spent), transaction created")
    log("\n" + "=" * 80)
    log("NO CRITICAL ISSUES FOUND - ALL MONEY FLOWS VERIFIED")
    log("=" * 80)

if __name__ == "__main__":
    try:
        test_phase5_ads_manager()
        sys.exit(0)
    except AssertionError as e:
        log(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        log(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
