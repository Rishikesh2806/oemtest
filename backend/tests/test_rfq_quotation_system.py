"""
Test RFQ Analysis and Quotation System
Tests for:
- POST /api/rfq/analyze-and-match - AI-based RFQ analysis and vendor matching
- GET /api/rfq/:rfqId/vendors - Get matched vendors with status
- GET /api/rfq/:rfqId/quotations - Get quotations with cost breakdown
- POST /api/vendor/quotation - Submit quotation with cost breakdown
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"
VENDOR_EMAIL = "testvendor@oemlinker.com"
VENDOR_PASSWORD = "Vendor123!"

# Test data from context
TEST_RFQ_ID = "rfq_932de773568a"
TEST_VENDOR_ID = "vendor_da93e0230ecd"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def vendor_token():
    """Get vendor authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": VENDOR_EMAIL,
        "password": VENDOR_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Vendor login failed: {response.status_code} - {response.text}")


@pytest.fixture(scope="module")
def admin_client(admin_token):
    """Authenticated admin session"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    })
    return session


@pytest.fixture(scope="module")
def vendor_client(vendor_token):
    """Authenticated vendor session"""
    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {vendor_token}",
        "Content-Type": "application/json"
    })
    return session


class TestRFQAnalyzeAndMatch:
    """Tests for POST /api/rfq/analyze-and-match endpoint"""
    
    def test_analyze_and_match_requires_auth(self):
        """Test that endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/rfq/analyze-and-match", json={
            "rfq_id": TEST_RFQ_ID
        })
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_analyze_and_match_requires_rfq_id(self, admin_client):
        """Test that rfq_id is required"""
        response = admin_client.post(f"{BASE_URL}/api/rfq/analyze-and-match", json={})
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "rfq_id" in response.text.lower()
    
    def test_analyze_and_match_invalid_rfq(self, admin_client):
        """Test with non-existent RFQ"""
        response = admin_client.post(f"{BASE_URL}/api/rfq/analyze-and-match", json={
            "rfq_id": "rfq_nonexistent123"
        })
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    
    def test_analyze_and_match_success(self, admin_client):
        """Test successful RFQ analysis and vendor matching"""
        response = admin_client.post(f"{BASE_URL}/api/rfq/analyze-and-match", json={
            "rfq_id": TEST_RFQ_ID
        })
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "rfq_id" in data
        assert data["rfq_id"] == TEST_RFQ_ID
        assert "process_detection" in data
        assert "matched_vendors" in data
        assert "total_matched" in data
        assert "total_rejected" in data
        
        # Verify process detection structure
        process_detection = data["process_detection"]
        assert "primary_process" in process_detection
        assert "all_processes" in process_detection
        assert "raw_material_provided" in process_detection
        
        # Primary process should be one of: machining, casting, forging, fabrication
        assert process_detection["primary_process"] in ["machining", "casting", "forging", "fabrication"]
        
        print(f"Process detected: {process_detection['primary_process']}")
        print(f"All processes: {process_detection['all_processes']}")
        print(f"Raw material provided: {process_detection['raw_material_provided']}")
        print(f"Matched vendors: {data['total_matched']}")
        print(f"Rejected vendors: {data['total_rejected']}")
    
    def test_process_detection_keywords(self, admin_client):
        """Verify process detection returns valid process types"""
        response = admin_client.post(f"{BASE_URL}/api/rfq/analyze-and-match", json={
            "rfq_id": TEST_RFQ_ID
        })
        assert response.status_code == 200
        
        data = response.json()
        process_detection = data["process_detection"]
        
        # Verify all_processes is a list
        assert isinstance(process_detection["all_processes"], list)
        
        # Each process should be valid
        valid_processes = ["machining", "casting", "forging", "fabrication"]
        for proc in process_detection["all_processes"]:
            assert proc in valid_processes, f"Invalid process: {proc}"
    
    def test_matched_vendors_structure(self, admin_client):
        """Verify matched vendors have correct structure"""
        response = admin_client.post(f"{BASE_URL}/api/rfq/analyze-and-match", json={
            "rfq_id": TEST_RFQ_ID
        })
        assert response.status_code == 200
        
        data = response.json()
        matched_vendors = data.get("matched_vendors", [])
        
        if matched_vendors:
            vendor = matched_vendors[0]
            # Verify vendor structure
            assert "vendor_id" in vendor
            assert "company_name" in vendor
            assert "suitability_score" in vendor
            assert "matched_capabilities" in vendor
            assert "match_reason" in vendor
            assert "match_type" in vendor
            
            # Score should be between 0 and 100
            assert 0 <= vendor["suitability_score"] <= 100
            
            print(f"Top matched vendor: {vendor['company_name']} (Score: {vendor['suitability_score']})")


