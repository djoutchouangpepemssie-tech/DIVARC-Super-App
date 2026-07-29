#!/usr/bin/env python3
"""
DIVARC Hub Administratif & Santé Backend Test - PHASE 7
Tests all admin endpoints with comprehensive verification
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

def test_phase7_admin_hub():
    """Test PHASE 7: Hub administratif & santé - connectors + documents + accounting"""
    
    log("=" * 80)
    log("PHASE 7: HUB ADMINISTRATIF & SANTÉ - COMPREHENSIVE BACKEND TEST")
    log("=" * 80)
    
    # ========================================================================
    # SETUP: Create user hub7@divarc.fr
    # ========================================================================
    log("\n[SETUP] Creating user hub7@divarc.fr")
    token, user = create_user("hub7@divarc.fr", "Hub Seven")
    headers = {"Authorization": f"Bearer {token}"}
    
    # ========================================================================
    # TEST 1: GET /api/admin/connectors - Verify 5 connectors with all fields
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 1: GET /api/admin/connectors - Verify 5 connectors with all required fields")
    log("=" * 80)
    
    res = requests.get(f"{BASE_URL}/admin/connectors", headers=headers)
    assert res.status_code == 200, f"GET /admin/connectors failed: {res.status_code} {res.text}"
    connectors = res.json()
    
    log(f"✓ GET /admin/connectors returned {len(connectors)} connectors")
    assert len(connectors) == 5, f"Expected 5 connectors, got {len(connectors)}"
    
    # Verify exact connector IDs
    expected_ids = ['impots', 'ameli', 'caf', 'ants', 'assurance']
    actual_ids = [c['id'] for c in connectors]
    assert set(actual_ids) == set(expected_ids), f"Expected IDs {expected_ids}, got {actual_ids}"
    
    log(f"✓ All 5 expected connectors present: {', '.join(expected_ids)}")
    
    # Verify each connector has required fields
    required_fields = ['id', 'name', 'cat', 'emoji', 'color', 'desc', 'scopes', 'sensitive', 'connected', 'pseudonym', 'since', 'data']
    for conn in connectors:
        for field in required_fields:
            assert field in conn, f"Connector {conn.get('name')} missing field: {field}"
        
        # Verify initial state: connected=false, pseudonym=null, since=null, data=[]
        assert conn['connected'] == False, f"Connector {conn['name']} should have connected=false initially"
        assert conn['pseudonym'] == None, f"Connector {conn['name']} should have pseudonym=null initially"
        assert conn['since'] == None, f"Connector {conn['name']} should have since=null initially"
        assert conn['data'] == [], f"Connector {conn['name']} should have data=[] initially"
        
        # Verify scopes is an array
        assert isinstance(conn['scopes'], list), f"Connector {conn['name']} scopes should be an array"
        
        # Verify sensitive is boolean
        assert isinstance(conn['sensitive'], bool), f"Connector {conn['name']} sensitive should be boolean"
    
    log(f"✓ All 5 connectors have required fields: {', '.join(required_fields)}")
    log(f"✓ All connectors have connected=false, pseudonym=null, since=null, data=[] initially")
    
    # Find ameli and verify sensitive=true
    ameli = next((c for c in connectors if c['id'] == 'ameli'), None)
    assert ameli is not None, "Ameli connector not found"
    assert ameli['sensitive'] == True, f"Ameli should have sensitive=true, got {ameli['sensitive']}"
    
    log(f"✓ Ameli connector has sensitive=true")
    
    # Find impots for later tests
    impots = next((c for c in connectors if c['id'] == 'impots'), None)
    assert impots is not None, "Impots connector not found"
    
    log(f"✓ Found Impots: {impots['name']} (scopes: {impots['scopes']})")
    
    log("\n✅ TEST 1 PASSED: 5 connectors with all required fields verified")
    
    # ========================================================================
    # TEST 2: POST /api/admin/connectors/impots/connect - Create connection
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 2: POST /api/admin/connectors/impots/connect - Create connection")
    log("=" * 80)
    
    res = requests.post(f"{BASE_URL}/admin/connectors/impots/connect", headers=headers)
    assert res.status_code == 200, f"POST /admin/connectors/impots/connect failed: {res.status_code} {res.text}"
    data = res.json()
    
    assert "connection" in data, f"No connection in response: {data}"
    connection = data["connection"]
    
    log(f"✓ Connection created:")
    log(f"  - Connector ID: {connection.get('connectorId')}")
    log(f"  - Name: {connection.get('name')}")
    log(f"  - Pseudonym: {connection.get('pseudonym')}")
    log(f"  - Scopes: {connection.get('scopes')}")
    log(f"  - Sensitive: {connection.get('sensitive')}")
    log(f"  - Data length: {len(connection.get('data', []))}")
    
    # Verify pseudonym format: eidas-[0-9a-f]{6}
    pseudonym = connection.get('pseudonym')
    assert pseudonym is not None, "Pseudonym is None"
    
    pseudonym_pattern = r'^eidas-[0-9a-f]{6}$'
    assert re.match(pseudonym_pattern, pseudonym), f"Pseudonym '{pseudonym}' does not match pattern {pseudonym_pattern}"
    
    log(f"✓ Pseudonym matches pattern /^eidas-[0-9a-f]{{6}}$/")
    
    # Verify scopes match connector definition
    assert connection.get('scopes') == impots['scopes'], f"Scopes {connection.get('scopes')} do not match connector scopes {impots['scopes']}"
    
    log(f"✓ Scopes match connector definition: {impots['scopes']}")
    
    # Verify data is NON-EMPTY (mock preview data)
    data_items = connection.get('data', [])
    assert len(data_items) > 0, f"Data should be non-empty, got {len(data_items)} items"
    
    log(f"✓ Data is non-empty: {len(data_items)} items")
    
    # Verify data structure (each item should have label and value)
    for item in data_items:
        assert 'label' in item, f"Data item missing label: {item}"
        assert 'value' in item, f"Data item missing value: {item}"
        log(f"  - {item['label']}: {item['value']}")
    
    log(f"✓ Data items have correct structure (label, value)")
    
    # Store pseudonym for later verification
    impots_pseudonym = pseudonym
    
    log("\n✅ TEST 2 PASSED: Connection created with eidas pseudonym and non-empty data")
    
    # ========================================================================
    # TEST 3: GET /api/admin/connectors - Verify impots connected with data
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 3: GET /api/admin/connectors - Verify impots shows connected:true with data")
    log("=" * 80)
    
    res = requests.get(f"{BASE_URL}/admin/connectors", headers=headers)
    assert res.status_code == 200, f"GET /admin/connectors failed: {res.status_code} {res.text}"
    connectors = res.json()
    
    impots_conn = next((c for c in connectors if c['id'] == 'impots'), None)
    assert impots_conn is not None, "Impots connector not found"
    
    log(f"✓ Impots connector:")
    log(f"  - Connected: {impots_conn['connected']}")
    log(f"  - Pseudonym: {impots_conn['pseudonym']}")
    log(f"  - Data length: {len(impots_conn.get('data', []))}")
    
    assert impots_conn['connected'] == True, f"Impots should have connected=true, got {impots_conn['connected']}"
    assert impots_conn['pseudonym'] == impots_pseudonym, f"Impots pseudonym {impots_conn['pseudonym']} does not match {impots_pseudonym}"
    assert len(impots_conn.get('data', [])) > 0, f"Impots data should be non-empty"
    
    log(f"✓ Impots now shows connected=true with pseudonym {impots_pseudonym} and non-empty data")
    
    log("\n✅ TEST 3 PASSED: Connected flag, pseudonym, and data correctly reflected")
    
    # ========================================================================
    # TEST 4: IDEMPOTENT - POST /api/admin/connectors/impots/connect again
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 4: IDEMPOTENT - POST /api/admin/connectors/impots/connect again (should return existing)")
    log("=" * 80)
    
    res = requests.post(f"{BASE_URL}/admin/connectors/impots/connect", headers=headers)
    assert res.status_code == 200, f"POST /admin/connectors/impots/connect failed: {res.status_code} {res.text}"
    data = res.json()
    
    assert "connection" in data, f"No connection in response: {data}"
    assert "existing" in data, f"No existing flag in response: {data}"
    assert data["existing"] == True, f"Expected existing=true, got {data.get('existing')}"
    
    connection = data["connection"]
    log(f"✓ Connection returned with existing=true")
    log(f"  - Pseudonym: {connection.get('pseudonym')}")
    
    # Verify SAME pseudonym (no duplicate created)
    assert connection.get('pseudonym') == impots_pseudonym, f"Pseudonym changed! Expected {impots_pseudonym}, got {connection.get('pseudonym')}"
    
    log(f"✓ Pseudonym unchanged: {impots_pseudonym} (no duplicate created)")
    
    log("\n✅ TEST 4 PASSED: Idempotent connect - same pseudonym, no duplicate")
    
    # ========================================================================
    # TEST 5: INVALID - POST /api/admin/connectors/doesnotexist/connect
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 5: INVALID - POST /api/admin/connectors/doesnotexist/connect (should return 404)")
    log("=" * 80)
    
    res = requests.post(f"{BASE_URL}/admin/connectors/doesnotexist/connect", headers=headers)
    assert res.status_code == 404, f"Expected 404 for invalid connector, got {res.status_code}: {res.text}"
    
    log(f"✓ Correctly returned 404 for non-existent connector")
    
    log("\n✅ TEST 5 PASSED: Invalid connector returns 404")
    
    # ========================================================================
    # TEST 6: DISCONNECT - POST /api/admin/connectors/impots/disconnect
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 6: DISCONNECT - POST /api/admin/connectors/impots/disconnect")
    log("=" * 80)
    
    res = requests.post(f"{BASE_URL}/admin/connectors/impots/disconnect", headers=headers)
    assert res.status_code == 200, f"POST /admin/connectors/impots/disconnect failed: {res.status_code} {res.text}"
    data = res.json()
    
    assert data.get("ok") == True, f"Expected ok=true, got {data}"
    log(f"✓ Disconnect returned ok=true")
    
    # Verify GET /api/admin/connectors shows impots connected=false
    res = requests.get(f"{BASE_URL}/admin/connectors", headers=headers)
    assert res.status_code == 200, f"GET /admin/connectors failed: {res.status_code} {res.text}"
    connectors = res.json()
    
    impots_conn = next((c for c in connectors if c['id'] == 'impots'), None)
    assert impots_conn is not None, "Impots connector not found"
    
    log(f"✓ Impots connector after disconnect:")
    log(f"  - Connected: {impots_conn['connected']}")
    
    assert impots_conn['connected'] == False, f"Impots should have connected=false after disconnect, got {impots_conn['connected']}"
    
    log(f"✓ Impots now shows connected=false")
    
    log("\n✅ TEST 6 PASSED: Disconnect working correctly")
    
    # ========================================================================
    # TEST 7: GET /api/admin/documents - Auto-seed 2 docs on first call
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 7: GET /api/admin/documents - Auto-seed 2 docs on first call, no duplicates on second")
    log("=" * 80)
    
    # First call - should auto-seed 2 documents
    res = requests.get(f"{BASE_URL}/admin/documents", headers=headers)
    assert res.status_code == 200, f"GET /admin/documents failed: {res.status_code} {res.text}"
    docs_first = res.json()
    
    log(f"✓ First GET /admin/documents returned {len(docs_first)} documents")
    assert len(docs_first) == 2, f"Expected 2 auto-seeded documents, got {len(docs_first)}"
    
    # Verify the 2 seeded documents
    expected_titles = ['Avis d\u2019imposition 2024', 'Attestation carte Vitale']
    expected_issuers = ['DGFiP', 'Ameli']
    
    actual_titles = [d['title'] for d in docs_first]
    actual_issuers = [d['issuer'] for d in docs_first]
    
    assert 'Avis d\u2019imposition 2024' in actual_titles, f"Expected 'Avis d'imposition 2024' in titles, got {actual_titles}"
    assert 'Attestation carte Vitale' in actual_titles, f"Expected 'Attestation carte Vitale' in titles, got {actual_titles}"
    assert 'DGFiP' in actual_issuers, f"Expected 'DGFiP' in issuers, got {actual_issuers}"
    assert 'Ameli' in actual_issuers, f"Expected 'Ameli' in issuers, got {actual_issuers}"
    
    log(f"✓ Auto-seeded documents verified:")
    for doc in docs_first:
        log(f"  - {doc['title']} (issuer: {doc['issuer']}, encrypted: {doc['encrypted']}, shared: {doc['shared']})")
        
        # Verify document structure
        assert 'id' in doc, f"Document missing id: {doc}"
        assert 'title' in doc, f"Document missing title: {doc}"
        assert 'category' in doc, f"Document missing category: {doc}"
        assert 'issuer' in doc, f"Document missing issuer: {doc}"
        assert 'emoji' in doc, f"Document missing emoji: {doc}"
        assert 'encrypted' in doc, f"Document missing encrypted: {doc}"
        assert 'shared' in doc, f"Document missing shared: {doc}"
        assert 'createdAt' in doc, f"Document missing createdAt: {doc}"
        
        # Verify encrypted=true, shared=false
        assert doc['encrypted'] == True, f"Document should have encrypted=true, got {doc['encrypted']}"
        assert doc['shared'] == False, f"Document should have shared=false initially, got {doc['shared']}"
    
    log(f"✓ All documents have encrypted=true and shared=false")
    
    # Verify sorted by createdAt desc (most recent first)
    # Since they're created at the same time, just verify we have 2 docs
    
    # Second call - should NOT re-seed (still 2 docs, no duplicates)
    res = requests.get(f"{BASE_URL}/admin/documents", headers=headers)
    assert res.status_code == 200, f"GET /admin/documents failed: {res.status_code} {res.text}"
    docs_second = res.json()
    
    log(f"✓ Second GET /admin/documents returned {len(docs_second)} documents")
    assert len(docs_second) == 2, f"Expected 2 documents (no re-seeding), got {len(docs_second)}"
    
    # Verify same document IDs (no duplicates)
    first_ids = set(d['id'] for d in docs_first)
    second_ids = set(d['id'] for d in docs_second)
    assert first_ids == second_ids, f"Document IDs changed between calls (duplicates created)"
    
    log(f"✓ Second call did NOT re-seed (same 2 documents, no duplicates)")
    
    log("\n✅ TEST 7 PASSED: Auto-seed working correctly, no duplicates on second call")
    
    # ========================================================================
    # TEST 8: POST /api/admin/documents - Create encrypted document
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 8: POST /api/admin/documents - Create encrypted document")
    log("=" * 80)
    
    new_doc_data = {
        "title": "Relevé de compte bancaire",
        "category": "Finance",
        "issuer": "Ma Banque",
        "emoji": "🏦"
    }
    
    res = requests.post(f"{BASE_URL}/admin/documents", headers=headers, json=new_doc_data)
    assert res.status_code == 200, f"POST /admin/documents failed: {res.status_code} {res.text}"
    new_doc = res.json()
    
    log(f"✓ Document created:")
    log(f"  - ID: {new_doc.get('id')}")
    log(f"  - Title: {new_doc.get('title')}")
    log(f"  - Category: {new_doc.get('category')}")
    log(f"  - Issuer: {new_doc.get('issuer')}")
    log(f"  - Emoji: {new_doc.get('emoji')}")
    log(f"  - Encrypted: {new_doc.get('encrypted')}")
    log(f"  - Shared: {new_doc.get('shared')}")
    
    # Verify document fields
    assert new_doc.get('id') is not None, "Document missing id"
    assert new_doc.get('title') == new_doc_data['title'], f"Title mismatch"
    assert new_doc.get('category') == new_doc_data['category'], f"Category mismatch"
    assert new_doc.get('issuer') == new_doc_data['issuer'], f"Issuer mismatch"
    assert new_doc.get('emoji') == new_doc_data['emoji'], f"Emoji mismatch"
    assert new_doc.get('encrypted') == True, f"Document should have encrypted=true"
    assert new_doc.get('shared') == False, f"Document should have shared=false initially"
    
    log(f"✓ Document created with encrypted=true and shared=false")
    
    # Verify document appears in GET /admin/documents
    res = requests.get(f"{BASE_URL}/admin/documents", headers=headers)
    assert res.status_code == 200, f"GET /admin/documents failed: {res.status_code} {res.text}"
    docs = res.json()
    
    log(f"✓ GET /admin/documents now returns {len(docs)} documents")
    assert len(docs) == 3, f"Expected 3 documents (2 seeded + 1 created), got {len(docs)}"
    
    # Verify new document is in the list
    new_doc_found = any(d['id'] == new_doc['id'] for d in docs)
    assert new_doc_found, f"New document not found in list"
    
    log(f"✓ New document appears in GET /admin/documents")
    
    # Store document ID for later tests
    doc_id = new_doc['id']
    
    log("\n✅ TEST 8 PASSED: Document creation working correctly")
    
    # ========================================================================
    # TEST 9: POST /api/admin/documents/:id/share - Share document
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 9: POST /api/admin/documents/:id/share - Share document")
    log("=" * 80)
    
    share_data = {"hours": 24}
    
    res = requests.post(f"{BASE_URL}/admin/documents/{doc_id}/share", headers=headers, json=share_data)
    assert res.status_code == 200, f"POST /admin/documents/{doc_id}/share failed: {res.status_code} {res.text}"
    share_result = res.json()
    
    log(f"✓ Share result:")
    log(f"  - Shared: {share_result.get('shared')}")
    log(f"  - Share Token: {share_result.get('shareToken')}")
    log(f"  - Expires At: {share_result.get('expiresAt')}")
    
    # Verify share response
    assert share_result.get('shared') == True, f"Expected shared=true, got {share_result.get('shared')}"
    assert share_result.get('shareToken') is not None, f"Share token is None"
    assert share_result.get('expiresAt') is not None, f"Expires at is None"
    
    log(f"✓ Share returned shared=true with shareToken and expiresAt")
    
    share_token = share_result.get('shareToken')
    
    # Verify GET /admin/documents shows document as shared
    res = requests.get(f"{BASE_URL}/admin/documents", headers=headers)
    assert res.status_code == 200, f"GET /admin/documents failed: {res.status_code} {res.text}"
    docs = res.json()
    
    shared_doc = next((d for d in docs if d['id'] == doc_id), None)
    assert shared_doc is not None, f"Document {doc_id} not found"
    
    log(f"✓ Document after share:")
    log(f"  - Shared: {shared_doc.get('shared')}")
    log(f"  - Share Token: {shared_doc.get('shareToken')}")
    
    assert shared_doc.get('shared') == True, f"Document should have shared=true, got {shared_doc.get('shared')}"
    assert shared_doc.get('shareToken') == share_token, f"Share token mismatch"
    
    log(f"✓ GET /admin/documents shows document with shared=true and shareToken")
    
    log("\n✅ TEST 9 PASSED: Document sharing working correctly")
    
    # ========================================================================
    # TEST 10: POST /api/admin/documents/:id/unshare - Unshare document
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 10: POST /api/admin/documents/:id/unshare - Unshare document")
    log("=" * 80)
    
    res = requests.post(f"{BASE_URL}/admin/documents/{doc_id}/unshare", headers=headers)
    assert res.status_code == 200, f"POST /admin/documents/{doc_id}/unshare failed: {res.status_code} {res.text}"
    unshare_result = res.json()
    
    log(f"✓ Unshare result:")
    log(f"  - Shared: {unshare_result.get('shared')}")
    
    assert unshare_result.get('shared') == False, f"Expected shared=false, got {unshare_result.get('shared')}"
    
    log(f"✓ Unshare returned shared=false")
    
    # Verify GET /admin/documents shows document as not shared
    res = requests.get(f"{BASE_URL}/admin/documents", headers=headers)
    assert res.status_code == 200, f"GET /admin/documents failed: {res.status_code} {res.text}"
    docs = res.json()
    
    unshared_doc = next((d for d in docs if d['id'] == doc_id), None)
    assert unshared_doc is not None, f"Document {doc_id} not found"
    
    log(f"✓ Document after unshare:")
    log(f"  - Shared: {unshared_doc.get('shared')}")
    
    assert unshared_doc.get('shared') == False, f"Document should have shared=false, got {unshared_doc.get('shared')}"
    
    log(f"✓ GET /admin/documents shows document with shared=false")
    
    log("\n✅ TEST 10 PASSED: Document unsharing working correctly")
    
    # ========================================================================
    # TEST 11: DELETE /api/admin/documents/:id - Delete document
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 11: DELETE /api/admin/documents/:id - Delete document")
    log("=" * 80)
    
    res = requests.delete(f"{BASE_URL}/admin/documents/{doc_id}", headers=headers)
    assert res.status_code == 200, f"DELETE /admin/documents/{doc_id} failed: {res.status_code} {res.text}"
    delete_result = res.json()
    
    log(f"✓ Delete result:")
    log(f"  - OK: {delete_result.get('ok')}")
    
    assert delete_result.get('ok') == True, f"Expected ok=true, got {delete_result.get('ok')}"
    
    log(f"✓ Delete returned ok=true")
    
    # Verify document removed from GET /admin/documents
    res = requests.get(f"{BASE_URL}/admin/documents", headers=headers)
    assert res.status_code == 200, f"GET /admin/documents failed: {res.status_code} {res.text}"
    docs = res.json()
    
    log(f"✓ GET /admin/documents now returns {len(docs)} documents")
    assert len(docs) == 2, f"Expected 2 documents (deleted 1), got {len(docs)}"
    
    # Verify deleted document is NOT in the list
    deleted_doc_found = any(d['id'] == doc_id for d in docs)
    assert not deleted_doc_found, f"Deleted document still found in list"
    
    log(f"✓ Deleted document removed from GET /admin/documents")
    
    log("\n✅ TEST 11 PASSED: Document deletion working correctly")
    
    # ========================================================================
    # TEST 12: GET /api/admin/accounting - Verify income/expense/net/categories
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 12: GET /api/admin/accounting - Verify income/expense/net/categories")
    log("=" * 80)
    
    res = requests.get(f"{BASE_URL}/admin/accounting", headers=headers)
    assert res.status_code == 200, f"GET /admin/accounting failed: {res.status_code} {res.text}"
    accounting = res.json()
    
    log(f"✓ Accounting data:")
    log(f"  - Income Cents: {accounting.get('incomeCents')}")
    log(f"  - Expense Cents: {accounting.get('expenseCents')}")
    log(f"  - Net Cents: {accounting.get('netCents')}")
    log(f"  - Categories: {len(accounting.get('categories', []))} items")
    log(f"  - Transaction Count: {accounting.get('count')}")
    
    # Verify required fields
    assert 'incomeCents' in accounting, "Missing incomeCents"
    assert 'expenseCents' in accounting, "Missing expenseCents"
    assert 'netCents' in accounting, "Missing netCents"
    assert 'categories' in accounting, "Missing categories"
    assert 'count' in accounting, "Missing count"
    
    log(f"✓ All required fields present")
    
    # Verify netCents == incomeCents - expenseCents
    income = accounting.get('incomeCents')
    expense = accounting.get('expenseCents')
    net = accounting.get('netCents')
    
    expected_net = income - expense
    assert net == expected_net, f"Net cents mismatch: expected {expected_net}, got {net}"
    
    log(f"✓ Net cents calculation correct: {income} - {expense} = {net}")
    
    # Verify new users get welcome transaction (+480000c income)
    assert income >= 480000, f"Income should be >= 480000 (welcome transaction), got {income}"
    
    log(f"✓ Income >= 480000 (welcome transaction present)")
    
    # Verify categories structure
    categories = accounting.get('categories', [])
    assert isinstance(categories, list), "Categories should be an array"
    
    if len(categories) > 0:
        log(f"✓ Categories (top {len(categories)}):")
        for cat in categories:
            assert 'name' in cat, f"Category missing name: {cat}"
            assert 'amountCents' in cat, f"Category missing amountCents: {cat}"
            log(f"  - {cat['name']}: {cat['amountCents']} cents")
        
        # Verify sorted desc (highest amount first)
        amounts = [c['amountCents'] for c in categories]
        assert amounts == sorted(amounts, reverse=True), f"Categories not sorted desc by amountCents"
        
        log(f"✓ Categories sorted desc by amountCents")
    else:
        log(f"✓ No expense categories yet (expected for new user)")
    
    log("\n✅ TEST 12 PASSED: Accounting endpoint working correctly")
    
    # ========================================================================
    # TEST 13: AUTH - All /admin/* endpoints return 401 without Bearer token
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 13: AUTH - All /admin/* endpoints return 401 without Bearer token")
    log("=" * 80)
    
    # Test without headers (no Bearer token)
    endpoints_to_test = [
        ("GET", f"{BASE_URL}/admin/connectors"),
        ("POST", f"{BASE_URL}/admin/connectors/impots/connect"),
        ("GET", f"{BASE_URL}/admin/documents"),
        ("POST", f"{BASE_URL}/admin/documents"),
        ("GET", f"{BASE_URL}/admin/accounting"),
    ]
    
    for method, url in endpoints_to_test:
        if method == "GET":
            res = requests.get(url)
        elif method == "POST":
            res = requests.post(url, json={})
        
        assert res.status_code == 401, f"{method} {url} should return 401 without auth, got {res.status_code}"
        log(f"✓ {method} {url.split('/api')[1]} returns 401 without Bearer token")
    
    log(f"✓ All /admin/* endpoints require authentication")
    
    log("\n✅ TEST 13 PASSED: Authentication required for all admin endpoints")
    
    # ========================================================================
    # TEST 14: MULTI-USER ISOLATION - hub7 and hub7b have independent data
    # ========================================================================
    log("\n" + "=" * 80)
    log("TEST 14: MULTI-USER ISOLATION - hub7 and hub7b have independent data")
    log("=" * 80)
    
    # Create second user hub7b@divarc.fr
    log(f"\n[User B] Creating user hub7b@divarc.fr")
    token_b, user_b = create_user("hub7b@divarc.fr", "Hub Seven B")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    
    # User A (hub7) connects to impots
    log(f"\n[User A] Connecting to impots")
    res = requests.post(f"{BASE_URL}/admin/connectors/impots/connect", headers=headers)
    assert res.status_code == 200, f"POST /admin/connectors/impots/connect failed: {res.status_code} {res.text}"
    data = res.json()
    
    impots_pseudonym_a = data["connection"]["pseudonym"]
    log(f"✓ User A connected to impots with pseudonym: {impots_pseudonym_a}")
    
    # User B connects to ameli
    log(f"\n[User B] Connecting to ameli")
    res = requests.post(f"{BASE_URL}/admin/connectors/ameli/connect", headers=headers_b)
    assert res.status_code == 200, f"POST /admin/connectors/ameli/connect failed: {res.status_code} {res.text}"
    data = res.json()
    
    ameli_pseudonym_b = data["connection"]["pseudonym"]
    log(f"✓ User B connected to ameli with pseudonym: {ameli_pseudonym_b}")
    
    # Verify User A connectors do NOT show ameli as connected
    log(f"\n[User A] Verifying connectors do NOT show ameli as connected")
    res = requests.get(f"{BASE_URL}/admin/connectors", headers=headers)
    assert res.status_code == 200, f"GET /admin/connectors failed: {res.status_code} {res.text}"
    connectors_a = res.json()
    
    impots_a = next((c for c in connectors_a if c['id'] == 'impots'), None)
    ameli_a = next((c for c in connectors_a if c['id'] == 'ameli'), None)
    
    assert impots_a['connected'] == True, f"User A should see impots as connected"
    assert ameli_a['connected'] == False, f"User A should NOT see ameli as connected (belongs to User B)"
    
    log(f"✓ User A sees impots connected, ameli NOT connected")
    
    # Verify User B connectors do NOT show impots as connected
    log(f"\n[User B] Verifying connectors do NOT show impots as connected")
    res = requests.get(f"{BASE_URL}/admin/connectors", headers=headers_b)
    assert res.status_code == 200, f"GET /admin/connectors failed: {res.status_code} {res.text}"
    connectors_b = res.json()
    
    impots_b = next((c for c in connectors_b if c['id'] == 'impots'), None)
    ameli_b = next((c for c in connectors_b if c['id'] == 'ameli'), None)
    
    assert impots_b['connected'] == False, f"User B should NOT see impots as connected (belongs to User A)"
    assert ameli_b['connected'] == True, f"User B should see ameli as connected"
    
    log(f"✓ User B sees ameli connected, impots NOT connected")
    
    # User A creates a document
    log(f"\n[User A] Creating document")
    res = requests.post(f"{BASE_URL}/admin/documents", headers=headers, json={
        "title": "Document User A",
        "category": "Test",
        "issuer": "User A",
        "emoji": "📄"
    })
    assert res.status_code == 200, f"POST /admin/documents failed: {res.status_code} {res.text}"
    doc_a = res.json()
    log(f"✓ User A created document: {doc_a['title']}")
    
    # User B creates a document
    log(f"\n[User B] Creating document")
    res = requests.post(f"{BASE_URL}/admin/documents", headers=headers_b, json={
        "title": "Document User B",
        "category": "Test",
        "issuer": "User B",
        "emoji": "📄"
    })
    assert res.status_code == 200, f"POST /admin/documents failed: {res.status_code} {res.text}"
    doc_b = res.json()
    log(f"✓ User B created document: {doc_b['title']}")
    
    # Verify User A documents do NOT include User B's document
    log(f"\n[User A] Verifying documents do NOT include User B's document")
    res = requests.get(f"{BASE_URL}/admin/documents", headers=headers)
    assert res.status_code == 200, f"GET /admin/documents failed: {res.status_code} {res.text}"
    docs_a = res.json()
    
    doc_b_in_a = any(d['id'] == doc_b['id'] for d in docs_a)
    assert not doc_b_in_a, f"User A should NOT see User B's document"
    
    doc_a_in_a = any(d['id'] == doc_a['id'] for d in docs_a)
    assert doc_a_in_a, f"User A should see their own document"
    
    log(f"✓ User A sees {len(docs_a)} documents (including their own, NOT User B's)")
    
    # Verify User B documents do NOT include User A's document
    log(f"\n[User B] Verifying documents do NOT include User A's document")
    res = requests.get(f"{BASE_URL}/admin/documents", headers=headers_b)
    assert res.status_code == 200, f"GET /admin/documents failed: {res.status_code} {res.text}"
    docs_b = res.json()
    
    doc_a_in_b = any(d['id'] == doc_a['id'] for d in docs_b)
    assert not doc_a_in_b, f"User B should NOT see User A's document"
    
    doc_b_in_b = any(d['id'] == doc_b['id'] for d in docs_b)
    assert doc_b_in_b, f"User B should see their own document"
    
    log(f"✓ User B sees {len(docs_b)} documents (including their own, NOT User A's)")
    
    log("\n✅ TEST 14 PASSED: Multi-user isolation working correctly for connectors and documents")
    
    # ========================================================================
    # FINAL SUMMARY
    # ========================================================================
    log("\n" + "=" * 80)
    log("PHASE 7 HUB ADMINISTRATIF & SANTÉ - ALL TESTS PASSED ✅")
    log("=" * 80)
    log("\nSummary:")
    log("  1. ✅ GET /admin/connectors - 5 connectors (impots, ameli, caf, ants, assurance) with all fields")
    log("  2. ✅ POST /admin/connectors/impots/connect - creates connection with eidas-[0-9a-f]{6} pseudonym")
    log("  3. ✅ GET /admin/connectors - impots shows connected:true with pseudonym and non-empty data")
    log("  4. ✅ IDEMPOTENT connect - returns existing:true with SAME pseudonym (no duplicate)")
    log("  5. ✅ INVALID connector - returns 404 for non-existent connector")
    log("  6. ✅ DISCONNECT - impots shows connected:false after disconnect")
    log("  7. ✅ GET /admin/documents - auto-seeds 2 docs on first call, no duplicates on second")
    log("  8. ✅ POST /admin/documents - creates encrypted doc (encrypted:true, shared:false)")
    log("  9. ✅ SHARE - returns shareToken+expiresAt, doc shows shared:true")
    log(" 10. ✅ UNSHARE - returns shared:false, doc shows shared:false")
    log(" 11. ✅ DELETE - removes document from list")
    log(" 12. ✅ GET /admin/accounting - returns income/expense/net/categories, net=income-expense")
    log(" 13. ✅ AUTH - all /admin/* endpoints return 401 without Bearer token")
    log(" 14. ✅ MULTI-USER ISOLATION - hub7 and hub7b have independent connectors/documents")
    log("\n" + "=" * 80)
    log("NO CRITICAL ISSUES FOUND - ALL ADMIN HUB ENDPOINTS WORKING")
    log("=" * 80)

if __name__ == "__main__":
    try:
        test_phase7_admin_hub()
        sys.exit(0)
    except AssertionError as e:
        log(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        log(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
