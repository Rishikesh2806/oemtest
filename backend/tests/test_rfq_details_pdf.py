"""
Test cases for Admin RFQ Details View and PDF Download feature.
Testing:
- GET /api/admin/rfqs/{rfq_id} - Enhanced RFQ details endpoint
- GET /api/admin/rfqs/{rfq_id}/pdf - PDF generation endpoint
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL')

class TestAdminRFQDetailsAndPDF:
    """Test Admin RFQ Details and PDF Download endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin and get auth token"""
        self.admin_email = "admin@offoadex.com"
        self.admin_password = "admin123"
        self.test_rfq_id = "rfq_932de773568a"
        
        # Login
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": self.admin_email,
            "password": self.admin_password
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    # ============ GET /api/admin/rfqs/{rfq_id} Tests ============
    
    def test_01_get_rfq_details_success(self):
        """Test getting enhanced RFQ details with buyer_info, drawings, quotes, matched_vendors_details"""
        response = requests.get(f"{BASE_URL}/api/admin/rfqs/{self.test_rfq_id}", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        
        # Verify basic RFQ fields
        assert "rfq_id" in data, "Missing rfq_id"
        assert data["rfq_id"] == self.test_rfq_id, "RFQ ID mismatch"
        assert "title" in data, "Missing title"
        assert "status" in data, "Missing status"
        assert "created_at" in data, "Missing created_at"
        
    def test_02_get_rfq_details_includes_buyer_info(self):
        """Test that RFQ details include buyer information"""
        response = requests.get(f"{BASE_URL}/api/admin/rfqs/{self.test_rfq_id}", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "buyer_info" in data, "Missing buyer_info"
        
        buyer_info = data["buyer_info"]
        # Buyer info should have name and email at minimum
        if buyer_info:
            # At least some buyer fields should be present
            possible_fields = ["name", "email", "phone", "company_name", "city", "state", "country"]
            has_field = any(field in buyer_info and buyer_info[field] for field in possible_fields)
            assert has_field or buyer_info is None, "buyer_info should have at least one field or be None"
    
    def test_03_get_rfq_details_includes_drawings(self):
        """Test that RFQ details include drawings array"""
        response = requests.get(f"{BASE_URL}/api/admin/rfqs/{self.test_rfq_id}", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "drawings" in data, "Missing drawings field"
        assert isinstance(data["drawings"], list), "drawings should be a list"
        
        # If drawings exist, verify they don't include raw file_data (for performance)
        for drawing in data["drawings"]:
            assert "file_data" not in drawing, "drawings should not include file_data for performance"
    
    def test_04_get_rfq_details_includes_quotes(self):
        """Test that RFQ details include quotes array"""
        response = requests.get(f"{BASE_URL}/api/admin/rfqs/{self.test_rfq_id}", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "quotes" in data, "Missing quotes field"
        assert isinstance(data["quotes"], list), "quotes should be a list"
        
        # If quotes exist, verify they have vendor_info
        for quote in data["quotes"]:
            assert "vendor_info" in quote, "Each quote should have vendor_info"
    
    def test_05_get_rfq_details_includes_matched_vendors_details(self):
        """Test that RFQ details include matched_vendors_details"""
        response = requests.get(f"{BASE_URL}/api/admin/rfqs/{self.test_rfq_id}", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "matched_vendors_details" in data, "Missing matched_vendors_details"
        assert isinstance(data["matched_vendors_details"], list), "matched_vendors_details should be a list"
    
    def test_06_get_rfq_details_includes_ai_summary(self):
        """Test that RFQ details include AI summary"""
        response = requests.get(f"{BASE_URL}/api/admin/rfqs/{self.test_rfq_id}", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "ai_summary" in data, "Missing ai_summary field"
        
        ai_summary = data["ai_summary"]
        # AI summary should have these keys (can be empty)
        expected_keys = ["recommended_processes", "overall_dimensions", "material_suggestions", "complexity_score", "part_geometry"]
        for key in expected_keys:
            assert key in ai_summary, f"ai_summary missing key: {key}"
    
    def test_07_get_rfq_details_nonexistent(self):
        """Test getting details for nonexistent RFQ returns 404"""
        response = requests.get(f"{BASE_URL}/api/admin/rfqs/nonexistent_rfq_123", headers=self.headers)
        assert response.status_code == 404, f"Expected 404 for nonexistent RFQ, got {response.status_code}"
    
    def test_08_get_rfq_details_without_auth(self):
        """Test getting RFQ details without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/admin/rfqs/{self.test_rfq_id}")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
    
    # ============ GET /api/admin/rfqs/{rfq_id}/pdf Tests ============
    
    def test_09_get_rfq_pdf_success(self):
        """Test downloading RFQ as PDF returns valid PDF"""
        response = requests.get(f"{BASE_URL}/api/admin/rfqs/{self.test_rfq_id}/pdf", headers=self.headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify content type is PDF
        content_type = response.headers.get("Content-Type", "")
        assert "application/pdf" in content_type, f"Expected application/pdf, got {content_type}"
        
        # Verify Content-Disposition header for download
        content_disposition = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disposition, "Missing attachment in Content-Disposition"
        assert self.test_rfq_id in content_disposition, "RFQ ID should be in filename"
    
    def test_10_get_rfq_pdf_valid_content(self):
        """Test PDF content starts with PDF magic bytes"""
        response = requests.get(f"{BASE_URL}/api/admin/rfqs/{self.test_rfq_id}/pdf", headers=self.headers)
        assert response.status_code == 200
        
        # PDF files start with %PDF
        content = response.content
        assert len(content) > 100, "PDF should have substantial content"
        assert content[:4] == b'%PDF', f"PDF should start with %PDF magic bytes, got: {content[:10]}"
    
    def test_11_get_rfq_pdf_nonexistent(self):
        """Test downloading PDF for nonexistent RFQ returns 404"""
        response = requests.get(f"{BASE_URL}/api/admin/rfqs/nonexistent_rfq_123/pdf", headers=self.headers)
        assert response.status_code == 404, f"Expected 404 for nonexistent RFQ, got {response.status_code}"
    
    def test_12_get_rfq_pdf_without_auth(self):
        """Test downloading PDF without auth returns 401"""
        response = requests.get(f"{BASE_URL}/api/admin/rfqs/{self.test_rfq_id}/pdf")
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
    
    # ============ Additional Integration Tests ============
    
    def test_13_get_rfq_details_has_material_and_quantity(self):
        """Test that RFQ details include material_type and quantity"""
        response = requests.get(f"{BASE_URL}/api/admin/rfqs/{self.test_rfq_id}", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "material_type" in data, "Missing material_type"
        assert "quantity" in data, "Missing quantity"
    
    def test_14_get_rfq_details_has_tolerance(self):
        """Test that RFQ details include tolerance"""
        response = requests.get(f"{BASE_URL}/api/admin/rfqs/{self.test_rfq_id}", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "tolerance" in data, "Missing tolerance field"
    
    def test_15_pdf_has_reasonable_size(self):
        """Test PDF file has reasonable size (not too small, not too large)"""
        response = requests.get(f"{BASE_URL}/api/admin/rfqs/{self.test_rfq_id}/pdf", headers=self.headers)
        assert response.status_code == 200
        
        content = response.content
        # PDF should be at least 1KB and less than 10MB
        assert len(content) > 1000, f"PDF too small: {len(content)} bytes"
        assert len(content) < 10 * 1024 * 1024, f"PDF too large: {len(content)} bytes"


class TestRFQDetailsWithDifferentRFQs:
    """Test with different RFQ scenarios"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@offoadex.com",
            "password": "admin123"
        })
        assert response.status_code == 200
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_16_get_list_of_rfqs_has_rfqs(self):
        """Verify there are RFQs to test with"""
        response = requests.get(f"{BASE_URL}/api/admin/rfqs", headers=self.headers)
        assert response.status_code == 200
        
        data = response.json()
        # API returns a list directly, not {"rfqs": [...]}
        assert isinstance(data, list), "Response should be a list of RFQs"
        assert len(data) > 0, "No RFQs found in the system"
    
    def test_17_get_details_for_first_available_rfq(self):
        """Get details for first available RFQ"""
        # Get list of RFQs
        list_response = requests.get(f"{BASE_URL}/api/admin/rfqs", headers=self.headers)
        assert list_response.status_code == 200
        
        rfqs = list_response.json()  # API returns list directly
        assert isinstance(rfqs, list), "Response should be a list"
        if len(rfqs) > 0:
            first_rfq_id = rfqs[0]["rfq_id"]
            
            # Get details
            details_response = requests.get(f"{BASE_URL}/api/admin/rfqs/{first_rfq_id}", headers=self.headers)
            assert details_response.status_code == 200
            
            data = details_response.json()
            assert data["rfq_id"] == first_rfq_id
            assert "buyer_info" in data
            assert "drawings" in data
            assert "quotes" in data
    
    def test_18_generate_pdf_for_first_available_rfq(self):
        """Generate PDF for first available RFQ"""
        # Get list of RFQs
        list_response = requests.get(f"{BASE_URL}/api/admin/rfqs", headers=self.headers)
        assert list_response.status_code == 200
        
        rfqs = list_response.json()  # API returns list directly
        assert isinstance(rfqs, list), "Response should be a list"
        if len(rfqs) > 0:
            first_rfq_id = rfqs[0]["rfq_id"]
            
            # Get PDF
            pdf_response = requests.get(f"{BASE_URL}/api/admin/rfqs/{first_rfq_id}/pdf", headers=self.headers)
            assert pdf_response.status_code == 200
            assert "application/pdf" in pdf_response.headers.get("Content-Type", "")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
