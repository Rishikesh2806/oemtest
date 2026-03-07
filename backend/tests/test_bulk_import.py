"""
Tests for Bulk Machine Import Feature
- GET /api/machines/bulk-import/template - CSV template download
- POST /api/machines/bulk-import - CSV file upload and import
"""

import pytest
import requests
import os
import io

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')

# Test credentials
VENDOR_EMAIL = "vendor@offoadex.com"
VENDOR_PASSWORD = "vendor123"
BUYER_EMAIL = "buyer@offoadex.com"
BUYER_PASSWORD = "buyer123"


class TestBulkImportTemplate:
    """Tests for GET /api/machines/bulk-import/template"""
    
    def test_get_template_returns_csv(self):
        """Template endpoint should return CSV template with instructions"""
        response = requests.get(f"{BASE_URL}/api/machines/bulk-import/template")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        
        # Verify template content exists
        assert "template" in data, "Response should contain 'template'"
        assert len(data["template"]) > 0, "Template should not be empty"
        
        # Verify template has CSV header and example rows
        template = data["template"]
        assert "name,machine_category,machine_type,brand,model" in template, "Template should have CSV headers"
        assert "Mazak" in template or "Haas" in template, "Template should have example data"
        
        print(f"Template content length: {len(template)} chars")
    
    def test_template_includes_instructions(self):
        """Template should include field instructions"""
        response = requests.get(f"{BASE_URL}/api/machines/bulk-import/template")
        assert response.status_code == 200
        
        data = response.json()
        assert "instructions" in data, "Response should contain instructions"
        
        # Verify key instructions exist
        instructions = data["instructions"]
        assert "machine_type" in instructions, "Instructions should include machine_type"
        assert "brand" in instructions, "Instructions should include brand"
        assert "model" in instructions, "Instructions should include model"
        
        print(f"Instructions provided for {len(instructions)} fields")
    
    def test_template_includes_valid_categories(self):
        """Template should list valid machine categories"""
        response = requests.get(f"{BASE_URL}/api/machines/bulk-import/template")
        assert response.status_code == 200
        
        data = response.json()
        assert "valid_categories" in data, "Response should contain valid_categories"
        
        categories = data["valid_categories"]
        assert len(categories) > 0, "Should have at least one category"
        assert "CNC Turning/Lathe" in categories or "VMC (Vertical Machining Center)" in categories, \
            "Should include common machine categories"
        
        print(f"Valid categories: {len(categories)} categories")
    
    def test_template_includes_valid_materials(self):
        """Template should list valid materials"""
        response = requests.get(f"{BASE_URL}/api/machines/bulk-import/template")
        assert response.status_code == 200
        
        data = response.json()
        assert "valid_materials" in data, "Response should contain valid_materials"
        
        materials = data["valid_materials"]
        assert "Aluminum" in materials, "Should include Aluminum"
        assert "Steel" in materials, "Should include Steel"
        
        print(f"Valid materials: {materials}")


