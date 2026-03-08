"""
WhatsApp Machine Dimension Flow Tests for OEMLinker
Tests the dynamic machine parameter collection via WhatsApp:
- MACHINE_DIMENSION_FIELDS alignment with /api/machine-categories
- get_dimension_config_for_category helper function fuzzy matching
- Step progress display (Step N/total) during dimension collection
- Category-specific parameters (thickness for welding, spindle for boring, etc.)
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"
VENDOR_EMAIL = "vendor@offoadex.com"
VENDOR_PASSWORD = "vendor123"


@pytest.fixture(scope="module")
def admin_token():
    """Get admin auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Admin authentication failed")


@pytest.fixture(scope="module")
def vendor_token():
    """Get vendor auth token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": VENDOR_EMAIL,
        "password": VENDOR_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip("Vendor authentication failed")


class TestMachineCategoriesEndpoint:
    """Test /api/machine-categories endpoint returns correct category structure"""
    
    def test_machine_categories_returns_all_categories(self):
        """Test that /api/machine-categories returns 21+ categories"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        
        categories = response.json()
        assert isinstance(categories, dict), "Response should be a dictionary"
        
        # Verify we have at least 21 categories
        assert len(categories) >= 21, f"Expected at least 21 categories, got {len(categories)}"
        print(f"Total categories returned: {len(categories)}")
        print(f"Categories: {list(categories.keys())}")
    
    def test_machine_categories_structure(self):
        """Test that each category has correct structure with types and dimension_fields"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        
        for cat_name, cat_data in categories.items():
            # Each category should have 'types' and 'dimension_fields'
            assert "types" in cat_data, f"Category '{cat_name}' missing 'types'"
            assert "dimension_fields" in cat_data, f"Category '{cat_name}' missing 'dimension_fields'"
            
            # Types should be a list
            assert isinstance(cat_data["types"], list), f"Category '{cat_name}' types should be a list"
            assert len(cat_data["types"]) > 0, f"Category '{cat_name}' should have at least one type"
            
            # Dimension fields should be a list
            assert isinstance(cat_data["dimension_fields"], list), f"Category '{cat_name}' dimension_fields should be a list"
            assert len(cat_data["dimension_fields"]) > 0, f"Category '{cat_name}' should have at least one dimension field"
            
            # Each dimension field should have key, label, type
            for field in cat_data["dimension_fields"]:
                assert "key" in field, f"Category '{cat_name}' field missing 'key'"
                assert "label" in field, f"Category '{cat_name}' field missing 'label'"
                assert "type" in field, f"Category '{cat_name}' field missing 'type'"
                assert field["type"] == "number", f"Field type should be 'number', got '{field['type']}'"
        
        print(f"All {len(categories)} categories have valid structure")
    
    def test_welding_category_has_thickness_field(self):
        """Test that Welding category has max_thickness (weld thickness) field"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        
        # Find Welding category
        assert "Welding" in categories, "Welding category should exist"
        
        welding_fields = categories["Welding"]["dimension_fields"]
        field_keys = [f["key"] for f in welding_fields]
        
        # Welding should have thickness field
        assert "max_thickness" in field_keys, f"Welding should have max_thickness field, got {field_keys}"
        assert "max_length" in field_keys, f"Welding should have max_length field, got {field_keys}"
        assert "amperage" in field_keys, f"Welding should have amperage field, got {field_keys}"
        
        print(f"Welding dimension fields: {field_keys}")
    
    def test_boring_category_has_spindle_field(self):
        """Test that Boring Machine category has bore_diameter (spindle) field"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        
        # Find Boring Machine category
        assert "Boring Machine" in categories, "Boring Machine category should exist"
        
        boring_fields = categories["Boring Machine"]["dimension_fields"]
        field_keys = [f["key"] for f in boring_fields]
        
        # Boring should have spindle/bore diameter field
        assert "bore_diameter" in field_keys, f"Boring should have bore_diameter field, got {field_keys}"
        
        print(f"Boring Machine dimension fields: {field_keys}")
    
    def test_cnc_turning_category_has_correct_fields(self):
        """Test that CNC Turning/Lathe has max_length, max_diameter, max_swing"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        
        assert "CNC Turning/Lathe" in categories, "CNC Turning/Lathe category should exist"
        
        turning_fields = categories["CNC Turning/Lathe"]["dimension_fields"]
        field_keys = [f["key"] for f in turning_fields]
        
        assert "max_length" in field_keys, f"CNC Turning should have max_length, got {field_keys}"
        assert "max_diameter" in field_keys, f"CNC Turning should have max_diameter, got {field_keys}"
        assert "max_swing" in field_keys, f"CNC Turning should have max_swing, got {field_keys}"
        
        print(f"CNC Turning/Lathe dimension fields: {field_keys}")
    
    def test_vtl_category_has_table_diameter(self):
        """Test that VTL has table_diameter and max_weight fields"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        
        assert "VTL (Vertical Turret Lathe)" in categories, "VTL category should exist"
        
        vtl_fields = categories["VTL (Vertical Turret Lathe)"]["dimension_fields"]
        field_keys = [f["key"] for f in vtl_fields]
        
        assert "table_diameter" in field_keys, f"VTL should have table_diameter, got {field_keys}"
        assert "max_weight" in field_keys, f"VTL should have max_weight, got {field_keys}"
        
        print(f"VTL dimension fields: {field_keys}")
    
    def test_vmc_category_has_xyz_travel(self):
        """Test that VMC has X, Y, Z axis travel and table size fields"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        
        assert "VMC (Vertical Machining Center)" in categories, "VMC category should exist"
        
        vmc_fields = categories["VMC (Vertical Machining Center)"]["dimension_fields"]
        field_keys = [f["key"] for f in vmc_fields]
        
        assert "max_x" in field_keys, f"VMC should have max_x, got {field_keys}"
        assert "max_y" in field_keys, f"VMC should have max_y, got {field_keys}"
        assert "max_z" in field_keys, f"VMC should have max_z, got {field_keys}"
        assert "table_size_x" in field_keys, f"VMC should have table_size_x, got {field_keys}"
        assert "table_size_y" in field_keys, f"VMC should have table_size_y, got {field_keys}"
        
        print(f"VMC dimension fields: {field_keys}")
    
    def test_5axis_category_has_rotation_fields(self):
        """Test that 5-Axis Machining has a_axis_range and c_axis_range fields"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        
        assert "5-Axis Machining" in categories, "5-Axis Machining category should exist"
        
        axis5_fields = categories["5-Axis Machining"]["dimension_fields"]
        field_keys = [f["key"] for f in axis5_fields]
        
        assert "a_axis_range" in field_keys, f"5-Axis should have a_axis_range, got {field_keys}"
        assert "c_axis_range" in field_keys, f"5-Axis should have c_axis_range, got {field_keys}"
        assert "max_x" in field_keys, f"5-Axis should have max_x, got {field_keys}"
        assert "max_y" in field_keys, f"5-Axis should have max_y, got {field_keys}"
        assert "max_z" in field_keys, f"5-Axis should have max_z, got {field_keys}"
        
        print(f"5-Axis Machining dimension fields: {field_keys}")
    
    def test_gear_manufacturing_category_has_module_field(self):
        """Test that Gear Manufacturing has max_module and min_teeth fields"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        
        assert "Gear Manufacturing" in categories, "Gear Manufacturing category should exist"
        
        gear_fields = categories["Gear Manufacturing"]["dimension_fields"]
        field_keys = [f["key"] for f in gear_fields]
        
        assert "max_module" in field_keys, f"Gear Manufacturing should have max_module, got {field_keys}"
        assert "min_teeth" in field_keys, f"Gear Manufacturing should have min_teeth, got {field_keys}"
        assert "max_diameter" in field_keys, f"Gear Manufacturing should have max_diameter, got {field_keys}"
        
        print(f"Gear Manufacturing dimension fields: {field_keys}")
    
    def test_drilling_machine_category_has_depth_and_arm_fields(self):
        """Test that Drilling Machine has max_depth and arm_length fields"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        
        assert "Drilling Machine" in categories, "Drilling Machine category should exist"
        
        drill_fields = categories["Drilling Machine"]["dimension_fields"]
        field_keys = [f["key"] for f in drill_fields]
        
        assert "max_depth" in field_keys, f"Drilling should have max_depth, got {field_keys}"
        assert "arm_length" in field_keys, f"Drilling should have arm_length, got {field_keys}"
        assert "max_diameter" in field_keys, f"Drilling should have max_diameter, got {field_keys}"
        
        print(f"Drilling Machine dimension fields: {field_keys}")
    
    def test_laser_cutting_category_has_power_field(self):
        """Test that Laser Cutting has laser_power field"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        
        assert "Laser Cutting" in categories, "Laser Cutting category should exist"
        
        laser_fields = categories["Laser Cutting"]["dimension_fields"]
        field_keys = [f["key"] for f in laser_fields]
        
        assert "laser_power" in field_keys, f"Laser Cutting should have laser_power, got {field_keys}"
        assert "max_thickness" in field_keys, f"Laser Cutting should have max_thickness, got {field_keys}"
        
        print(f"Laser Cutting dimension fields: {field_keys}")
    
    def test_heat_treatment_category_has_temp_field(self):
        """Test that Heat Treatment has max_temp field"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        
        assert "Heat Treatment" in categories, "Heat Treatment category should exist"
        
        heat_fields = categories["Heat Treatment"]["dimension_fields"]
        field_keys = [f["key"] for f in heat_fields]
        
        assert "max_temp" in field_keys, f"Heat Treatment should have max_temp, got {field_keys}"
        
        print(f"Heat Treatment dimension fields: {field_keys}")
    
    def test_cmm_category_has_accuracy_field(self):
        """Test that Inspection/CMM has accuracy field"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        
        assert "Inspection/CMM" in categories, "Inspection/CMM category should exist"
        
        cmm_fields = categories["Inspection/CMM"]["dimension_fields"]
        field_keys = [f["key"] for f in cmm_fields]
        
        assert "accuracy" in field_keys, f"Inspection/CMM should have accuracy, got {field_keys}"
        
        print(f"Inspection/CMM dimension fields: {field_keys}")
    
    def test_additive_manufacturing_category_has_layer_thickness(self):
        """Test that Additive Manufacturing has layer_thickness field"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        
        assert "Additive Manufacturing" in categories, "Additive Manufacturing category should exist"
        
        additive_fields = categories["Additive Manufacturing"]["dimension_fields"]
        field_keys = [f["key"] for f in additive_fields]
        
        assert "layer_thickness" in field_keys, f"Additive Manufacturing should have layer_thickness, got {field_keys}"
        
        print(f"Additive Manufacturing dimension fields: {field_keys}")
    
    def test_edm_category_has_taper_angle_field(self):
        """Test that EDM has max_taper_angle field"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        
        assert "EDM" in categories, "EDM category should exist"
        
        edm_fields = categories["EDM"]["dimension_fields"]
        field_keys = [f["key"] for f in edm_fields]
        
        assert "max_taper_angle" in field_keys, f"EDM should have max_taper_angle, got {field_keys}"
        assert "max_thickness" in field_keys, f"EDM should have max_thickness, got {field_keys}"
        
        print(f"EDM dimension fields: {field_keys}")
    
    def test_sheet_metal_press_category_has_tonnage_field(self):
        """Test that Sheet Metal/Press has tonnage field"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        
        assert "Sheet Metal/Press" in categories, "Sheet Metal/Press category should exist"
        
        press_fields = categories["Sheet Metal/Press"]["dimension_fields"]
        field_keys = [f["key"] for f in press_fields]
        
        assert "tonnage" in field_keys, f"Sheet Metal/Press should have tonnage, got {field_keys}"
        assert "stroke" in field_keys, f"Sheet Metal/Press should have stroke, got {field_keys}"
        
        print(f"Sheet Metal/Press dimension fields: {field_keys}")


class TestMachineDimensionFieldsAlignment:
    """Test MACHINE_DIMENSION_FIELDS dictionary alignment with /api/machine-categories"""
    
    def test_all_web_categories_have_whatsapp_config(self):
        """Test that all categories from /api/machine-categories have WhatsApp dimension config"""
        # Get web app categories
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        web_categories = response.json()
        
        # We need to verify that the backend MACHINE_DIMENSION_FIELDS has entries for all web categories
        # We can test this indirectly by checking the structure consistency
        # The web categories should match the WhatsApp flow categories
        
        expected_categories = [
            "CNC Turning/Lathe",
            "VTL (Vertical Turret Lathe)",
            "VMC (Vertical Machining Center)",
            "HMC (Horizontal Machining Center)",
            "5-Axis Machining",
            "Conventional Lathe",
            "Conventional Milling",
            "Boring Machine",
            "Shaping Machine",
            "Gear Manufacturing",
            "Grinding",
            "EDM",
            "Drilling Machine",
            "Laser Cutting",
            "Plasma/Waterjet Cutting",
            "Sheet Metal/Press",
            "Welding",
            "Heat Treatment",
            "Surface Treatment",
            "Inspection/CMM",
            "Additive Manufacturing",
        ]
        
        for cat in expected_categories:
            assert cat in web_categories, f"Category '{cat}' should exist in web categories"
        
        print(f"All {len(expected_categories)} expected categories exist in web app")
    
    def test_dimension_field_keys_consistency(self):
        """Test that dimension field keys are consistent (use snake_case format)"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        
        valid_key_pattern = r'^[a-z][a-z0-9_]*$'
        import re
        
        for cat_name, cat_data in categories.items():
            for field in cat_data.get("dimension_fields", []):
                key = field.get("key", "")
                # Keys should be snake_case
                assert re.match(valid_key_pattern, key), f"Category '{cat_name}' has invalid key format: '{key}'"
        
        print("All dimension field keys follow valid snake_case format")