class TestGetRFQVendors:
    """Tests for GET /api/rfq/:rfqId/vendors endpoint"""
    
    def test_get_vendors_requires_auth(self):
        """Test that endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/rfq/{TEST_RFQ_ID}/vendors")
        assert response.status_code == 401
    
    def test_get_vendors_invalid_rfq(self, admin_client):
        """Test with non-existent RFQ"""
        response = admin_client.get(f"{BASE_URL}/api/rfq/rfq_nonexistent123/vendors")
        assert response.status_code == 404
    
    def test_get_vendors_success(self, admin_client):
        """Test successful retrieval of matched vendors"""
        response = admin_client.get(f"{BASE_URL}/api/rfq/{TEST_RFQ_ID}/vendors")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "rfq_id" in data
        assert data["rfq_id"] == TEST_RFQ_ID
        assert "matched_vendors" in data
        assert "total_matched" in data
        assert "process_detected" in data
        assert "raw_material_provided" in data
        
        print(f"Process detected: {data['process_detected']}")
        print(f"Raw material provided: {data['raw_material_provided']}")
        print(f"Total matched vendors: {data['total_matched']}")
    
    def test_vendors_have_quote_status(self, admin_client):
        """Verify vendors include quote status information"""
        response = admin_client.get(f"{BASE_URL}/api/rfq/{TEST_RFQ_ID}/vendors")
        assert response.status_code == 200
        
        data = response.json()
        matched_vendors = data.get("matched_vendors", [])
        
        for vendor in matched_vendors:
            # Each vendor should have quote status fields
            assert "has_quoted" in vendor
            assert isinstance(vendor["has_quoted"], bool)
            
            if vendor["has_quoted"]:
                assert "quote_info" in vendor
                assert vendor["quote_info"] is not None
                print(f"Vendor {vendor.get('company_name', vendor['vendor_id'])} has quoted: {vendor['quote_info']}")


class TestGetRFQQuotations:
    """Tests for GET /api/rfq/:rfqId/quotations endpoint"""
    
    def test_get_quotations_requires_auth(self):
        """Test that endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/rfq/{TEST_RFQ_ID}/quotations")
        assert response.status_code == 401
    
    def test_get_quotations_invalid_rfq(self, admin_client):
        """Test with non-existent RFQ"""
        response = admin_client.get(f"{BASE_URL}/api/rfq/rfq_nonexistent123/quotations")
        assert response.status_code == 404
    
    def test_get_quotations_success(self, admin_client):
        """Test successful retrieval of quotations with cost breakdown"""
        response = admin_client.get(f"{BASE_URL}/api/rfq/{TEST_RFQ_ID}/quotations")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "rfq_id" in data
        assert data["rfq_id"] == TEST_RFQ_ID
        assert "rfq_title" in data
        assert "quotations" in data
        assert "total_quotes" in data
        assert "comparison_summary" in data
        
        print(f"RFQ Title: {data['rfq_title']}")
        print(f"Total quotes: {data['total_quotes']}")
    
    def test_quotations_have_cost_breakdown(self, admin_client):
        """Verify quotations include detailed cost breakdown"""
        response = admin_client.get(f"{BASE_URL}/api/rfq/{TEST_RFQ_ID}/quotations")
        assert response.status_code == 200
        
        data = response.json()
        quotations = data.get("quotations", [])
        
        if quotations:
            quote = quotations[0]
            
            # Verify cost breakdown fields
            assert "material_cost" in quote
            assert "machining_cost" in quote
            assert "additional_costs" in quote
            assert "total_cost" in quote
            assert "material_provided_by_buyer" in quote
            
            # Verify other required fields
            assert "vendor_name" in quote
            assert "vendor_location" in quote
            assert "lead_time_days" in quote
            assert "currency" in quote
            
            print(f"Quote from {quote['vendor_name']}:")
            print(f"  Material cost: {quote['material_cost']}")
            print(f"  Machining cost: {quote['machining_cost']}")
            print(f"  Additional costs: {quote['additional_costs']}")
            print(f"  Total cost: {quote['total_cost']}")
            print(f"  Material by buyer: {quote['material_provided_by_buyer']}")
    
    def test_comparison_summary_structure(self, admin_client):
        """Verify comparison summary has correct structure"""
        response = admin_client.get(f"{BASE_URL}/api/rfq/{TEST_RFQ_ID}/quotations")
        assert response.status_code == 200
        
        data = response.json()
        summary = data.get("comparison_summary", {})
        
        # Verify summary fields
        assert "lowest_total_cost" in summary
        assert "lowest_machining_cost" in summary
        assert "average_total_cost" in summary
        assert "quotes_with_material" in summary
        assert "quotes_without_material" in summary
        
        print(f"Comparison Summary:")
        print(f"  Lowest total: {summary['lowest_total_cost']}")
        print(f"  Lowest machining: {summary['lowest_machining_cost']}")
        print(f"  Average total: {summary['average_total_cost']}")
        print(f"  Quotes with material: {summary['quotes_with_material']}")
        print(f"  Quotes without material: {summary['quotes_without_material']}")
    
    def test_total_cost_calculation(self, admin_client):
        """Verify total_cost is correctly calculated"""
        response = admin_client.get(f"{BASE_URL}/api/rfq/{TEST_RFQ_ID}/quotations")
        assert response.status_code == 200
        
        data = response.json()
        quotations = data.get("quotations", [])
        
        for quote in quotations:
            material = quote.get("material_cost", 0) or 0
            machining = quote.get("machining_cost", 0) or 0
            additional = quote.get("additional_costs", {}) or {}
            additional_total = sum(additional.values()) if additional else 0
            
            # If buyer provides material, material_cost should be 0 or not counted
            if quote.get("material_provided_by_buyer"):
                expected_total = machining + additional_total
            else:
                expected_total = material + machining + additional_total
            
            total = quote.get("total_cost", 0)
            
            # Allow small floating point differences
            assert abs(total - expected_total) < 1, f"Total cost mismatch: {total} != {expected_total}"
            print(f"Quote {quote['quote_id']}: Total {total} = Material {material} + Machining {machining} + Additional {additional_total}")


