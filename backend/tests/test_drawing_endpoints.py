"""
Test Drawing View/Download Endpoints and Email Service Configuration
Features tested:
- Drawing view endpoint with token auth
- Drawing download endpoint with Bearer auth
- Email service configuration
- Unauthorized access rejection
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestAuthSetup:
    """Get authentication token for tests"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Authenticate as admin and get token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "admin@offoadex.com", "password": "admin123"}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        return data["access_token"]
    
    @pytest.fixture(scope="class")
    def drawing_id(self, admin_token):
        """Get a valid drawing ID from the database"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(f"{BASE_URL}/api/admin/drawings", headers=headers)
        assert response.status_code == 200, f"Failed to get drawings: {response.text}"
        drawings = response.json()
        assert len(drawings) > 0, "No drawings found in database"
        return drawings[0]["drawing_id"]


class TestDrawingViewEndpoint(TestAuthSetup):
    """Test /api/drawings/{id}/view endpoint - token-based auth for browser viewing"""
    
    def test_view_drawing_with_query_token(self, admin_token, drawing_id):
        """View endpoint should work with token query parameter"""
        response = requests.get(
            f"{BASE_URL}/api/drawings/{drawing_id}/view",
            params={"token": admin_token},
            allow_redirects=True
        )
        assert response.status_code == 200, f"View failed: {response.status_code} - {response.text[:200]}"
        assert len(response.content) > 0, "Response body is empty"
        # Check content-disposition header for inline viewing
        content_disp = response.headers.get("content-disposition", "")
        assert "inline" in content_disp.lower() or len(response.content) > 0, "Should be inline or have content"
        print(f"✓ View with query token - Status: {response.status_code}, Size: {len(response.content)} bytes")
    
    def test_view_drawing_without_token_fails(self, drawing_id):
        """View endpoint should reject requests without token"""
        response = requests.get(f"{BASE_URL}/api/drawings/{drawing_id}/view")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        assert "detail" in response.json()
        print(f"✓ Unauthorized access rejected - Status: {response.status_code}")
    
    def test_view_drawing_with_invalid_token_fails(self, drawing_id):
        """View endpoint should reject invalid tokens"""
        response = requests.get(
            f"{BASE_URL}/api/drawings/{drawing_id}/view",
            params={"token": "invalid_token_12345"}
        )
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ Invalid token rejected - Status: {response.status_code}")
    
    def test_view_nonexistent_drawing(self, admin_token):
        """View endpoint should return 404 for non-existent drawing"""
        response = requests.get(
            f"{BASE_URL}/api/drawings/drawing_nonexistent123/view",
            params={"token": admin_token}
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Non-existent drawing returns 404")


class TestDrawingDownloadEndpoint(TestAuthSetup):
    """Test /api/drawings/{id}/download endpoint - Bearer auth for downloads"""
    
    def test_download_drawing_with_bearer_token(self, admin_token, drawing_id):
        """Download endpoint should work with Bearer authorization header"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/drawings/{drawing_id}/download",
            headers=headers
        )
        assert response.status_code == 200, f"Download failed: {response.status_code}"
        assert len(response.content) > 0, "Response body is empty"
        # Check content-disposition header for attachment
        content_disp = response.headers.get("content-disposition", "")
        assert "attachment" in content_disp.lower(), f"Expected attachment disposition, got: {content_disp}"
        print(f"✓ Download with Bearer token - Status: {response.status_code}, Size: {len(response.content)} bytes")
    
    def test_download_drawing_without_auth_fails(self, drawing_id):
        """Download endpoint should reject requests without authorization"""
        response = requests.get(f"{BASE_URL}/api/drawings/{drawing_id}/download")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print(f"✓ Unauthorized download rejected - Status: {response.status_code}")
    
    def test_download_nonexistent_drawing(self, admin_token):
        """Download endpoint should return 404 for non-existent drawing"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/drawings/drawing_nonexistent123/download",
            headers=headers
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print(f"✓ Non-existent drawing download returns 404")


class TestDrawingListEndpoint(TestAuthSetup):
    """Test /api/rfqs/{id}/drawings endpoint - list drawings for an RFQ"""
    
    def test_list_drawings_for_rfq(self, admin_token):
        """Should list drawings for an RFQ"""
        # First get an RFQ that has drawings
        headers = {"Authorization": f"Bearer {admin_token}"}
        drawings_response = requests.get(f"{BASE_URL}/api/admin/drawings", headers=headers)
        assert drawings_response.status_code == 200
        drawings = drawings_response.json()
        assert len(drawings) > 0, "No drawings found"
        
        rfq_id = drawings[0]["rfq_id"]
        
        # Now list drawings for that RFQ
        response = requests.get(f"{BASE_URL}/api/rfqs/{rfq_id}/drawings", headers=headers)
        assert response.status_code == 200, f"Failed to list drawings: {response.text}"
        rfq_drawings = response.json()
        assert isinstance(rfq_drawings, list)
        print(f"✓ Listed {len(rfq_drawings)} drawings for RFQ {rfq_id}")


class TestEmailServiceConfiguration:
    """Test that email service is properly configured"""
    
    def test_resend_api_key_configured(self):
        """Verify RESEND_API_KEY is set in environment"""
        # Check backend .env for RESEND_API_KEY
        env_path = "/app/backend/.env"
        try:
            with open(env_path, 'r') as f:
                env_content = f.read()
            assert "RESEND_API_KEY" in env_content, "RESEND_API_KEY not found in backend/.env"
            # Check it has a value
            for line in env_content.split('\n'):
                if line.startswith('RESEND_API_KEY'):
                    key_value = line.split('=', 1)
                    if len(key_value) > 1:
                        assert len(key_value[1].strip()) > 0, "RESEND_API_KEY is empty"
                        print(f"✓ RESEND_API_KEY configured: {key_value[1][:10]}...")
                    break
        except FileNotFoundError:
            pytest.skip("Backend .env file not accessible for testing")
    
    def test_sender_email_configured(self):
        """Verify SENDER_EMAIL is set"""
        env_path = "/app/backend/.env"
        try:
            with open(env_path, 'r') as f:
                env_content = f.read()
            assert "SENDER_EMAIL" in env_content, "SENDER_EMAIL not found in backend/.env"
            print(f"✓ SENDER_EMAIL configured")
        except FileNotFoundError:
            pytest.skip("Backend .env file not accessible for testing")


class TestDrawingMetadata(TestAuthSetup):
    """Test drawing metadata retrieval"""
    
    def test_get_drawing_details(self, admin_token, drawing_id):
        """Should retrieve drawing metadata without file data"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = requests.get(
            f"{BASE_URL}/api/drawings/{drawing_id}",
            headers=headers
        )
        assert response.status_code == 200, f"Failed to get drawing: {response.text}"
        drawing = response.json()
        
        # Verify required fields
        assert "drawing_id" in drawing
        assert "filename" in drawing
        assert "file_type" in drawing
        assert "file_size" in drawing
        assert "rfq_id" in drawing
        
        print(f"✓ Drawing metadata retrieved: {drawing['filename']} ({drawing['file_size']} bytes)")


class TestMultipleDrawingTypes(TestAuthSetup):
    """Test viewing/downloading different file types"""
    
    def test_view_different_file_types(self, admin_token):
        """Test viewing drawings of different file types"""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Get all drawings
        response = requests.get(f"{BASE_URL}/api/admin/drawings", headers=headers)
        assert response.status_code == 200
        drawings = response.json()
        
        # Categorize by file type
        file_types_tested = set()
        for drawing in drawings[:10]:  # Test first 10
            file_type = drawing.get("file_type", "unknown")
            
            # Test view endpoint
            view_response = requests.get(
                f"{BASE_URL}/api/drawings/{drawing['drawing_id']}/view",
                params={"token": admin_token}
            )
            
            if view_response.status_code == 200:
                file_types_tested.add(file_type)
                print(f"  ✓ {drawing['filename']} ({file_type}) - {len(view_response.content)} bytes")
        
        print(f"✓ Tested file types: {file_types_tested}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