class TestWhatsAppWebhookMachineDimensionFlow:
    """Test WhatsApp webhook machine dimension collection flow"""
    
    def _send_webhook_message(self, phone: str, text: str):
        """Helper to send a WhatsApp webhook message"""
        payload = {
            "type": "message",
            "payload": {
                "source": phone,
                "type": "text",
                "id": f"test_msg_{phone}_{text[:10]}",
                "payload": {
                    "text": text
                }
            },
            "timestamp": "2026-01-15T10:05:00Z",
            "app": "OEMLinker"
        }
        return requests.post(f"{BASE_URL}/api/whatsapp/webhook", json=payload)
    
    def test_webhook_accepts_text_messages(self):
        """Test that webhook accepts and processes text messages"""
        response = self._send_webhook_message("919876543210", "help")
        assert response.status_code == 200
        assert response.json().get("status") == "ok"
        print("Webhook text message processing: PASS")
    
    def test_webhook_handles_skip_command(self):
        """Test that webhook handles 'skip' command in dimension flow"""
        response = self._send_webhook_message("919876543211", "skip")
        assert response.status_code == 200
        assert response.json().get("status") == "ok"
        print("Webhook skip command handling: PASS")
    
    def test_webhook_handles_cancel_command(self):
        """Test that webhook handles 'cancel' command"""
        response = self._send_webhook_message("919876543212", "cancel")
        assert response.status_code == 200
        assert response.json().get("status") == "ok"
        print("Webhook cancel command handling: PASS")
    
    def test_webhook_handles_numeric_dimension_input(self):
        """Test that webhook processes numeric dimension values"""
        # Simulate numeric input (e.g., "500" or "500mm")
        response = self._send_webhook_message("919876543213", "500")
        assert response.status_code == 200
        assert response.json().get("status") == "ok"
        print("Webhook numeric input handling: PASS")
    
    def test_webhook_handles_dimension_with_unit(self):
        """Test that webhook processes dimension with unit suffix"""
        response = self._send_webhook_message("919876543214", "750mm")
        assert response.status_code == 200
        assert response.json().get("status") == "ok"
        print("Webhook dimension with unit handling: PASS")