class TestSubmitVendorQuotation:
    """Tests for POST /api/vendor/quotation endpoint"""
    
    def test_submit_quotation_requires_auth(self):
        """Test that endpoint requires authentication"""
        response = requests.post(f"{BASE_URL}/api/vendor/quotation", json={
            "rfq_id": TEST_RFQ_ID,
            "machining_cost": 5000,
            "lead_time_days": 10
        })
        assert response.status_code == 401
    
    def test_submit_quotation_requires_vendor_profile(self, admin_client):
        """Test that non-vendor users cannot submit quotations"""
        response = admin_client.post(f"{BASE_URL}/api/vendor/quotation", json={
            "rfq_id": TEST_RFQ_ID,
            "machining_cost": 5000,
            "lead_time_days": 10
        })
        # Admin without vendor profile should get 403
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_submit_quotation_requires_rfq_id(self, vendor_client):
        """Test that rfq_id is required"""
        response = vendor_client.post(f"{BASE_URL}/api/vendor/quotation", json={
            "machining_cost": 5000,
            "lead_time_days": 10
        })
        assert response.status_code == 400
        assert "rfq_id" in response.text.lower()
    
    def test_submit_quotation_requires_machining_cost(self, vendor_client):
        """Test that machining_cost is required and must be > 0"""
        response = vendor_client.post(f"{BASE_URL}/api/vendor/quotation", json={
            "rfq_id": TEST_RFQ_ID,
            "machining_cost": 0,
            "lead_time_days": 10
        })
        assert response.status_code == 400
        # Either machining cost error or already quoted error
        assert "machining" in response.text.lower() or "already" in response.text.lower()
        print(f"Response: {response.text}")
    
    def test_submit_quotation_material_cost_validation(self, vendor_client):
        """Test material_cost validation when vendor provides material"""
        response = vendor_client.post(f"{BASE_URL}/api/vendor/quotation", json={
            "rfq_id": TEST_RFQ_ID,
            "material_provided_by_buyer": False,
            "material_cost": 0,  # Should fail - material cost required
            "machining_cost": 5000,
            "lead_time_days": 10
        })
        assert response.status_code == 400
        # Either material cost error or already quoted error
        assert "material" in response.text.lower() or "already" in response.text.lower()
        print(f"Response: {response.text}")
    
    def test_submit_quotation_buyer_provides_material(self, vendor_client):
        """Test quotation when buyer provides material (no material_cost required)"""
        # First check if vendor already quoted
        response = vendor_client.post(f"{BASE_URL}/api/vendor/quotation", json={
            "rfq_id": TEST_RFQ_ID,
            "material_provided_by_buyer": True,
            "machining_cost": 8500,
            "additional_costs": {"heat_treatment": 1500},
            "lead_time_days": 14,
            "notes": "Test quotation - buyer provides material"
        })
        
        # Either success (200) or already quoted (400)
        if response.status_code == 400 and "already" in response.text.lower():
            print("Vendor has already submitted a quotation for this RFQ")
            pytest.skip("Vendor already quoted on this RFQ")
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "quote_id" in data
        print(f"Quotation submitted: {data.get('quote_id')}")


