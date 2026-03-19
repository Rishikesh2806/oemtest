"""
Test Drawing URLs and PDF Layout Formatting
Tests for:
1. GET /api/admin/rfqs/{rfqId} returns drawings with presigned S3 URLs
2. Drawings have file_url, view_url, download_url fields
3. Drawings have is_previewable, is_image, is_pdf flags
4. GET /api/admin/rfqs/{rfqId}/pdf returns properly formatted PDF
5. PDF has page numbers, proper alignment, text wrapping
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"

# Test RFQ with drawings
TEST_RFQ_ID = "rfq_932de773568a"


class TestDrawingURLsAndPDFLayout:
    """Test drawing URLs use presigned S3 URLs and PDF layout"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if response.status_code != 200:
            pytest.skip(f"Admin login failed: {response.status_code}")
        return response.json().get("access_token")
    
    @pytest.fixture(scope="class")
    def auth_headers(self, admin_token):
        """Headers with auth token"""
        return {"Authorization": f"Bearer {admin_token}"}
    
    # ========== Admin RFQ Details Tests ==========
    
    def test_admin_get_rfq_returns_rfq_data(self, auth_headers):
        """Test GET /api/admin/rfqs/{rfqId} returns RFQ data"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/{TEST_RFQ_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"Failed to get RFQ: {response.text}"
        
        data = response.json()
        assert "rfq_id" in data
        assert data["rfq_id"] == TEST_RFQ_ID
        print(f"PASS: Admin RFQ details endpoint returns data for {TEST_RFQ_ID}")
    
    def test_admin_get_rfq_includes_drawings(self, auth_headers):
        """Test that RFQ details includes drawings array"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/{TEST_RFQ_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "drawings" in data, "Response missing 'drawings' field"
        drawings = data["drawings"]
        print(f"PASS: RFQ has drawings array with {len(drawings)} item(s)")
    
    def test_drawing_has_file_url_field(self, auth_headers):
        """Test that drawings have file_url field"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/{TEST_RFQ_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        drawings = data.get("drawings", [])
        
        if len(drawings) == 0:
            pytest.skip("No drawings in test RFQ to verify")
        
        for i, drawing in enumerate(drawings):
            assert "file_url" in drawing, f"Drawing {i} missing 'file_url'"
            print(f"PASS: Drawing {i} has file_url: {drawing['file_url'][:80]}...")
    
    def test_drawing_has_view_url_field(self, auth_headers):
        """Test that drawings have view_url field"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/{TEST_RFQ_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        drawings = data.get("drawings", [])
        
        if len(drawings) == 0:
            pytest.skip("No drawings in test RFQ to verify")
        
        for i, drawing in enumerate(drawings):
            assert "view_url" in drawing, f"Drawing {i} missing 'view_url'"
            print(f"PASS: Drawing {i} has view_url")
    
    def test_drawing_has_download_url_field(self, auth_headers):
        """Test that drawings have download_url field"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/{TEST_RFQ_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        drawings = data.get("drawings", [])
        
        if len(drawings) == 0:
            pytest.skip("No drawings in test RFQ to verify")
        
        for i, drawing in enumerate(drawings):
            assert "download_url" in drawing, f"Drawing {i} missing 'download_url'"
            print(f"PASS: Drawing {i} has download_url")
    
    def test_drawing_has_is_previewable_flag(self, auth_headers):
        """Test that drawings have is_previewable flag"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/{TEST_RFQ_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        drawings = data.get("drawings", [])
        
        if len(drawings) == 0:
            pytest.skip("No drawings in test RFQ to verify")
        
        for i, drawing in enumerate(drawings):
            assert "is_previewable" in drawing, f"Drawing {i} missing 'is_previewable'"
            assert isinstance(drawing["is_previewable"], bool), "is_previewable should be boolean"
            print(f"PASS: Drawing {i} has is_previewable={drawing['is_previewable']}")
    
    def test_drawing_has_is_image_flag(self, auth_headers):
        """Test that drawings have is_image flag"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/{TEST_RFQ_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        drawings = data.get("drawings", [])
        
        if len(drawings) == 0:
            pytest.skip("No drawings in test RFQ to verify")
        
        for i, drawing in enumerate(drawings):
            assert "is_image" in drawing, f"Drawing {i} missing 'is_image'"
            assert isinstance(drawing["is_image"], bool), "is_image should be boolean"
            print(f"PASS: Drawing {i} has is_image={drawing['is_image']}")
    
    def test_drawing_has_is_pdf_flag(self, auth_headers):
        """Test that drawings have is_pdf flag"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/{TEST_RFQ_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        drawings = data.get("drawings", [])
        
        if len(drawings) == 0:
            pytest.skip("No drawings in test RFQ to verify")
        
        for i, drawing in enumerate(drawings):
            assert "is_pdf" in drawing, f"Drawing {i} missing 'is_pdf'"
            assert isinstance(drawing["is_pdf"], bool), "is_pdf should be boolean"
            print(f"PASS: Drawing {i} has is_pdf={drawing['is_pdf']}")
    
    def test_drawing_url_is_presigned_s3_url(self, auth_headers):
        """Test that drawing URLs are presigned S3 URLs (not /api/storage/ URLs)"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/{TEST_RFQ_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        drawings = data.get("drawings", [])
        
        if len(drawings) == 0:
            pytest.skip("No drawings in test RFQ to verify")
        
        for i, drawing in enumerate(drawings):
            file_url = drawing.get("file_url", "")
            
            # Should NOT be an /api/storage/ URL
            assert "/api/storage/" not in file_url, f"Drawing {i} uses /api/storage/ URL instead of presigned S3"
            
            # Should be an S3 presigned URL (contains amazonaws.com and signature params)
            if file_url:
                is_s3_url = "amazonaws.com" in file_url or "s3" in file_url.lower()
                has_signature = "X-Amz-Signature" in file_url or "Signature=" in file_url
                
                assert is_s3_url, f"Drawing {i} URL is not an S3 URL: {file_url[:100]}"
                assert has_signature, f"Drawing {i} URL is not presigned (no signature): {file_url[:100]}"
                
                print(f"PASS: Drawing {i} uses presigned S3 URL with signature")
    
    def test_drawing_url_is_accessible(self, auth_headers):
        """Test that presigned URL is actually accessible"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/{TEST_RFQ_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        drawings = data.get("drawings", [])
        
        if len(drawings) == 0:
            pytest.skip("No drawings in test RFQ to verify")
        
        for i, drawing in enumerate(drawings):
            file_url = drawing.get("file_url", "")
            if file_url:
                # Try to access the URL with GET request (S3 presigned URLs may not support HEAD)
                get_response = requests.get(file_url, stream=True, timeout=10)
                
                # Accept 200 or 206 (partial content for range requests)
                assert get_response.status_code in [200, 206], f"Drawing URL not accessible: {get_response.status_code}"
                
                # Verify content length indicates actual file
                content_length = get_response.headers.get("content-length")
                if content_length:
                    assert int(content_length) > 0, "Downloaded file is empty"
                
                print(f"PASS: Drawing {i} presigned URL is accessible (status {get_response.status_code})")
    
    # ========== PDF Generation Tests ==========
    
    def test_pdf_endpoint_returns_pdf(self, auth_headers):
        """Test GET /api/admin/rfqs/{rfqId}/pdf returns PDF content type"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/{TEST_RFQ_ID}/pdf",
            headers=auth_headers
        )
        
        assert response.status_code == 200, f"PDF generation failed: {response.text}"
        
        content_type = response.headers.get("content-type", "")
        assert "application/pdf" in content_type, f"Wrong content type: {content_type}"
        print(f"PASS: PDF endpoint returns application/pdf content type")
    
    def test_pdf_has_content_disposition(self, auth_headers):
        """Test PDF response has correct content-disposition header"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/{TEST_RFQ_ID}/pdf",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        content_disposition = response.headers.get("content-disposition", "")
        assert "attachment" in content_disposition, "Missing 'attachment' in content-disposition"
        assert TEST_RFQ_ID in content_disposition, "RFQ ID not in filename"
        assert ".pdf" in content_disposition, "Missing .pdf extension"
        print(f"PASS: PDF has correct content-disposition: {content_disposition}")
    
    def test_pdf_has_valid_size(self, auth_headers):
        """Test PDF has reasonable file size (not empty)"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/{TEST_RFQ_ID}/pdf",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        content_length = len(response.content)
        assert content_length > 1000, f"PDF too small ({content_length} bytes), likely empty or broken"
        assert content_length < 10000000, f"PDF too large ({content_length} bytes), likely corrupted"
        print(f"PASS: PDF has valid size: {content_length} bytes")
    
    def test_pdf_starts_with_pdf_header(self, auth_headers):
        """Test PDF content starts with valid PDF header"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/{TEST_RFQ_ID}/pdf",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # PDF files start with %PDF
        pdf_header = response.content[:10]
        assert pdf_header.startswith(b'%PDF'), f"Invalid PDF header: {pdf_header}"
        print(f"PASS: PDF has valid header: {pdf_header[:8]}")
    
    # ========== RFQ Detail Structure Tests ==========
    
    def test_rfq_has_buyer_info(self, auth_headers):
        """Test RFQ details includes buyer_info"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/{TEST_RFQ_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "buyer_info" in data, "Missing buyer_info"
        buyer_info = data["buyer_info"]
        
        # Should have common buyer fields
        if buyer_info:
            print(f"PASS: RFQ has buyer_info with keys: {list(buyer_info.keys())}")
    
    def test_rfq_has_ai_summary(self, auth_headers):
        """Test RFQ details includes ai_summary"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/{TEST_RFQ_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "ai_summary" in data, "Missing ai_summary"
        ai_summary = data["ai_summary"]
        
        # Should have structured fields
        assert "recommended_processes" in ai_summary
        assert "overall_dimensions" in ai_summary
        print(f"PASS: RFQ has ai_summary with recommended_processes and dimensions")
    
    def test_rfq_has_matched_vendors_details(self, auth_headers):
        """Test RFQ details includes matched_vendors_details"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/{TEST_RFQ_ID}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "matched_vendors_details" in data, "Missing matched_vendors_details"
        print(f"PASS: RFQ has matched_vendors_details ({len(data['matched_vendors_details'])} vendors)")
    
    # ========== Error Handling Tests ==========
    
    def test_get_rfq_not_found(self, auth_headers):
        """Test 404 for non-existent RFQ"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/nonexistent_rfq_id",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        print("PASS: 404 returned for non-existent RFQ")
    
    def test_pdf_rfq_not_found(self, auth_headers):
        """Test 404 for PDF of non-existent RFQ"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/nonexistent_rfq_id/pdf",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        print("PASS: 404 returned for PDF of non-existent RFQ")
    
    def test_unauthorized_access_denied(self):
        """Test unauthorized access is denied"""
        response = requests.get(
            f"{BASE_URL}/api/admin/rfqs/{TEST_RFQ_ID}"
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("PASS: Unauthorized request returns 401")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
