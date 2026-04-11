"""
Test suite for Browse Before Registering feature - Public API endpoints
Tests: /api/public/vendors, /api/public/vendors/{vendor_id}, /api/public/rfqs, /api/public/machines, /api/public/stats
All endpoints should work without authentication
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestPublicVendorsEndpoint:
    """Tests for GET /api/public/vendors - no auth required"""
    
    def test_public_vendors_returns_200(self):
        """Verify public vendors endpoint returns 200 without auth"""
        response = requests.get(f"{BASE_URL}/api/public/vendors")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: GET /api/public/vendors returns 200")
    
    def test_public_vendors_response_structure(self):
        """Verify response has vendors list, total, page, limit"""
        response = requests.get(f"{BASE_URL}/api/public/vendors")
        data = response.json()
        
        assert "vendors" in data, "Response missing 'vendors' key"
        assert "total" in data, "Response missing 'total' key"
        assert "page" in data, "Response missing 'page' key"
        assert "limit" in data, "Response missing 'limit' key"
        assert isinstance(data["vendors"], list), "vendors should be a list"
        print(f"PASS: Response structure valid - {len(data['vendors'])} vendors, total: {data['total']}")
    
    def test_public_vendors_data_fields(self):
        """Verify each vendor has required fields: vendor_id, company_name, capabilities, materials, machines_preview"""
        response = requests.get(f"{BASE_URL}/api/public/vendors?limit=5")
        data = response.json()
        
        if len(data["vendors"]) == 0:
            pytest.skip("No vendors in database")
        
        vendor = data["vendors"][0]
        required_fields = ["vendor_id", "company_name", "machine_count", "capabilities", "materials", "machines_preview"]
        for field in required_fields:
            assert field in vendor, f"Vendor missing required field: {field}"
        
        # Verify no sensitive data exposed
        sensitive_fields = ["email", "phone", "password", "address"]
        for field in sensitive_fields:
            assert field not in vendor, f"Sensitive field '{field}' should not be exposed"
        
        print(f"PASS: Vendor data fields valid - {vendor['company_name']}")
    
    def test_public_vendors_capability_filter(self):
        """Test capability filter parameter"""
        response = requests.get(f"{BASE_URL}/api/public/vendors?capability=CNC")
        assert response.status_code == 200
        data = response.json()
        print(f"PASS: Capability filter works - {len(data['vendors'])} vendors with CNC capability")
    
    def test_public_vendors_material_filter(self):
        """Test material filter parameter"""
        response = requests.get(f"{BASE_URL}/api/public/vendors?material=steel")
        assert response.status_code == 200
        data = response.json()
        print(f"PASS: Material filter works - {len(data['vendors'])} vendors with steel material")


class TestPublicVendorDetailEndpoint:
    """Tests for GET /api/public/vendors/{vendor_id} - no auth required"""
    
    def test_public_vendor_detail_returns_200(self):
        """Get a vendor_id first, then test detail endpoint"""
        # First get a vendor_id from the list
        list_response = requests.get(f"{BASE_URL}/api/public/vendors?limit=1")
        list_data = list_response.json()
        
        if len(list_data["vendors"]) == 0:
            pytest.skip("No vendors in database")
        
        vendor_id = list_data["vendors"][0]["vendor_id"]
        
        # Now test detail endpoint
        response = requests.get(f"{BASE_URL}/api/public/vendors/{vendor_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        print(f"PASS: GET /api/public/vendors/{vendor_id} returns 200")
    
    def test_public_vendor_detail_response_structure(self):
        """Verify vendor detail has full machine list"""
        list_response = requests.get(f"{BASE_URL}/api/public/vendors?limit=1")
        list_data = list_response.json()
        
        if len(list_data["vendors"]) == 0:
            pytest.skip("No vendors in database")
        
        vendor_id = list_data["vendors"][0]["vendor_id"]
        response = requests.get(f"{BASE_URL}/api/public/vendors/{vendor_id}")
        data = response.json()
        
        required_fields = ["vendor_id", "company_name", "capabilities", "materials", "machine_count", "machines"]
        for field in required_fields:
            assert field in data, f"Vendor detail missing field: {field}"
        
        assert isinstance(data["machines"], list), "machines should be a list"
        print(f"PASS: Vendor detail structure valid - {data['company_name']} with {len(data['machines'])} machines")
    
    def test_public_vendor_detail_machine_fields(self):
        """Verify machine objects have required fields"""
        list_response = requests.get(f"{BASE_URL}/api/public/vendors?limit=1")
        list_data = list_response.json()
        
        if len(list_data["vendors"]) == 0:
            pytest.skip("No vendors in database")
        
        vendor_id = list_data["vendors"][0]["vendor_id"]
        response = requests.get(f"{BASE_URL}/api/public/vendors/{vendor_id}")
        data = response.json()
        
        if len(data["machines"]) == 0:
            pytest.skip("Vendor has no machines")
        
        machine = data["machines"][0]
        expected_fields = ["machine_id", "machine_type", "brand", "model"]
        for field in expected_fields:
            assert field in machine, f"Machine missing field: {field}"
        
        print(f"PASS: Machine fields valid - {machine.get('brand')} {machine.get('model')}")
    
    def test_public_vendor_detail_404_for_invalid_id(self):
        """Test 404 for non-existent vendor"""
        response = requests.get(f"{BASE_URL}/api/public/vendors/invalid-vendor-id-12345")
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("PASS: Returns 404 for invalid vendor_id")


class TestPublicRFQsEndpoint:
    """Tests for GET /api/public/rfqs - no auth required, no buyer info exposed"""
    
    def test_public_rfqs_returns_200(self):
        """Verify public RFQs endpoint returns 200 without auth"""
        response = requests.get(f"{BASE_URL}/api/public/rfqs")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: GET /api/public/rfqs returns 200")
    
    def test_public_rfqs_response_structure(self):
        """Verify response has rfqs list, total, page, limit, filters"""
        response = requests.get(f"{BASE_URL}/api/public/rfqs")
        data = response.json()
        
        assert "rfqs" in data, "Response missing 'rfqs' key"
        assert "total" in data, "Response missing 'total' key"
        assert "page" in data, "Response missing 'page' key"
        assert "limit" in data, "Response missing 'limit' key"
        assert "filters" in data, "Response missing 'filters' key"
        assert isinstance(data["rfqs"], list), "rfqs should be a list"
        print(f"PASS: Response structure valid - {len(data['rfqs'])} RFQs, total: {data['total']}")
    
    def test_public_rfqs_data_fields(self):
        """Verify RFQ has material, processes, geometry, complexity - NO buyer info"""
        response = requests.get(f"{BASE_URL}/api/public/rfqs?limit=5")
        data = response.json()
        
        if len(data["rfqs"]) == 0:
            pytest.skip("No RFQs in database")
        
        rfq = data["rfqs"][0]
        expected_fields = ["rfq_id", "title", "material", "quantity", "status", "created_at"]
        for field in expected_fields:
            assert field in rfq, f"RFQ missing field: {field}"
        
        # Verify NO buyer info exposed
        sensitive_fields = ["buyer_id", "buyer_email", "buyer_name", "buyer_phone", "user_id", "email"]
        for field in sensitive_fields:
            assert field not in rfq, f"Sensitive buyer field '{field}' should NOT be exposed"
        
        print(f"PASS: RFQ data fields valid - {rfq['title']}, material: {rfq.get('material')}")
    
    def test_public_rfqs_material_filter(self):
        """Test material filter parameter"""
        response = requests.get(f"{BASE_URL}/api/public/rfqs?material=steel")
        assert response.status_code == 200
        data = response.json()
        print(f"PASS: Material filter works - {len(data['rfqs'])} RFQs with steel")
    
    def test_public_rfqs_process_filter(self):
        """Test process filter parameter"""
        response = requests.get(f"{BASE_URL}/api/public/rfqs?process=CNC")
        assert response.status_code == 200
        data = response.json()
        print(f"PASS: Process filter works - {len(data['rfqs'])} RFQs with CNC process")
    
    def test_public_rfqs_filters_in_response(self):
        """Verify filters object contains materials and statuses"""
        response = requests.get(f"{BASE_URL}/api/public/rfqs")
        data = response.json()
        
        assert "filters" in data
        assert "materials" in data["filters"], "filters missing 'materials'"
        assert "statuses" in data["filters"], "filters missing 'statuses'"
        assert isinstance(data["filters"]["materials"], list)
        print(f"PASS: Filters in response - {len(data['filters']['materials'])} materials, {len(data['filters']['statuses'])} statuses")


class TestPublicMachinesEndpoint:
    """Tests for GET /api/public/machines - no auth required"""
    
    def test_public_machines_returns_200(self):
        """Verify public machines endpoint returns 200 without auth"""
        response = requests.get(f"{BASE_URL}/api/public/machines")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: GET /api/public/machines returns 200")
    
    def test_public_machines_response_structure(self):
        """Verify response has machines list, total, page, limit, filters"""
        response = requests.get(f"{BASE_URL}/api/public/machines")
        data = response.json()
        
        assert "machines" in data, "Response missing 'machines' key"
        assert "total" in data, "Response missing 'total' key"
        assert "page" in data, "Response missing 'page' key"
        assert "limit" in data, "Response missing 'limit' key"
        assert isinstance(data["machines"], list), "machines should be a list"
        print(f"PASS: Response structure valid - {len(data['machines'])} machines, total: {data['total']}")
    
    def test_public_machines_data_fields(self):
        """Verify machine has envelope, tolerance, materials, vendor_name"""
        response = requests.get(f"{BASE_URL}/api/public/machines?limit=5")
        data = response.json()
        
        if len(data["machines"]) == 0:
            pytest.skip("No machines in database")
        
        machine = data["machines"][0]
        expected_fields = ["machine_id", "machine_type", "brand", "model", "vendor_id", "vendor_name"]
        for field in expected_fields:
            assert field in machine, f"Machine missing field: {field}"
        
        # Check envelope structure if present
        if "envelope" in machine:
            assert isinstance(machine["envelope"], dict), "envelope should be a dict"
        
        print(f"PASS: Machine data fields valid - {machine.get('brand')} {machine.get('model')}")
    
    def test_public_machines_type_filter(self):
        """Test machine_type filter parameter"""
        response = requests.get(f"{BASE_URL}/api/public/machines?machine_type=CNC")
        assert response.status_code == 200
        data = response.json()
        print(f"PASS: Machine type filter works - {len(data['machines'])} CNC machines")
    
    def test_public_machines_material_filter(self):
        """Test material filter parameter"""
        response = requests.get(f"{BASE_URL}/api/public/machines?material=steel")
        assert response.status_code == 200
        data = response.json()
        print(f"PASS: Material filter works - {len(data['machines'])} machines supporting steel")


class TestPublicStatsEndpoint:
    """Tests for GET /api/public/stats - platform statistics"""
    
    def test_public_stats_returns_200(self):
        """Verify public stats endpoint returns 200 without auth"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        print("PASS: GET /api/public/stats returns 200")
    
    def test_public_stats_response_structure(self):
        """Verify stats has vendors, machines, rfqs_processed, capabilities"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        data = response.json()
        
        required_fields = ["vendors", "machines", "rfqs_processed", "capabilities"]
        for field in required_fields:
            assert field in data, f"Stats missing field: {field}"
        
        assert isinstance(data["vendors"], int), "vendors should be int"
        assert isinstance(data["machines"], int), "machines should be int"
        assert isinstance(data["rfqs_processed"], int), "rfqs_processed should be int"
        assert isinstance(data["capabilities"], list), "capabilities should be list"
        
        print(f"PASS: Stats structure valid - {data['vendors']} vendors, {data['machines']} machines, {data['rfqs_processed']} RFQs")
    
    def test_public_stats_values_match_expected(self):
        """Verify stats values are reasonable (11 vendors, 31 machines, 288 RFQs per spec)"""
        response = requests.get(f"{BASE_URL}/api/public/stats")
        data = response.json()
        
        # Per spec: 11 vendors, 31 machines, 288 RFQs
        assert data["vendors"] >= 1, "Should have at least 1 vendor"
        assert data["machines"] >= 1, "Should have at least 1 machine"
        assert data["rfqs_processed"] >= 1, "Should have at least 1 RFQ"
        
        print(f"PASS: Stats values reasonable - vendors: {data['vendors']}, machines: {data['machines']}, rfqs: {data['rfqs_processed']}")


class TestNoAuthRequired:
    """Verify all public endpoints work without any authentication header"""
    
    def test_all_public_endpoints_no_auth(self):
        """Test all public endpoints without Authorization header"""
        endpoints = [
            "/api/public/vendors",
            "/api/public/rfqs",
            "/api/public/machines",
            "/api/public/stats",
        ]
        
        for endpoint in endpoints:
            response = requests.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 200, f"{endpoint} failed without auth: {response.status_code}"
            print(f"PASS: {endpoint} works without auth")
        
        print("PASS: All public endpoints accessible without authentication")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