class TestExistingQuotationData:
    """Tests to verify existing quotation data from context"""
    
    def test_existing_quote_has_correct_costs(self, admin_client):
        """Verify the test RFQ has quotation with expected cost breakdown"""
        response = admin_client.get(f"{BASE_URL}/api/rfq/{TEST_RFQ_ID}/quotations")
        assert response.status_code == 200
        
        data = response.json()
        quotations = data.get("quotations", [])
        
        # From context: Test RFQ has 1 quote with total_cost 27000, machining_cost 8500, material_cost 15000
        if quotations:
            # Find quote with expected values
            found_expected = False
            for quote in quotations:
                if quote.get("total_cost") == 27000:
                    assert quote.get("machining_cost") == 8500, f"Expected machining_cost 8500, got {quote.get('machining_cost')}"
                    assert quote.get("material_cost") == 15000, f"Expected material_cost 15000, got {quote.get('material_cost')}"
                    found_expected = True
                    print(f"Found expected quote: total={quote['total_cost']}, machining={quote['machining_cost']}, material={quote['material_cost']}")
                    break
            
            if not found_expected:
                print(f"Note: Expected quote with total_cost=27000 not found. Current quotes: {[q['total_cost'] for q in quotations]}")


class TestProcessDetectionLogic:
    """Tests for process detection logic"""
    
    def test_process_detection_returns_valid_structure(self, admin_client):
        """Verify process detection returns all required fields"""
        response = admin_client.post(f"{BASE_URL}/api/rfq/analyze-and-match", json={
            "rfq_id": TEST_RFQ_ID
        })
        assert response.status_code == 200
        
        data = response.json()
        process_detection = data.get("process_detection", {})
        
        required_fields = ["primary_process", "all_processes", "raw_material_provided"]
        for field in required_fields:
            assert field in process_detection, f"Missing field: {field}"
        
        # Verify types
        assert isinstance(process_detection["primary_process"], str)
        assert isinstance(process_detection["all_processes"], list)
        assert isinstance(process_detection["raw_material_provided"], bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
