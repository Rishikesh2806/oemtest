"""
Tests for AWS S3 File Management Integration
Tests admin file manager endpoints and machine image uploads to S3
"""
import pytest
import requests
import os
import time
import base64

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"
VENDOR_EMAIL = "vendor@offoadex.com"
VENDOR_PASSWORD = "vendor123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.status_code} - {response.text}")
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def vendor_token():
    """Get vendor authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": VENDOR_EMAIL,
        "password": VENDOR_PASSWORD
    })
    if response.status_code != 200:
        pytest.skip(f"Vendor login failed: {response.status_code} - {response.text}")
    return response.json().get("access_token")


@pytest.fixture(scope="module")
def vendor_info(vendor_token):
    """Get vendor user info"""
    response = requests.get(f"{BASE_URL}/api/auth/me", headers={
        "Authorization": f"Bearer {vendor_token}"
    })
    if response.status_code != 200:
        pytest.skip(f"Failed to get vendor info: {response.status_code}")
    return response.json()


class TestAdminFileStats:
    """Test /api/admin/files/stats endpoint - S3 bucket statistics"""
    
    def test_admin_can_get_file_stats(self, admin_token):
        """Admin should be able to get S3 storage statistics"""
        response = requests.get(
            f"{BASE_URL}/api/admin/files/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Failed to get stats: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "total_files" in data, "Missing total_files"
        assert "total_size_mb" in data, "Missing total_size_mb"
        assert "machine_images" in data, "Missing machine_images"
        assert "drawings" in data, "Missing drawings"
        assert "storage" in data, "Missing storage type"
        assert "bucket" in data, "Missing bucket name"
        
        # Verify data types
        assert isinstance(data["total_files"], int), "total_files should be int"
        assert isinstance(data["machine_images"], int), "machine_images should be int"
        assert isinstance(data["drawings"], int), "drawings should be int"
        
        # Verify it's AWS S3
        assert data["storage"] == "AWS S3", f"Expected AWS S3, got {data['storage']}"
        assert "oemlinker" in data["bucket"].lower(), f"Unexpected bucket: {data['bucket']}"
        
        print(f"S3 Stats: {data['total_files']} files, {data['total_size_mb']} MB, bucket: {data['bucket']}")
    
    def test_non_admin_cannot_access_stats(self, vendor_token):
        """Non-admin users should not access file stats"""
        response = requests.get(
            f"{BASE_URL}/api/admin/files/stats",
            headers={"Authorization": f"Bearer {vendor_token}"}
        )
        
        # Should return 403 Forbidden
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_unauthenticated_cannot_access_stats(self):
        """Unauthenticated requests should be rejected"""
        response = requests.get(f"{BASE_URL}/api/admin/files/stats")
        
        # Should return 401 Unauthorized
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestAdminFileList:
    """Test /api/admin/files endpoint - List S3 files"""
    
    def test_admin_can_list_all_files(self, admin_token):
        """Admin should be able to list all files in S3"""
        response = requests.get(
            f"{BASE_URL}/api/admin/files",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Failed to list files: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "files" in data, "Missing files array"
        assert "total" in data, "Missing total count"
        assert isinstance(data["files"], list), "files should be a list"
        
        # Check each file has required fields
        for file in data["files"]:
            assert "path" in file, "File missing path"
            assert "name" in file, "File missing name"
            assert "size" in file, "File missing size"
            assert "url" in file or "storage_url" in file, "File missing URL"
        
        print(f"Listed {data['total']} files from S3")
    
    def test_admin_can_filter_by_machines_prefix(self, admin_token):
        """Admin should be able to filter files by machines prefix"""
        response = requests.get(
            f"{BASE_URL}/api/admin/files?prefix=machines",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Failed to filter files: {response.text}"
        
        data = response.json()
        
        # All returned files should be in machines folder
        for file in data["files"]:
            assert "machines" in file["path"].lower(), f"File {file['path']} not in machines folder"
        
        print(f"Filtered {len(data['files'])} machine images")
    
    def test_admin_can_filter_by_drawings_prefix(self, admin_token):
        """Admin should be able to filter files by drawings prefix"""
        response = requests.get(
            f"{BASE_URL}/api/admin/files?prefix=drawings",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200, f"Failed to filter files: {response.text}"
        
        data = response.json()
        
        # All returned files should be in drawings folder
        for file in data["files"]:
            assert "drawings" in file["path"].lower(), f"File {file['path']} not in drawings folder"
        
        print(f"Filtered {len(data['files'])} drawings")
    
    def test_non_admin_cannot_list_files(self, vendor_token):
        """Non-admin users should not list files"""
        response = requests.get(
            f"{BASE_URL}/api/admin/files",
            headers={"Authorization": f"Bearer {vendor_token}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"


class TestFileViewing:
    """Test viewing files from S3 storage"""
    
    def test_can_view_s3_file_via_storage_endpoint(self, admin_token):
        """Should be able to view S3 files via /api/storage/{path} endpoint"""
        # First get list of files
        list_response = requests.get(
            f"{BASE_URL}/api/admin/files",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert list_response.status_code == 200
        files = list_response.json().get("files", [])
        
        if not files:
            pytest.skip("No files in S3 to test viewing")
        
        # Try to view the first file
        first_file = files[0]
        storage_url = first_file.get("storage_url", "")
        
        if storage_url:
            # Remove leading /api if present
            if storage_url.startswith("/api"):
                storage_url = storage_url
            
            view_response = requests.get(f"{BASE_URL}{storage_url}")
            
            # Should return 200 with file content
            assert view_response.status_code == 200, f"Failed to view file: {view_response.status_code}"
            assert len(view_response.content) > 0, "File content is empty"
            
            print(f"Successfully viewed file: {first_file['name']} ({len(view_response.content)} bytes)")


class TestFileDelete:
    """Test file deletion from S3 - requires careful handling"""
    
    def test_delete_endpoint_requires_admin(self, vendor_token):
        """Delete endpoint should require admin role"""
        response = requests.delete(
            f"{BASE_URL}/api/admin/files/test/file.jpg",
            headers={"Authorization": f"Bearer {vendor_token}"}
        )
        
        assert response.status_code == 403, f"Expected 403, got {response.status_code}"
    
    def test_delete_nonexistent_file_returns_error(self, admin_token):
        """Deleting a non-existent file should return success or not found"""
        response = requests.delete(
            f"{BASE_URL}/api/admin/files/nonexistent_test_file_12345.jpg",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        # S3 delete is idempotent, may return 200 even for non-existent files
        # Or might return 404 depending on implementation
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"


class TestMachineImageUpload:
    """Test machine image upload to S3"""
    
    def test_vendor_can_upload_machine_image(self, vendor_token, vendor_info):
        """Vendor should be able to upload machine images to S3"""
        # First, we need to get vendor's machines
        vendor_id = vendor_info.get("user_id")
        
        # Get vendor profile to get vendor_id
        profile_response = requests.get(
            f"{BASE_URL}/api/vendors/profile",
            headers={"Authorization": f"Bearer {vendor_token}"}
        )
        
        if profile_response.status_code != 200:
            pytest.skip("Vendor profile not found")
        
        profile = profile_response.json()
        actual_vendor_id = profile.get("vendor_id")
        
        # Get vendor's machines
        machines_response = requests.get(
            f"{BASE_URL}/api/machines",
            headers={"Authorization": f"Bearer {vendor_token}"}
        )
        
        if machines_response.status_code != 200:
            pytest.skip("No machines available for vendor")
        
        machines = machines_response.json()
        
        if not machines:
            pytest.skip("Vendor has no machines to test image upload")
        
        machine_id = machines[0].get("machine_id")
        
        # Create a small test PNG image (1x1 pixel red)
        # PNG header with 1x1 red pixel
        test_image = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
        )
        
        # Upload to machine
        files = {"file": ("test_image.png", test_image, "image/png")}
        
        upload_response = requests.post(
            f"{BASE_URL}/api/machines/{machine_id}/images",
            headers={"Authorization": f"Bearer {vendor_token}"},
            files=files
        )
        
        assert upload_response.status_code == 200, f"Upload failed: {upload_response.text}"
        
        data = upload_response.json()
        
        # Verify S3 URL returned
        assert "image_url" in data, "Missing image_url in response"
        image_url = data["image_url"]
        
        # Check it's an S3 URL
        assert "s3" in image_url.lower() or "amazonaws" in image_url.lower(), \
            f"Image URL doesn't appear to be S3: {image_url}"
        
        print(f"Successfully uploaded machine image to S3: {image_url}")
        
        # Verify image is accessible
        img_response = requests.get(image_url)
        assert img_response.status_code == 200, f"Cannot access uploaded image: {img_response.status_code}"
        
        # Store for cleanup
        return {"machine_id": machine_id, "image_url": image_url}


class TestS3IntegrationVerification:
    """Verify S3 integration is working end-to-end"""
    
    def test_s3_bucket_accessible(self, admin_token):
        """Verify S3 bucket is accessible and configured"""
        response = requests.get(
            f"{BASE_URL}/api/admin/files/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Verify S3 configuration
        assert data["storage"] == "AWS S3", "Storage should be AWS S3"
        assert data["bucket"] == "oemlinker-storage", f"Unexpected bucket: {data['bucket']}"
        
        print(f"S3 Integration verified: bucket={data['bucket']}, files={data['total_files']}")
    
    def test_files_have_s3_urls(self, admin_token):
        """Verify files are stored with proper S3 URLs"""
        response = requests.get(
            f"{BASE_URL}/api/admin/files",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        assert response.status_code == 200
        
        files = response.json().get("files", [])
        
        for file in files:
            url = file.get("url", "")
            # S3 URLs should contain amazonaws.com or the bucket name
            assert "amazonaws.com" in url or "oemlinker" in url, \
                f"File URL doesn't appear to be S3: {url}"
        
        print(f"Verified {len(files)} files have S3 URLs")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
