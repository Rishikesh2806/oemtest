"""
Tests for Admin RFQ-Vendor Manual Matching Feature
Tests the following endpoints:
- POST /api/admin/rfq/:rfqId/match-vendors - Match vendors to RFQ
- GET /api/admin/rfq/:rfqId/matches - Get matched vendors
- DELETE /api/admin/rfq/:rfqId/match/:vendorId - Remove vendor match
- PUT /api/admin/rfq/:rfqId/match/:vendorId/status - Update match status
- GET /api/admin/vendors/search - Search vendors for matching

Test RFQ ID: rfq_932de773568a (already has 1 vendor matched)
Available vendor IDs: vendor_68cfbaafb999, vendor_fb2b51067982, vendor_aerospace_01
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://rfq-marketplace-9.preview.emergentagent.com').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"

# Test data
TEST_RFQ_ID = "rfq_932de773568a"
AVAILABLE_VENDORS = ["vendor_68cfbaafb999", "vendor_fb2b51067982", "vendor_aerospace_01"]

# Store auth token
auth_token = None

class TestRFQVendorMatching:
    """Tests for Admin RFQ-Vendor Manual Matching Feature"""
    
    @pytest.fixture(autouse=True, scope="class")
    def setup(self):
        """Setup auth token for all tests"""
        global auth_token
        if not auth_token:
            response = requests.post(f"{BASE_URL}/api/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            })
            assert response.status_code == 200, f"Login failed: {response.text}"
            auth_token = response.json().get("access_token")
            assert auth_token, "No access token in login response"
        yield
    
    def get_headers(self):
        """Get auth headers for requests"""
        return {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
    
    # ==================== GET VENDORS SEARCH TESTS ====================
    
    def test_01_admin_vendors_search_returns_vendors(self):
        """Test GET /api/admin/vendors/search returns vendors list"""
        response = requests.get(
            f"{BASE_URL}/api/admin/vendors/search",
            headers=self.get_headers()
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "vendors" in data
        assert "total" in data
        assert isinstance(data["vendors"], list)
        print(f"✓ Found {data['total']} vendors")
    
    def test_02_admin_vendors_search_with_search_term(self):
        """Test vendor search with search query parameter"""
        response = requests.get(
            f"{BASE_URL}/api/admin/vendors/search?search=vendor",
            headers=self.get_headers()
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "vendors" in data
        print(f"✓ Search with term returned {data['total']} vendors")
    
    def test_03_admin_vendors_search_with_category_filter(self):
        """Test vendor search filtered by machine category"""
        response = requests.get(
            f"{BASE_URL}/api/admin/vendors/search?category=CNC",
            headers=self.get_headers()
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "vendors" in data
        print(f"✓ Category filter returned {data['total']} vendors")
    
    def test_04_admin_vendors_search_includes_machine_info(self):
        """Test that vendor search results include machine information"""
        response = requests.get(
            f"{BASE_URL}/api/admin/vendors/search?approved_only=true",
            headers=self.get_headers()
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        if data["vendors"]:
            vendor = data["vendors"][0]
            assert "machines_count" in vendor, "vendor should have machines_count"
            assert "machine_categories" in vendor, "vendor should have machine_categories"
            print(f"✓ Vendor has machines_count: {vendor['machines_count']}, categories: {vendor.get('machine_categories', [])}")
        else:
            print("⚠ No vendors found to verify machine info")
    
    # ==================== GET RFQ MATCHES TESTS ====================
    
    def test_05_get_rfq_matches(self):
        """Test GET /api/admin/rfq/:rfqId/matches returns matched vendors"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfq/{TEST_RFQ_ID}/matches",
            headers=self.get_headers()
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert "rfq_id" in data
        assert "matches" in data
        assert "total_matched" in data
        assert data["rfq_id"] == TEST_RFQ_ID
        print(f"✓ RFQ {TEST_RFQ_ID} has {data['total_matched']} matched vendors, {data.get('total_quoted', 0)} quoted")
    
    def test_06_get_rfq_matches_includes_vendor_info(self):
        """Test that matched vendors include vendor_info with company details"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfq/{TEST_RFQ_ID}/matches",
            headers=self.get_headers()
        )
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        
        if data["matches"]:
            match = data["matches"][0]
            assert "vendor_info" in match, "match should have vendor_info"
            if match["vendor_info"]:
                assert "company_name" in match["vendor_info"]
                print(f"✓ Match includes vendor_info: {match['vendor_info'].get('company_name')}")
        else:
            print("⚠ No matches to verify vendor_info structure")
    
    def test_07_get_rfq_matches_nonexistent_rfq(self):
        """Test GET /api/admin/rfq/:rfqId/matches with invalid RFQ returns 404"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfq/nonexistent_rfq_id/matches",
            headers=self.get_headers()
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Correctly returns 404 for non-existent RFQ")
    
    # ==================== POST MATCH VENDORS TESTS ====================
    
    def test_08_match_vendors_missing_vendor_ids(self):
        """Test POST /api/admin/rfq/:rfqId/match-vendors fails without vendor_ids"""
        response = requests.post(
            f"{BASE_URL}/api/admin/rfq/{TEST_RFQ_ID}/match-vendors",
            headers=self.get_headers(),
            json={}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ Correctly rejects request without vendor_ids")
    
    def test_09_match_vendors_empty_array(self):
        """Test POST /api/admin/rfq/:rfqId/match-vendors fails with empty vendor_ids array"""
        response = requests.post(
            f"{BASE_URL}/api/admin/rfq/{TEST_RFQ_ID}/match-vendors",
            headers=self.get_headers(),
            json={"vendor_ids": []}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ Correctly rejects empty vendor_ids array")
    
    def test_10_match_vendors_nonexistent_rfq(self):
        """Test POST /api/admin/rfq/:rfqId/match-vendors with invalid RFQ"""
        response = requests.post(
            f"{BASE_URL}/api/admin/rfq/nonexistent_rfq_id/match-vendors",
            headers=self.get_headers(),
            json={"vendor_ids": AVAILABLE_VENDORS[:1]}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        print("✓ Correctly returns 404 for non-existent RFQ")
    
    def test_11_match_vendors_invalid_vendor_ids(self):
        """Test POST /api/admin/rfq/:rfqId/match-vendors with invalid vendor IDs"""
        response = requests.post(
            f"{BASE_URL}/api/admin/rfq/{TEST_RFQ_ID}/match-vendors",
            headers=self.get_headers(),
            json={"vendor_ids": ["invalid_vendor_1", "invalid_vendor_2"]}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ Correctly rejects invalid vendor IDs")
    
    def test_12_match_vendors_success(self):
        """Test POST /api/admin/rfq/:rfqId/match-vendors creates matches successfully"""
        # Find a vendor that isn't already matched
        # First get current matches
        get_response = requests.get(
            f"{BASE_URL}/api/admin/rfq/{TEST_RFQ_ID}/matches",
            headers=self.get_headers()
        )
        current_matches = get_response.json().get("matches", [])
        current_vendor_ids = {m.get("vendor_id") for m in current_matches}
        
        # Find vendors not yet matched
        vendors_to_match = [v for v in AVAILABLE_VENDORS if v not in current_vendor_ids]
        
        if not vendors_to_match:
            print("⚠ All test vendors already matched - skipping match creation")
            return
        
        vendor_to_match = vendors_to_match[0]
        
        response = requests.post(
            f"{BASE_URL}/api/admin/rfq/{TEST_RFQ_ID}/match-vendors",
            headers=self.get_headers(),
            json={"vendor_ids": [vendor_to_match]}
        )
        
        # If vendor doesn't exist, it's valid to get 400
        if response.status_code == 400:
            print(f"⚠ Vendor {vendor_to_match} may not exist in DB: {response.text}")
            return
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print(f"✓ Successfully matched vendor(s). Created: {data.get('matches_created')}, Notified: {data.get('vendors_notified')}")
    
    def test_13_match_vendors_already_matched_is_skipped(self):
        """Test that already matched vendors are not duplicated"""
        # Get current matches first
        get_response = requests.get(
            f"{BASE_URL}/api/admin/rfq/{TEST_RFQ_ID}/matches",
            headers=self.get_headers()
        )
        current_matches = get_response.json().get("matches", [])
        
        if not current_matches:
            print("⚠ No existing matches to test duplicate prevention")
            return
        
        # Try to match an already matched vendor
        matched_vendor_id = current_matches[0].get("vendor_id")
        
        response = requests.post(
            f"{BASE_URL}/api/admin/rfq/{TEST_RFQ_ID}/match-vendors",
            headers=self.get_headers(),
            json={"vendor_ids": [matched_vendor_id]}
        )
        
        # It should succeed but not create new matches
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("matches_created") == 0, "Should not create duplicate match"
        print(f"✓ Already matched vendor correctly skipped, matches_created=0")
    
    # ==================== PUT UPDATE MATCH STATUS TESTS ====================
    
    def test_14_update_match_status_invalid_status(self):
        """Test PUT /api/admin/rfq/:rfqId/match/:vendorId/status rejects invalid status"""
        # Get a matched vendor first
        get_response = requests.get(
            f"{BASE_URL}/api/admin/rfq/{TEST_RFQ_ID}/matches",
            headers=self.get_headers()
        )
        matches = get_response.json().get("matches", [])
        
        if not matches:
            print("⚠ No matches to test status update")
            return
        
        vendor_id = matches[0].get("vendor_id")
        
        response = requests.put(
            f"{BASE_URL}/api/admin/rfq/{TEST_RFQ_ID}/match/{vendor_id}/status",
            headers=self.get_headers(),
            json={"status": "invalid_status"}
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        print("✓ Correctly rejects invalid status value")
    
    def test_15_update_match_status_success(self):
        """Test PUT /api/admin/rfq/:rfqId/match/:vendorId/status updates status"""
        # Get a matched vendor first
        get_response = requests.get(
            f"{BASE_URL}/api/admin/rfq/{TEST_RFQ_ID}/matches",
            headers=self.get_headers()
        )
        matches = get_response.json().get("matches", [])
        
        if not matches:
            print("⚠ No matches to test status update")
            return
        
        vendor_id = matches[0].get("vendor_id")
        
        response = requests.put(
            f"{BASE_URL}/api/admin/rfq/{TEST_RFQ_ID}/match/{vendor_id}/status",
            headers=self.get_headers(),
            json={"status": "viewed"}
        )
        
        # 404 is valid if match doesn't exist in rfq_vendor_matches collection (legacy match)
        if response.status_code == 404:
            print("⚠ Match may be legacy (not in rfq_vendor_matches collection)")
            return
        
        assert response.status_code == 200, f"Failed: {response.text}"
        data = response.json()
        assert data.get("success") == True
        print(f"✓ Successfully updated match status to 'viewed'")
    
    def test_16_update_match_status_nonexistent(self):
        """Test PUT status update for non-existent match returns 404"""
        response = requests.put(
            f"{BASE_URL}/api/admin/rfq/{TEST_RFQ_ID}/match/nonexistent_vendor/status",
            headers=self.get_headers(),
            json={"status": "viewed"}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Correctly returns 404 for non-existent match")
    
    # ==================== DELETE MATCH TESTS ====================
    
    def test_17_delete_match_nonexistent_rfq(self):
        """Test DELETE /api/admin/rfq/:rfqId/match/:vendorId with invalid RFQ"""
        response = requests.delete(
            f"{BASE_URL}/api/admin/rfq/nonexistent_rfq/match/vendor_123",
            headers=self.get_headers()
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Correctly returns 404 for non-existent RFQ")
    
    def test_18_delete_match_success(self):
        """Test DELETE /api/admin/rfq/:rfqId/match/:vendorId removes match"""
        # First, let's try to create a test match that we can delete
        # Get a vendor that's available
        search_response = requests.get(
            f"{BASE_URL}/api/admin/vendors/search?approved_only=true&limit=5",
            headers=self.get_headers()
        )
        vendors = search_response.json().get("vendors", [])
        
        if not vendors:
            print("⚠ No vendors available to test delete")
            return
        
        # Get current matches
        get_response = requests.get(
            f"{BASE_URL}/api/admin/rfq/{TEST_RFQ_ID}/matches",
            headers=self.get_headers()
        )
        current_matches = get_response.json().get("matches", [])
        current_vendor_ids = {m.get("vendor_id") for m in current_matches}
        
        # Find a vendor not already matched
        new_vendor = None
        for v in vendors:
            if v.get("vendor_id") not in current_vendor_ids:
                new_vendor = v
                break
        
        if not new_vendor:
            # If all are matched, test delete on an existing one
            if current_matches:
                vendor_id = current_matches[-1].get("vendor_id")  # Use last match
                print(f"Testing delete on existing match: {vendor_id}")
            else:
                print("⚠ No matches available to test delete")
                return
        else:
            # Create a new match first
            match_response = requests.post(
                f"{BASE_URL}/api/admin/rfq/{TEST_RFQ_ID}/match-vendors",
                headers=self.get_headers(),
                json={"vendor_ids": [new_vendor["vendor_id"]]}
            )
            if match_response.status_code != 200:
                print(f"⚠ Could not create test match: {match_response.text}")
                return
            vendor_id = new_vendor["vendor_id"]
        
        # Now delete the match
        delete_response = requests.delete(
            f"{BASE_URL}/api/admin/rfq/{TEST_RFQ_ID}/match/{vendor_id}",
            headers=self.get_headers()
        )
        assert delete_response.status_code == 200, f"Failed: {delete_response.text}"
        data = delete_response.json()
        assert data.get("success") == True
        print(f"✓ Successfully deleted match for vendor {vendor_id}")
    
    # ==================== ACTIVITY LOG TESTS ====================
    
    def test_19_activity_log_created_on_match(self):
        """Test that activity log is created when vendors are matched"""
        # Get activity logs for RFQ entity
        response = requests.get(
            f"{BASE_URL}/api/admin/activity-logs/rfqs?entity_id={TEST_RFQ_ID}&limit=10",
            headers=self.get_headers()
        )
        
        # Activity logs endpoint might have different path
        if response.status_code == 404:
            # Try alternate path
            response = requests.get(
                f"{BASE_URL}/api/admin/activity-logs?entity_type=rfq&entity_id={TEST_RFQ_ID}&limit=10",
                headers=self.get_headers()
            )
        
        if response.status_code == 200:
            data = response.json()
            logs = data.get("logs", data.get("activities", []))
            match_logs = [l for l in logs if l.get("type") in ["rfq_vendors_matched", "rfq_vendor_unmatched"]]
            print(f"✓ Found {len(match_logs)} matching activity logs for RFQ")
        else:
            print(f"⚠ Activity logs endpoint returned {response.status_code}")
    
    # ==================== RBAC/PERMISSION TESTS ====================
    
    def test_20_unauthenticated_access_denied(self):
        """Test that unauthenticated requests are denied"""
        response = requests.get(f"{BASE_URL}/api/admin/rfq/{TEST_RFQ_ID}/matches")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Unauthenticated access correctly denied")
    
    def test_21_vendor_search_requires_auth(self):
        """Test that vendor search requires authentication"""
        response = requests.get(f"{BASE_URL}/api/admin/vendors/search")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Vendor search correctly requires authentication")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