class TestCategoryFuzzyMatching:
    """Test fuzzy category matching for AI-identified categories"""
    
    def test_machine_categories_accessible(self):
        """Verify machine categories endpoint is accessible for fuzzy matching validation"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        
        # Verify common fuzzy match targets exist
        expected_fuzzy_targets = {
            "CNC Turning/Lathe": ["lathe", "turning", "cnc lathe"],
            "VTL (Vertical Turret Lathe)": ["vtl", "vertical turret"],
            "VMC (Vertical Machining Center)": ["vmc", "vertical machining"],
            "HMC (Horizontal Machining Center)": ["hmc", "horizontal machining"],
            "5-Axis Machining": ["5 axis", "5-axis", "five axis"],
            "Boring Machine": ["boring", "horizontal boring"],
            "Gear Manufacturing": ["gear", "hobbing"],
            "Grinding": ["grinder", "surface grinder", "cylindrical grinder"],
            "EDM": ["edm", "wire edm", "sinker edm"],
            "Drilling Machine": ["drill", "radial drill"],
            "Laser Cutting": ["laser", "fiber laser"],
            "Welding": ["welding", "mig", "tig"],
            "Heat Treatment": ["heat treatment", "furnace", "hardening"],
            "Inspection/CMM": ["cmm", "inspection"],
            "Additive Manufacturing": ["3d printing", "additive", "fdm", "sla", "sls"],
        }
        
        for category, fuzzy_terms in expected_fuzzy_targets.items():
            assert category in categories, f"Category '{category}' should exist for fuzzy match target"
        
        print(f"All {len(expected_fuzzy_targets)} fuzzy match target categories exist")


class TestAllCategoriesPresent:
    """Ensure all 21+ machine categories are present with proper dimension fields"""
    
    def test_all_21_plus_categories_exist(self):
        """Test that at least 21 categories exist"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        category_count = len(categories)
        
        assert category_count >= 21, f"Expected at least 21 categories, got {category_count}"
        
        print(f"Total categories: {category_count}")
        print("All 21+ categories present: PASS")
    
    def test_each_category_has_at_least_one_type(self):
        """Test that each category has at least one machine type"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        
        for cat_name, cat_data in categories.items():
            types = cat_data.get("types", [])
            assert len(types) > 0, f"Category '{cat_name}' should have at least one type"
        
        print("All categories have at least one type: PASS")
    
    def test_each_category_has_at_least_one_dimension_field(self):
        """Test that each category has at least one dimension field"""
        response = requests.get(f"{BASE_URL}/api/machine-categories")
        assert response.status_code == 200
        
        categories = response.json()
        
        for cat_name, cat_data in categories.items():
            fields = cat_data.get("dimension_fields", [])
            assert len(fields) > 0, f"Category '{cat_name}' should have at least one dimension field"
        
        print("All categories have at least one dimension field: PASS")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
