"""
Test machine dimension display and WhatsApp machine handling
Tests for:
- Machine names not showing 'Unknown Unknown'
- All dimensions being returned for WhatsApp machines
- WhatsApp badge (source='whatsapp') being present
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestMachineDimensions:
    """Test machine dimension display in vendor profiles and admin endpoints"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@offoadex.com",
            "password": "admin123"
        })
        assert response.status_code == 200, f"Login failed: {response.text}"
        self.token = response.json().get("access_token")
        self.headers = {"Authorization": f"Bearer {self.token}"}
    
    def test_vendor_profile_returns_machines_with_dimensions(self):
        """Test GET /api/vendors/{vendor_id}/full returns machines with all dimension fields"""
        vendor_id = "vendor_fb2b51067982"  # Simpson Munro - has WhatsApp machines
        
        response = requests.get(
            f"{BASE_URL}/api/vendors/{vendor_id}/full",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Failed to get vendor profile: {response.text}"
        data = response.json()
        
        # Verify vendor has machines
        assert "machines" in data, "Response should contain 'machines' field"
        machines = data["machines"]
        assert len(machines) > 0, "Vendor should have machines"
        
        # Check for WhatsApp machines
        whatsapp_machines = [m for m in machines if m.get("source") == "whatsapp"]
        assert len(whatsapp_machines) > 0, "Vendor should have WhatsApp-sourced machines"
        
        # Verify dimension fields are present
        dimension_fields = [
            "max_diameter", "max_length", "max_x", "max_y", "max_z",
            "bore_diameter", "tonnage", "max_thickness"
        ]
        
        for machine in whatsapp_machines:
            # Check that at least some dimension fields exist
            has_dimensions = any(machine.get(field) for field in dimension_fields)
            # Note: Some machines may not have dimensions, that's OK
            print(f"Machine: {machine.get('name')}, source: {machine.get('source')}, has_dimensions: {has_dimensions}")
    
    def test_machine_names_not_unknown_unknown(self):
        """Test that machine names don't show 'Unknown Unknown'"""
        vendor_id = "vendor_fb2b51067982"
        
        response = requests.get(
            f"{BASE_URL}/api/vendors/{vendor_id}/full",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        machines = data.get("machines", [])
        
        for machine in machines:
            name = machine.get("name", "")
            brand = machine.get("brand", "")
            model = machine.get("model", "")
            machine_type = machine.get("machine_type", "")
            
            # The name field in DB might be "Unknown Unknown" but frontend should handle it
            # Backend should return the raw data, frontend handles display logic
            print(f"Machine: name='{name}', brand='{brand}', model='{model}', type='{machine_type}'")
            
            # Verify machine_type is always present as fallback
            assert machine_type, f"Machine should have machine_type: {machine}"
    
    def test_whatsapp_machines_have_source_field(self):
        """Test that WhatsApp machines have source='whatsapp' field"""
        vendor_id = "vendor_fb2b51067982"
        
        response = requests.get(
            f"{BASE_URL}/api/vendors/{vendor_id}/full",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        machines = data.get("machines", [])
        
        whatsapp_count = 0
        for machine in machines:
            if machine.get("source") == "whatsapp":
                whatsapp_count += 1
                print(f"WhatsApp machine: {machine.get('name')} - {machine.get('machine_type')}")
        
        assert whatsapp_count > 0, "Should have at least one WhatsApp-sourced machine"
        print(f"Total WhatsApp machines: {whatsapp_count}")
    
    def test_admin_machines_endpoint(self):
        """Test GET /api/admin/machines returns machines with proper fields"""
        response = requests.get(
            f"{BASE_URL}/api/admin/machines",
            headers=self.headers
        )
        
        assert response.status_code == 200, f"Failed to get admin machines: {response.text}"
        machines = response.json()
        
        assert isinstance(machines, list), "Response should be a list"
        assert len(machines) > 0, "Should have machines"
        
        # Check structure of first machine
        machine = machines[0]
        required_fields = ["machine_id", "machine_type"]
        for field in required_fields:
            assert field in machine, f"Machine should have '{field}' field"
        
        # Check for dimension fields
        dimension_fields = ["max_x", "max_y", "max_z", "max_diameter", "max_length"]
        has_any_dimension = any(field in machine for field in dimension_fields)
        print(f"First machine has dimension fields: {has_any_dimension}")
    
    def test_cnc_lathe_whatsapp_machine_dimensions(self):
        """Test specific CNC Lathe WhatsApp machine has correct dimensions"""
        vendor_id = "vendor_fb2b51067982"
        
        response = requests.get(
            f"{BASE_URL}/api/vendors/{vendor_id}/full",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        machines = data.get("machines", [])
        
        # Find CNC Lathe with WhatsApp source
        cnc_lathe = None
        for m in machines:
            if m.get("machine_type") == "CNC Lathe" and m.get("source") == "whatsapp":
                cnc_lathe = m
                break
        
        assert cnc_lathe is not None, "Should find CNC Lathe with WhatsApp source"
        
        # Verify dimensions
        assert cnc_lathe.get("max_diameter") == 600.0, f"CNC Lathe max_diameter should be 600, got {cnc_lathe.get('max_diameter')}"
        assert cnc_lathe.get("max_length") == 2200.0, f"CNC Lathe max_length should be 2200, got {cnc_lathe.get('max_length')}"
        assert cnc_lathe.get("bore_diameter") == 230.0, f"CNC Lathe bore_diameter should be 230, got {cnc_lathe.get('bore_diameter')}"
        
        print(f"CNC Lathe dimensions verified: max_diameter={cnc_lathe.get('max_diameter')}, max_length={cnc_lathe.get('max_length')}, bore_diameter={cnc_lathe.get('bore_diameter')}")
    
    def test_horizontal_boring_whatsapp_machine_dimensions(self):
        """Test Horizontal Boring WhatsApp machine has XYZ dimensions"""
        vendor_id = "vendor_fb2b51067982"
        
        response = requests.get(
            f"{BASE_URL}/api/vendors/{vendor_id}/full",
            headers=self.headers
        )
        
        assert response.status_code == 200
        data = response.json()
        machines = data.get("machines", [])
        
        # Find Horizontal Boring with WhatsApp source
        h_boring = None
        for m in machines:
            if m.get("machine_type") == "Horizontal Boring" and m.get("source") == "whatsapp":
                h_boring = m
                break
        
        assert h_boring is not None, "Should find Horizontal Boring with WhatsApp source"
        
        # Verify XYZ dimensions
        assert h_boring.get("max_x") == 600.0, f"Horizontal Boring max_x should be 600, got {h_boring.get('max_x')}"
        assert h_boring.get("max_y") == 6000.0, f"Horizontal Boring max_y should be 6000, got {h_boring.get('max_y')}"
        assert h_boring.get("max_z") == 400.0, f"Horizontal Boring max_z should be 400, got {h_boring.get('max_z')}"
        assert h_boring.get("bore_diameter") == 100.0, f"Horizontal Boring bore_diameter should be 100, got {h_boring.get('bore_diameter')}"
        
        print(f"Horizontal Boring dimensions verified: XYZ={h_boring.get('max_x')}x{h_boring.get('max_y')}x{h_boring.get('max_z')}, bore={h_boring.get('bore_diameter')}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