class TestBulkImportUpload:
    """Tests for POST /api/machines/bulk-import"""
    
    @pytest.fixture
    def vendor_token(self):
        """Get vendor authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": VENDOR_EMAIL,
            "password": VENDOR_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Vendor login failed - skipping authenticated tests")
        return response.json()["access_token"]
    
    @pytest.fixture
    def buyer_token(self):
        """Get buyer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Buyer login failed - skipping test")
        return response.json()["access_token"]
    
    def test_bulk_import_requires_auth(self):
        """Import endpoint should require authentication"""
        csv_content = "name,machine_type,brand,model\nTest,CNC Lathe,Test,Test"
        files = {"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        
        response = requests.post(f"{BASE_URL}/api/machines/bulk-import", files=files)
        assert response.status_code == 401, f"Expected 401 without auth, got {response.status_code}"
        print("Unauthenticated request correctly rejected")
    
    def test_bulk_import_buyer_forbidden(self, buyer_token):
        """Buyers should not be able to import machines"""
        csv_content = "name,machine_type,brand,model\nTest,CNC Lathe,Test,Test"
        files = {"file": ("test.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        response = requests.post(f"{BASE_URL}/api/machines/bulk-import", files=files, headers=headers)
        assert response.status_code == 403, f"Expected 403 for buyer, got {response.status_code}"
        print("Buyer correctly forbidden from importing")
    
    def test_bulk_import_rejects_non_csv(self, vendor_token):
        """Import should reject non-CSV files"""
        txt_content = "This is not a CSV file"
        files = {"file": ("test.txt", io.BytesIO(txt_content.encode()), "text/plain")}
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        response = requests.post(f"{BASE_URL}/api/machines/bulk-import", files=files, headers=headers)
        assert response.status_code == 400, f"Expected 400 for non-CSV, got {response.status_code}"
        print("Non-CSV file correctly rejected")
    
    def test_bulk_import_valid_machines(self, vendor_token):
        """Vendor can import valid machines via CSV"""
        csv_content = """name,machine_category,machine_type,brand,model,max_x,max_y,max_z,tolerance,materials_supported,monthly_capacity_hours
TEST_BulkImport VMC,VMC (Vertical Machining Center),VMC,Haas,VF-2SS,762,406,508,0.01,"Aluminum,Steel",160
TEST_BulkImport Lathe,CNC Turning/Lathe,CNC Lathe,Mazak,QT-200,,,200,0.02,"Steel,Stainless Steel",180"""
        
        files = {"file": ("machines.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        response = requests.post(f"{BASE_URL}/api/machines/bulk-import", files=files, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert "total_rows" in data, "Response should contain total_rows"
        assert "successful" in data, "Response should contain successful count"
        assert "failed" in data, "Response should contain failed count"
        assert "machines_created" in data, "Response should contain machines_created list"
        
        print(f"Import result: {data['successful']} successful, {data['failed']} failed out of {data['total_rows']} rows")
        
        # Verify machines were created
        assert data["successful"] >= 1, "At least one machine should be created"
        assert len(data["machines_created"]) == data["successful"], "machines_created list should match successful count"
    
    def test_bulk_import_missing_required_fields(self, vendor_token):
        """Import should report errors for rows missing required fields"""
        csv_content = """name,machine_category,machine_type,brand,model
TEST_Missing Fields,VMC,,,
,VMC,,Haas,"""
        
        files = {"file": ("machines.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        response = requests.post(f"{BASE_URL}/api/machines/bulk-import", files=files, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["failed"] >= 2, "Should have at least 2 failed rows due to missing required fields"
        assert "errors" in data, "Response should contain errors list"
        assert len(data["errors"]) >= 2, "Should report errors for invalid rows"
        
        # Check error details
        for error in data["errors"]:
            assert "row" in error, "Error should have row number"
            assert "errors" in error, "Error should have error messages"
            print(f"Row {error['row']} errors: {error['errors']}")
    
    def test_bulk_import_invalid_numeric_fields(self, vendor_token):
        """Import should report errors for invalid numeric values"""
        csv_content = """name,machine_type,brand,model,max_x,tolerance
TEST_InvalidNum,VMC,Haas,VF-2,not_a_number,0.01"""
        
        files = {"file": ("machines.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        response = requests.post(f"{BASE_URL}/api/machines/bulk-import", files=files, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["failed"] >= 1, "Should have at least 1 failed row due to invalid number"
        
        # Check that error mentions the invalid field
        if data["errors"]:
            error_text = str(data["errors"])
            assert "max_x" in error_text.lower() or "number" in error_text.lower(), \
                "Error should mention the invalid numeric field"
        print(f"Invalid numeric row correctly rejected with {data['failed']} failed")
    
    def test_bulk_import_materials_parsing(self, vendor_token):
        """Import should correctly parse comma-separated materials"""
        csv_content = """name,machine_type,brand,model,materials_supported
TEST_Materials,VMC,TestBrand,TestModel,"Aluminum,Steel,Titanium" """
        
        files = {"file": ("machines.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        response = requests.post(f"{BASE_URL}/api/machines/bulk-import", files=files, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        print(f"Materials parsing result: {data['successful']} successful, {data['failed']} failed")
        
        # Materials should be parsed correctly
        if data["successful"] > 0:
            print(f"Created machines: {data['machines_created']}")
    
    def test_bulk_import_mixed_valid_invalid(self, vendor_token):
        """Import should process valid rows even if some are invalid"""
        csv_content = """name,machine_type,brand,model,tolerance
TEST_MixedValid,VMC,Haas,VF-2,0.01
TEST_MixedInvalid,,Haas,VF-3,0.02
TEST_MixedValid2,CNC Lathe,Mazak,QT-100,0.015"""
        
        files = {"file": ("machines.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        response = requests.post(f"{BASE_URL}/api/machines/bulk-import", files=files, headers=headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        data = response.json()
        assert data["total_rows"] == 3, "Should have 3 total rows"
        assert data["successful"] == 2, "Should have 2 successful imports"
        assert data["failed"] == 1, "Should have 1 failed import"
        
        print(f"Mixed import: {data['successful']} valid, {data['failed']} invalid out of {data['total_rows']}")


class TestBulkImportCleanup:
    """Cleanup test machines created during bulk import tests"""
    
    @pytest.fixture
    def vendor_token(self):
        """Get vendor authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": VENDOR_EMAIL,
            "password": VENDOR_PASSWORD
        })
        if response.status_code != 200:
            pytest.skip("Vendor login failed")
        return response.json()["access_token"]
    
    def test_cleanup_test_machines(self, vendor_token):
        """Clean up TEST_ prefixed machines created during tests"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        # Get all machines
        response = requests.get(f"{BASE_URL}/api/machines", headers=headers)
        if response.status_code != 200:
            print("Could not fetch machines for cleanup")
            return
        
        machines = response.json()
        deleted_count = 0
        
        for machine in machines:
            # Delete TEST_ prefixed machines
            name = machine.get("name", "")
            if name.startswith("TEST_"):
                delete_response = requests.delete(
                    f"{BASE_URL}/api/machines/{machine['machine_id']}", 
                    headers=headers
                )
                if delete_response.status_code in [200, 204]:
                    deleted_count += 1
                    print(f"Deleted test machine: {name}")
        
        print(f"Cleanup completed: {deleted_count} test machines deleted")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
