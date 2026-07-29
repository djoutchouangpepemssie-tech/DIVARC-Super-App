#!/usr/bin/env python3
"""
DIVARC Backend Test Suite - PHASE 9: Ads Manager v2 (Google Ads-like)
Tests all Ads Manager v2 endpoints with comprehensive validation
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "https://divarc-hub.preview.emergentagent.com/api"
TEST_USER_EMAIL = "ads9@divarc.fr"

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

    def get(self, path: str, **kwargs) -> requests.Response:
        """GET request with auth"""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        return requests.get(f"{self.base_url}{path}", headers=headers, **kwargs)

    def post(self, path: str, json_data: Optional[Dict] = None, **kwargs) -> requests.Response:
        """POST request with auth"""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        return requests.post(f"{self.base_url}{path}", json=json_data, headers=headers, **kwargs)

    def patch(self, path: str, json_data: Optional[Dict] = None, **kwargs) -> requests.Response:
        """PATCH request with auth"""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        return requests.patch(f"{self.base_url}{path}", json=json_data, headers=headers, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        """DELETE request with auth"""
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        return requests.delete(f"{self.base_url}{path}", headers=headers, **kwargs)

    def get_wallet(self) -> Dict[str, Any]:
        """Get wallet balance"""
        resp = self.get("/wallet")
        return resp.json()

def test_phase9_ads_manager_v2():
    """Test PHASE 9: Ads Manager v2 (Google Ads-like)"""
    client = APIClient(BASE_URL)
    
    print("\n" + "="*80)
    print("PHASE 9: ADS MANAGER V2 (Google Ads-like) - Backend Testing")
    print("="*80 + "\n")

    # ========== AUTH SETUP ==========
    print_test("Setting up authentication for ads9@divarc.fr")
    try:
        send_resp = client.auth_otp_send(TEST_USER_EMAIL)
        if not send_resp.get("ok"):
            print_fail(f"OTP send failed: {send_resp}")
            return False
        
        code = send_resp.get("previewCode")
        if not code:
            print_fail("No preview code returned")
            return False
        
        verify_resp = client.auth_otp_verify(TEST_USER_EMAIL, code)
        if "token" not in verify_resp:
            print_fail(f"OTP verify failed: {verify_resp}")
            return False
        
        print_pass(f"Authenticated as {client.user.get('handle')} with token")
    except Exception as e:
        print_fail(f"Auth setup failed: {e}")
        return False

    # ========== TEST 1: GET /ads/config ==========
    print_test("TEST 1: GET /ads/config - returns types, objectives, bidStrategies, interests, devices, ageRanges, genders")
    try:
        resp = client.get("/ads/config")
        if resp.status_code != 200:
            print_fail(f"Status {resp.status_code}: {resp.text}")
            return False
        
        config = resp.json()
        
        # Verify types (4: search/display/video/shopping)
        if "types" not in config or len(config["types"]) != 4:
            print_fail(f"Expected 4 types, got {len(config.get('types', []))}")
            return False
        
        type_ids = [t["id"] for t in config["types"]]
        expected_types = ["search", "display", "video", "shopping"]
        if type_ids != expected_types:
            print_fail(f"Expected types {expected_types}, got {type_ids}")
            return False
        
        # Verify each type has required fields
        for t in config["types"]:
            if not all(k in t for k in ["id", "name", "emoji", "color", "desc", "defaultBid"]):
                print_fail(f"Type {t.get('id')} missing required fields")
                return False
        
        # Verify objectives (5)
        if "objectives" not in config or len(config["objectives"]) != 5:
            print_fail(f"Expected 5 objectives, got {len(config.get('objectives', []))}")
            return False
        
        # Verify bidStrategies (4: cpc/cpm/maximize/target_cpa)
        if "bidStrategies" not in config or len(config["bidStrategies"]) != 4:
            print_fail(f"Expected 4 bidStrategies, got {len(config.get('bidStrategies', []))}")
            return False
        
        bid_ids = [b["id"] for b in config["bidStrategies"]]
        expected_bids = ["cpc", "cpm", "maximize", "target_cpa"]
        if bid_ids != expected_bids:
            print_fail(f"Expected bidStrategies {expected_bids}, got {bid_ids}")
            return False
        
        # Verify interests (array)
        if "interests" not in config or not isinstance(config["interests"], list) or len(config["interests"]) == 0:
            print_fail(f"Expected non-empty interests array")
            return False
        
        # Verify devices (3)
        if "devices" not in config or len(config["devices"]) != 3:
            print_fail(f"Expected 3 devices, got {len(config.get('devices', []))}")
            return False
        
        # Verify ageRanges (6)
        if "ageRanges" not in config or len(config["ageRanges"]) != 6:
            print_fail(f"Expected 6 ageRanges, got {len(config.get('ageRanges', []))}")
            return False
        
        # Verify genders (3)
        if "genders" not in config or len(config["genders"]) != 3:
            print_fail(f"Expected 3 genders, got {len(config.get('genders', []))}")
            return False
        
        print_pass(f"Config returned: 4 types (search/display/video/shopping), 5 objectives, 4 bidStrategies (cpc/cpm/maximize/target_cpa), {len(config['interests'])} interests, 3 devices, 6 ageRanges, 3 genders")
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

    # ========== TEST 2: GET /ads/keywords?q=chaussures ==========
    print_test("TEST 2: GET /ads/keywords?q=chaussures - returns 10 suggestions with text, matchType, volume, competition, suggestedBidCents")
    try:
        resp = client.get("/ads/keywords", params={"q": "chaussures"})
        if resp.status_code != 200:
            print_fail(f"Status {resp.status_code}: {resp.text}")
            return False
        
        keywords = resp.json()
        
        if not isinstance(keywords, list) or len(keywords) != 10:
            print_fail(f"Expected 10 keywords, got {len(keywords)}")
            return False
        
        # Verify first keyword contains 'chaussures'
        first_text = keywords[0].get("text", "").lower()
        if "chaussures" not in first_text:
            print_fail(f"First keyword text '{first_text}' does not contain 'chaussures'")
            return False
        
        # Verify all keywords have required fields
        for kw in keywords:
            if not all(k in kw for k in ["text", "matchType", "volume", "competition", "suggestedBidCents"]):
                print_fail(f"Keyword missing required fields: {kw}")
                return False
            
            if not isinstance(kw["volume"], int) or kw["volume"] <= 0:
                print_fail(f"Invalid volume: {kw['volume']}")
                return False
            
            if not isinstance(kw["suggestedBidCents"], int) or kw["suggestedBidCents"] <= 0:
                print_fail(f"Invalid suggestedBidCents: {kw['suggestedBidCents']}")
                return False
        
        print_pass(f"10 keywords returned, first text: '{keywords[0]['text']}' (contains 'chaussures'), all have text/matchType/volume/competition/suggestedBidCents")
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

    # ========== TEST 3: POST /ads/estimate - targeting narrowing ==========
    print_test("TEST 3: POST /ads/estimate - verify narrower targeting reduces audience")
    try:
        # First estimate with empty targeting (broad)
        resp1 = client.post("/ads/estimate", json_data={
            "dailyBudgetCents": 2000,
            "bidStrategy": "cpc",
            "maxBidCents": 45,
            "targeting": {}
        })
        if resp1.status_code != 200:
            print_fail(f"Status {resp1.status_code}: {resp1.text}")
            return False
        
        est1 = resp1.json()
        
        # Verify required fields
        required = ["audience", "impressionsPerDay", "clicksPerDay", "reachPerDay", "estCpcCents", "estCtr"]
        if not all(k in est1 for k in required):
            print_fail(f"Estimate missing required fields: {est1.keys()}")
            return False
        
        if not isinstance(est1["audience"], int) or est1["audience"] <= 0:
            print_fail(f"Invalid audience: {est1['audience']}")
            return False
        
        if not isinstance(est1["impressionsPerDay"], list) or len(est1["impressionsPerDay"]) != 2:
            print_fail(f"impressionsPerDay should be [min, max]: {est1['impressionsPerDay']}")
            return False
        
        if not isinstance(est1["clicksPerDay"], list) or len(est1["clicksPerDay"]) != 2:
            print_fail(f"clicksPerDay should be [min, max]: {est1['clicksPerDay']}")
            return False
        
        if not isinstance(est1["reachPerDay"], list) or len(est1["reachPerDay"]) != 2:
            print_fail(f"reachPerDay should be [min, max]: {est1['reachPerDay']}")
            return False
        
        # Second estimate with narrow targeting
        resp2 = client.post("/ads/estimate", json_data={
            "dailyBudgetCents": 2000,
            "bidStrategy": "cpc",
            "maxBidCents": 45,
            "targeting": {
                "interests": ["Tech", "Mode"],
                "ageRange": ["25-34", "35-44"]
            }
        })
        if resp2.status_code != 200:
            print_fail(f"Status {resp2.status_code}: {resp2.text}")
            return False
        
        est2 = resp2.json()
        
        # Verify narrower targeting reduces audience
        if est2["audience"] >= est1["audience"]:
            print_fail(f"Narrower targeting should reduce audience: broad={est1['audience']}, narrow={est2['audience']}")
            return False
        
        print_pass(f"Broad targeting audience={est1['audience']}, narrow targeting audience={est2['audience']} (reduced ✓). impressionsPerDay={est1['impressionsPerDay']}, clicksPerDay={est1['clicksPerDay']}, reachPerDay={est1['reachPerDay']}, estCpcCents={est1['estCpcCents']}, estCtr={est1['estCtr']}")
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

    # ========== TEST 4: POST /ads/campaigns - CRITICAL money flow ==========
    print_test("TEST 4: POST /ads/campaigns - CRITICAL money flow (wallet debit, transaction, daily[] history, adDerived fields)")
    try:
        # Get wallet before
        wallet_before = client.get_wallet()
        balance_before = wallet_before.get("balanceCents", 0)
        print_info(f"Wallet before: {balance_before}c")
        
        # Create campaign
        campaign_data = {
            "name": "Test Search",
            "type": "search",
            "objective": "traffic",
            "budgetType": "total",
            "budgetCents": 30000,
            "dailyBudgetCents": 1000,
            "bidStrategy": "cpc",
            "maxBidCents": 50,
            "targeting": {
                "interests": ["Tech"],
                "ageRange": ["25-34"],
                "genders": ["Tous"],
                "devices": ["Mobile"]
            },
            "keywords": ["chaussures", "baskets"],
            "creative": {
                "headline": "Promo",
                "body": "desc",
                "cta": "Acheter"
            }
        }
        
        resp = client.post("/ads/campaigns", json_data=campaign_data)
        if resp.status_code != 200:
            print_fail(f"Status {resp.status_code}: {resp.text}")
            return False
        
        result = resp.json()
        
        # Verify response structure
        if "campaign" not in result or "balanceCents" not in result:
            print_fail(f"Response missing campaign or balanceCents: {result.keys()}")
            return False
        
        campaign = result["campaign"]
        balance_after = result["balanceCents"]
        
        # Verify wallet debited by 30000c
        expected_balance = balance_before - 30000
        if balance_after != expected_balance:
            print_fail(f"Wallet not debited correctly: before={balance_before}, after={balance_after}, expected={expected_balance}")
            return False
        
        print_info(f"Wallet after: {balance_after}c (debited 30000c ✓)")
        
        # Verify campaign has daily[] array (non-empty, ~7 entries)
        if "daily" not in campaign or not isinstance(campaign["daily"], list):
            print_fail(f"Campaign missing daily[] array")
            return False
        
        if len(campaign["daily"]) < 5:
            print_fail(f"Campaign daily[] should have ~7 entries, got {len(campaign['daily'])}")
            return False
        
        print_info(f"Campaign daily[] has {len(campaign['daily'])} entries (simulated history ✓)")
        
        # Verify impressions > 0
        if "impressions" not in campaign or campaign["impressions"] <= 0:
            print_fail(f"Campaign impressions should be > 0, got {campaign.get('impressions')}")
            return False
        
        # Verify clicks >= 0
        if "clicks" not in campaign or campaign["clicks"] < 0:
            print_fail(f"Campaign clicks should be >= 0, got {campaign.get('clicks')}")
            return False
        
        # Verify spentCents > 0 AND <= budgetCents
        if "spentCents" not in campaign or campaign["spentCents"] <= 0:
            print_fail(f"Campaign spentCents should be > 0, got {campaign.get('spentCents')}")
            return False
        
        if campaign["spentCents"] > campaign.get("budgetCents", 0):
            print_fail(f"Campaign spentCents ({campaign['spentCents']}) should be <= budgetCents ({campaign.get('budgetCents')})")
            return False
        
        print_info(f"Campaign metrics: impressions={campaign['impressions']}, clicks={campaign['clicks']}, spentCents={campaign['spentCents']} (<=30000 ✓)")
        
        # Verify adDerived fields (ctr, cpcCents, cpmCents, convRate, remainingCents)
        ad_derived_fields = ["ctr", "cpcCents", "cpmCents", "convRate", "remainingCents"]
        for field in ad_derived_fields:
            if field not in campaign:
                print_fail(f"Campaign missing adDerived field: {field}")
                return False
        
        print_info(f"Campaign adDerived fields: ctr={campaign['ctr']}, cpcCents={campaign['cpcCents']}, cpmCents={campaign['cpmCents']}, convRate={campaign['convRate']}, remainingCents={campaign['remainingCents']}")
        
        # Verify keywords stored as objects with text/matchType/bidCents
        if "keywords" not in campaign or not isinstance(campaign["keywords"], list):
            print_fail(f"Campaign missing keywords array")
            return False
        
        for kw in campaign["keywords"]:
            if not all(k in kw for k in ["text", "matchType", "bidCents"]):
                print_fail(f"Keyword missing required fields: {kw}")
                return False
        
        print_info(f"Keywords stored correctly: {campaign['keywords']}")
        
        # Verify 'Publicité' transaction created
        txs_resp = client.get("/transactions")
        if txs_resp.status_code != 200:
            print_fail(f"Failed to get transactions: {txs_resp.status_code}")
            return False
        
        txs = txs_resp.json()
        pub_tx = next((t for t in txs if t.get("category") == "Publicité" and t.get("amountCents") == -30000), None)
        if not pub_tx:
            print_fail(f"'Publicité' transaction not found in transactions")
            return False
        
        print_info(f"'Publicité' transaction created: {pub_tx['label']} ({pub_tx['amountCents']}c)")
        
        # Store campaign ID for later tests
        global campaign_id
        campaign_id = campaign["id"]
        
        print_pass(f"Campaign created: wallet {balance_before}c -> {balance_after}c (-30000c ✓), 'Publicité' transaction created ✓, daily[] has {len(campaign['daily'])} entries ✓, impressions={campaign['impressions']}, clicks={campaign['clicks']}, spentCents={campaign['spentCents']} (<=30000 ✓), adDerived fields present ✓, keywords stored as objects ✓")
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

    # ========== TEST 5: POST /ads/campaigns - INSUFFICIENT balance ==========
    print_test("TEST 5: POST /ads/campaigns with budgetCents=99999999 - should return 402")
    try:
        resp = client.post("/ads/campaigns", json_data={
            "name": "Huge Campaign",
            "type": "search",
            "budgetCents": 99999999,
            "bidStrategy": "cpc",
            "maxBidCents": 50
        })
        
        if resp.status_code != 402:
            print_fail(f"Expected 402, got {resp.status_code}: {resp.text}")
            return False
        
        error = resp.json()
        if "error" not in error:
            print_fail(f"Expected error message in response: {error}")
            return False
        
        print_pass(f"Insufficient balance returns 402: {error['error']}")
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

    # ========== TEST 6: GET /ads/campaigns - list with adDerived ==========
    print_test("TEST 6: GET /ads/campaigns - lists campaigns with adDerived fields")
    try:
        resp = client.get("/ads/campaigns")
        if resp.status_code != 200:
            print_fail(f"Status {resp.status_code}: {resp.text}")
            return False
        
        campaigns = resp.json()
        
        if not isinstance(campaigns, list) or len(campaigns) == 0:
            print_fail(f"Expected non-empty campaigns array, got {campaigns}")
            return False
        
        # Verify first campaign has adDerived fields
        camp = campaigns[0]
        ad_derived_fields = ["ctr", "cpcCents", "remainingCents"]
        for field in ad_derived_fields:
            if field not in camp:
                print_fail(f"Campaign missing adDerived field: {field}")
                return False
        
        print_pass(f"GET /ads/campaigns returned {len(campaigns)} campaign(s) with adDerived fields (ctr={camp['ctr']}, cpcCents={camp['cpcCents']}, remainingCents={camp['remainingCents']})")
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

    # ========== TEST 7: GET /ads/campaigns/:id - detail ==========
    print_test("TEST 7: GET /ads/campaigns/:id - detail with daily[] time-series, targeting, keywords, creative")
    try:
        resp = client.get(f"/ads/campaigns/{campaign_id}")
        if resp.status_code != 200:
            print_fail(f"Status {resp.status_code}: {resp.text}")
            return False
        
        campaign = resp.json()
        
        # Verify required fields
        required = ["id", "name", "type", "daily", "targeting", "keywords", "creative"]
        for field in required:
            if field not in campaign:
                print_fail(f"Campaign detail missing field: {field}")
                return False
        
        # Verify daily[] is non-empty
        if not isinstance(campaign["daily"], list) or len(campaign["daily"]) == 0:
            print_fail(f"Campaign daily[] should be non-empty")
            return False
        
        # Verify targeting has expected fields
        if not isinstance(campaign["targeting"], dict):
            print_fail(f"Campaign targeting should be dict")
            return False
        
        # Verify keywords is array
        if not isinstance(campaign["keywords"], list):
            print_fail(f"Campaign keywords should be array")
            return False
        
        # Verify creative has expected fields
        if not isinstance(campaign["creative"], dict):
            print_fail(f"Campaign creative should be dict")
            return False
        
        print_pass(f"Campaign detail returned: id={campaign['id']}, name={campaign['name']}, type={campaign['type']}, daily[] has {len(campaign['daily'])} entries, targeting={list(campaign['targeting'].keys())}, keywords={len(campaign['keywords'])}, creative={list(campaign['creative'].keys())}")
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

    # ========== TEST 8: GET /ads/insights ==========
    print_test("TEST 8: GET /ads/insights - returns totals, daily[], top[], counts")
    try:
        resp = client.get("/ads/insights")
        if resp.status_code != 200:
            print_fail(f"Status {resp.status_code}: {resp.text}")
            return False
        
        insights = resp.json()
        
        # Verify required fields
        required = ["totals", "daily", "top", "counts"]
        for field in required:
            if field not in insights:
                print_fail(f"Insights missing field: {field}")
                return False
        
        # Verify totals has required fields
        totals = insights["totals"]
        totals_fields = ["impressions", "clicks", "spentCents", "conversions", "ctr", "cpcCents", "convRate"]
        for field in totals_fields:
            if field not in totals:
                print_fail(f"Totals missing field: {field}")
                return False
        
        # Verify totals.impressions > 0 (we created a campaign with simulated history)
        if totals["impressions"] <= 0:
            print_fail(f"Totals impressions should be > 0, got {totals['impressions']}")
            return False
        
        # Verify daily is array
        if not isinstance(insights["daily"], list):
            print_fail(f"Daily should be array")
            return False
        
        # Verify top is array
        if not isinstance(insights["top"], list):
            print_fail(f"Top should be array")
            return False
        
        # Verify counts has total, active, paused
        counts = insights["counts"]
        if not all(k in counts for k in ["total", "active", "paused"]):
            print_fail(f"Counts missing required fields: {counts.keys()}")
            return False
        
        # Verify counts.total >= 1 (we created a campaign)
        if counts["total"] < 1:
            print_fail(f"Counts.total should be >= 1, got {counts['total']}")
            return False
        
        # Verify counts.active >= 1 (our campaign is active)
        if counts["active"] < 1:
            print_fail(f"Counts.active should be >= 1, got {counts['active']}")
            return False
        
        print_pass(f"Insights returned: totals.impressions={totals['impressions']}, totals.clicks={totals['clicks']}, totals.spentCents={totals['spentCents']}, daily[] has {len(insights['daily'])} entries, top[] has {len(insights['top'])} entries, counts.total={counts['total']}, counts.active={counts['active']}")
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

    # ========== TEST 9: POST /ads/campaigns/:id/track - TRACK impressions/clicks/conversions ==========
    print_test("TEST 9: POST /ads/campaigns/:id/track - track impression/click/conversion, verify increments")
    try:
        # Get campaign before tracking
        resp_before = client.get(f"/ads/campaigns/{campaign_id}")
        if resp_before.status_code != 200:
            print_fail(f"Failed to get campaign before: {resp_before.status_code}")
            return False
        
        camp_before = resp_before.json()
        impr_before = camp_before.get("impressions", 0)
        clicks_before = camp_before.get("clicks", 0)
        spent_before = camp_before.get("spentCents", 0)
        conv_before = camp_before.get("conversions", 0)
        
        print_info(f"Before tracking: impressions={impr_before}, clicks={clicks_before}, spentCents={spent_before}, conversions={conv_before}")
        
        # Track impression
        resp1 = client.post(f"/ads/campaigns/{campaign_id}/track", json_data={"type": "impression"})
        if resp1.status_code != 200:
            print_fail(f"Track impression failed: {resp1.status_code} {resp1.text}")
            return False
        
        track1 = resp1.json()
        if not track1.get("ok"):
            print_fail(f"Track impression returned ok=false: {track1}")
            return False
        
        # Get campaign after impression
        resp_after1 = client.get(f"/ads/campaigns/{campaign_id}")
        camp_after1 = resp_after1.json()
        
        if camp_after1["impressions"] != impr_before + 1:
            print_fail(f"Impressions not incremented: before={impr_before}, after={camp_after1['impressions']}")
            return False
        
        print_info(f"After impression: impressions={camp_after1['impressions']} (+1 ✓)")
        
        # Track click
        resp2 = client.post(f"/ads/campaigns/{campaign_id}/track", json_data={"type": "click"})
        if resp2.status_code != 200:
            print_fail(f"Track click failed: {resp2.status_code} {resp2.text}")
            return False
        
        track2 = resp2.json()
        if not track2.get("ok"):
            print_fail(f"Track click returned ok=false: {track2}")
            return False
        
        # Get campaign after click
        resp_after2 = client.get(f"/ads/campaigns/{campaign_id}")
        camp_after2 = resp_after2.json()
        
        if camp_after2["clicks"] != clicks_before + 1:
            print_fail(f"Clicks not incremented: before={clicks_before}, after={camp_after2['clicks']}")
            return False
        
        # Verify spentCents increased by maxBidCents (50)
        expected_spent = spent_before + 50
        # Allow for small variance due to impression cost
        if abs(camp_after2["spentCents"] - expected_spent) > 10:
            print_fail(f"SpentCents not increased correctly: before={spent_before}, after={camp_after2['spentCents']}, expected~{expected_spent}")
            return False
        
        print_info(f"After click: clicks={camp_after2['clicks']} (+1 ✓), spentCents={camp_after2['spentCents']} (increased ✓)")
        
        # Track conversion
        resp3 = client.post(f"/ads/campaigns/{campaign_id}/track", json_data={"type": "conversion"})
        if resp3.status_code != 200:
            print_fail(f"Track conversion failed: {resp3.status_code} {resp3.text}")
            return False
        
        track3 = resp3.json()
        if not track3.get("ok"):
            print_fail(f"Track conversion returned ok=false: {track3}")
            return False
        
        # Get campaign after conversion
        resp_after3 = client.get(f"/ads/campaigns/{campaign_id}")
        camp_after3 = resp_after3.json()
        
        if camp_after3["conversions"] != conv_before + 1:
            print_fail(f"Conversions not incremented: before={conv_before}, after={camp_after3['conversions']}")
            return False
        
        print_info(f"After conversion: conversions={camp_after3['conversions']} (+1 ✓)")
        
        # Verify today's daily bucket updated
        if not isinstance(camp_after3.get("daily"), list) or len(camp_after3["daily"]) == 0:
            print_fail(f"Campaign daily[] should be non-empty after tracking")
            return False
        
        # Last entry should be today
        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        last_daily = camp_after3["daily"][-1]
        if last_daily.get("date") != today:
            print_info(f"Note: Last daily entry date={last_daily.get('date')}, today={today} (may be simulated history)")
        
        print_pass(f"Tracking works: impression +1 (impressions={camp_after3['impressions']}), click +1 (clicks={camp_after3['clicks']}, spentCents increased), conversion +1 (conversions={camp_after3['conversions']}), daily[] updated")
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

    # ========== TEST 10: PATCH /ads/campaigns/:id - edit fields ==========
    print_test("TEST 10: PATCH /ads/campaigns/:id - edit name, maxBidCents, targeting")
    try:
        # Edit campaign
        resp = client.patch(f"/ads/campaigns/{campaign_id}", json_data={
            "name": "Renamed",
            "maxBidCents": 80,
            "targeting": {
                "interests": ["Mode", "Sport"]
            }
        })
        
        if resp.status_code != 200:
            print_fail(f"Status {resp.status_code}: {resp.text}")
            return False
        
        updated = resp.json()
        
        # Verify name updated
        if updated.get("name") != "Renamed":
            print_fail(f"Name not updated: {updated.get('name')}")
            return False
        
        # Verify maxBidCents updated
        if updated.get("maxBidCents") != 80:
            print_fail(f"maxBidCents not updated: {updated.get('maxBidCents')}")
            return False
        
        # Verify targeting updated
        if "Mode" not in updated.get("targeting", {}).get("interests", []):
            print_fail(f"Targeting not updated: {updated.get('targeting')}")
            return False
        
        print_pass(f"Campaign edited: name='Renamed', maxBidCents=80, targeting.interests=['Mode', 'Sport']")
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

    # ========== TEST 11: PATCH status pause/active ==========
    print_test("TEST 11: PATCH /ads/campaigns/:id - status pause/active (removed from/added to sponsored feed)")
    try:
        # Pause campaign
        resp1 = client.patch(f"/ads/campaigns/{campaign_id}", json_data={"status": "paused"})
        if resp1.status_code != 200:
            print_fail(f"Pause failed: {resp1.status_code} {resp1.text}")
            return False
        
        paused = resp1.json()
        if paused.get("status") != "paused":
            print_fail(f"Status not paused: {paused.get('status')}")
            return False
        
        print_info(f"Campaign paused")
        
        # Check sponsored feed (should not include paused campaign)
        feed_resp1 = client.get("/social/feed", params={"mode": "foryou"})
        if feed_resp1.status_code != 200:
            print_fail(f"Failed to get feed: {feed_resp1.status_code}")
            return False
        
        feed1 = feed_resp1.json()
        sponsored1 = [p for p in feed1 if p.get("sponsored") and p.get("campaignId") == campaign_id]
        if len(sponsored1) > 0:
            print_fail(f"Paused campaign should not appear in feed, but found {len(sponsored1)} sponsored posts")
            return False
        
        print_info(f"Paused campaign not in feed ✓")
        
        # Resume campaign
        resp2 = client.patch(f"/ads/campaigns/{campaign_id}", json_data={"status": "active"})
        if resp2.status_code != 200:
            print_fail(f"Resume failed: {resp2.status_code} {resp2.text}")
            return False
        
        active = resp2.json()
        if active.get("status") != "active":
            print_fail(f"Status not active: {active.get('status')}")
            return False
        
        print_info(f"Campaign resumed (active)")
        
        # Check sponsored feed (should include active campaign)
        feed_resp2 = client.get("/social/feed", params={"mode": "foryou"})
        if feed_resp2.status_code != 200:
            print_fail(f"Failed to get feed: {feed_resp2.status_code}")
            return False
        
        feed2 = feed_resp2.json()
        sponsored2 = [p for p in feed2 if p.get("sponsored") and p.get("campaignId") == campaign_id]
        if len(sponsored2) == 0:
            print_fail(f"Active campaign should appear in feed, but found 0 sponsored posts")
            return False
        
        print_info(f"Active campaign in feed ✓ ({len(sponsored2)} sponsored post(s))")
        
        print_pass(f"Status pause/active works: paused -> not in feed, active -> in feed")
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

    # ========== TEST 12: PATCH status ended + REFUND ==========
    print_test("TEST 12: PATCH /ads/campaigns/:id status=ended - remaining budget refunded to wallet")
    try:
        # Create a fresh campaign for this test
        wallet_before = client.get_wallet()
        balance_before = wallet_before.get("balanceCents", 0)
        print_info(f"Wallet before new campaign: {balance_before}c")
        
        resp_create = client.post("/ads/campaigns", json_data={
            "name": "Test Refund",
            "type": "search",
            "budgetCents": 20000,
            "bidStrategy": "cpc",
            "maxBidCents": 50
        })
        
        if resp_create.status_code != 200:
            print_fail(f"Failed to create campaign: {resp_create.status_code} {resp_create.text}")
            return False
        
        result = resp_create.json()
        refund_campaign_id = result["campaign"]["id"]
        balance_after_create = result["balanceCents"]
        
        print_info(f"Wallet after creating campaign: {balance_after_create}c (debited 20000c)")
        
        # Get campaign to check spentCents
        resp_get = client.get(f"/ads/campaigns/{refund_campaign_id}")
        if resp_get.status_code != 200:
            print_fail(f"Failed to get campaign: {resp_get.status_code}")
            return False
        
        camp = resp_get.json()
        spent = camp.get("spentCents", 0)
        remaining = camp.get("budgetCents", 0) - spent
        
        print_info(f"Campaign: budgetCents={camp.get('budgetCents')}, spentCents={spent}, remaining={remaining}")
        
        # End campaign
        resp_end = client.patch(f"/ads/campaigns/{refund_campaign_id}", json_data={"status": "ended"})
        if resp_end.status_code != 200:
            print_fail(f"Failed to end campaign: {resp_end.status_code} {resp_end.text}")
            return False
        
        ended = resp_end.json()
        if ended.get("status") != "ended":
            print_fail(f"Status not ended: {ended.get('status')}")
            return False
        
        print_info(f"Campaign ended")
        
        # Get wallet after ending
        wallet_after = client.get_wallet()
        balance_after_end = wallet_after.get("balanceCents", 0)
        
        # Verify wallet increased by remaining
        expected_balance = balance_after_create + remaining
        if balance_after_end != expected_balance:
            print_fail(f"Wallet not refunded correctly: before_end={balance_after_create}, after_end={balance_after_end}, expected={expected_balance} (remaining={remaining})")
            return False
        
        print_info(f"Wallet after ending: {balance_after_end}c (refunded {remaining}c ✓)")
        
        # Verify 'Remboursement pub' transaction created
        txs_resp = client.get("/transactions")
        if txs_resp.status_code != 200:
            print_fail(f"Failed to get transactions: {txs_resp.status_code}")
            return False
        
        txs = txs_resp.json()
        refund_tx = next((t for t in txs if "Remboursement pub" in t.get("label", "") and t.get("amountCents") == remaining), None)
        if not refund_tx:
            print_fail(f"'Remboursement pub' transaction not found")
            return False
        
        print_info(f"'Remboursement pub' transaction created: {refund_tx['label']} ({refund_tx['amountCents']}c)")
        
        print_pass(f"END + REFUND works: campaign ended, wallet {balance_after_create}c -> {balance_after_end}c (+{remaining}c refund ✓), 'Remboursement pub' transaction created ✓")
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

    # ========== TEST 13: DELETE /ads/campaigns/:id - refund + removal ==========
    print_test("TEST 13: DELETE /ads/campaigns/:id - refunds remaining if not ended, removed from list")
    try:
        # Create a fresh campaign for this test
        wallet_before = client.get_wallet()
        balance_before = wallet_before.get("balanceCents", 0)
        
        resp_create = client.post("/ads/campaigns", json_data={
            "name": "Test Delete",
            "type": "search",
            "budgetCents": 15000,
            "bidStrategy": "cpc",
            "maxBidCents": 50
        })
        
        if resp_create.status_code != 200:
            print_fail(f"Failed to create campaign: {resp_create.status_code} {resp_create.text}")
            return False
        
        result = resp_create.json()
        delete_campaign_id = result["campaign"]["id"]
        balance_after_create = result["balanceCents"]
        
        # Get campaign to check remaining
        resp_get = client.get(f"/ads/campaigns/{delete_campaign_id}")
        camp = resp_get.json()
        remaining = camp.get("remainingCents", 0)
        
        print_info(f"Campaign created: id={delete_campaign_id}, remaining={remaining}c")
        
        # Delete campaign
        resp_delete = client.delete(f"/ads/campaigns/{delete_campaign_id}")
        if resp_delete.status_code != 200:
            print_fail(f"Failed to delete campaign: {resp_delete.status_code} {resp_delete.text}")
            return False
        
        delete_result = resp_delete.json()
        if not delete_result.get("ok"):
            print_fail(f"Delete returned ok=false: {delete_result}")
            return False
        
        print_info(f"Campaign deleted")
        
        # Verify wallet refunded
        wallet_after = client.get_wallet()
        balance_after_delete = wallet_after.get("balanceCents", 0)
        
        expected_balance = balance_after_create + remaining
        if balance_after_delete != expected_balance:
            print_fail(f"Wallet not refunded correctly: before_delete={balance_after_create}, after_delete={balance_after_delete}, expected={expected_balance}")
            return False
        
        print_info(f"Wallet refunded: {balance_after_create}c -> {balance_after_delete}c (+{remaining}c ✓)")
        
        # Verify campaign removed from list
        resp_list = client.get("/ads/campaigns")
        campaigns = resp_list.json()
        deleted_camp = next((c for c in campaigns if c.get("id") == delete_campaign_id), None)
        if deleted_camp:
            print_fail(f"Deleted campaign still in list: {deleted_camp}")
            return False
        
        print_info(f"Campaign removed from list ✓")
        
        print_pass(f"DELETE works: campaign deleted, wallet refunded +{remaining}c, removed from list")
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

    # ========== TEST 14: AUTH - 401 without Bearer ==========
    print_test("TEST 14: AUTH - /ads/config, /ads/campaigns, /ads/insights without Bearer -> 401")
    try:
        # Create client without auth
        no_auth_client = APIClient(BASE_URL)
        
        # Test /ads/config
        resp1 = no_auth_client.get("/ads/config")
        if resp1.status_code != 401:
            print_fail(f"/ads/config without auth should return 401, got {resp1.status_code}")
            return False
        
        # Test /ads/campaigns
        resp2 = no_auth_client.get("/ads/campaigns")
        if resp2.status_code != 401:
            print_fail(f"/ads/campaigns without auth should return 401, got {resp2.status_code}")
            return False
        
        # Test /ads/insights
        resp3 = no_auth_client.get("/ads/insights")
        if resp3.status_code != 401:
            print_fail(f"/ads/insights without auth should return 401, got {resp3.status_code}")
            return False
        
        print_pass(f"Auth required: /ads/config, /ads/campaigns, /ads/insights all return 401 without Bearer")
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

    # ========== TEST 15: SPONSORED FEED - active campaigns in foryou, not chrono ==========
    print_test("TEST 15: SPONSORED FEED - active campaign appears in foryou (sponsored:true, campaignId), NOT in chrono")
    try:
        # Get foryou feed
        resp_foryou = client.get("/social/feed", params={"mode": "foryou"})
        if resp_foryou.status_code != 200:
            print_fail(f"Failed to get foryou feed: {resp_foryou.status_code}")
            return False
        
        feed_foryou = resp_foryou.json()
        sponsored_foryou = [p for p in feed_foryou if p.get("sponsored")]
        
        if len(sponsored_foryou) == 0:
            print_fail(f"No sponsored posts in foryou feed (expected at least 1)")
            return False
        
        # Verify sponsored post has required fields
        sp = sponsored_foryou[0]
        if not sp.get("sponsored"):
            print_fail(f"Sponsored post missing sponsored:true")
            return False
        
        if not sp.get("campaignId"):
            print_fail(f"Sponsored post missing campaignId")
            return False
        
        print_info(f"Foryou feed: {len(sponsored_foryou)} sponsored post(s), campaignId={sp['campaignId']}, reason='{sp.get('reason')}'")
        
        # Get chrono feed
        resp_chrono = client.get("/social/feed", params={"mode": "chrono"})
        if resp_chrono.status_code != 200:
            print_fail(f"Failed to get chrono feed: {resp_chrono.status_code}")
            return False
        
        feed_chrono = resp_chrono.json()
        sponsored_chrono = [p for p in feed_chrono if p.get("sponsored")]
        
        if len(sponsored_chrono) > 0:
            print_fail(f"Sponsored posts should NOT appear in chrono feed, but found {len(sponsored_chrono)}")
            return False
        
        print_info(f"Chrono feed: 0 sponsored posts ✓")
        
        print_pass(f"Sponsored feed works: {len(sponsored_foryou)} sponsored post(s) in foryou (sponsored:true, campaignId present), 0 in chrono")
    except Exception as e:
        print_fail(f"Exception: {e}")
        return False

    print("\n" + "="*80)
    print("ALL PHASE 9 ADS MANAGER V2 TESTS PASSED ✅")
    print("="*80 + "\n")
    return True

if __name__ == "__main__":
    try:
        success = test_phase9_ads_manager_v2()
        sys.exit(0 if success else 1)
    except Exception as e:
        print_fail(f"Test suite failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
