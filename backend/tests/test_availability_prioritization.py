"""
Test availability prioritization for urgent RFQs
Tests:
1. Urgent RFQ matching returns availability data in vendor response
2. Urgent RFQ matching returns urgency_applied: true, availability_prioritized: true
3. Vendors with available machines get higher scores for urgent RFQs
4. Machine details include availability status indicator
"""
import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')

# Test credentials
BUYER_EMAIL = "buyer@offoadex.com"
BUYER_PASSWORD = "buyer123"
VENDOR_EMAIL = "vendor@offoadex.com"
VENDOR_PASSWORD = "vendor123"

@pytest.fixture(scope="module")
def buyer_token():
    """Get buyer authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": BUYER_EMAIL,
        "password": BUYER_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Buyer authentication failed: {response.status_code}")

@pytest.fixture(scope="module")
def vendor_token():
    """Get vendor authentication token"""
    response = requests.post(f"{BASE_URL}/api/auth/login", json={
        "email": VENDOR_EMAIL,
        "password": VENDOR_PASSWORD
    })
    if response.status_code == 200:
        return response.json().get("access_token")
    pytest.skip(f"Vendor authentication failed: {response.status_code}")


class TestUrgentRFQAvailabilityPrioritization:
    """Tests for urgent RFQ availability prioritization feature"""
    
    def test_get_urgent_rfq_details(self, buyer_token):
        """
        Test fetching the urgent RFQ rfq_ff88d4dd6ba0 to verify it exists
        """
        headers = {"Authorization": f"Bearer {buyer_token}"}
        response = requests.get(f"{BASE_URL}/api/rfqs/rfq_ff88d4dd6ba0", headers=headers)
        
        assert response.status_code == 200, f"Failed to get RFQ: {response.status_code} - {response.text}"
        
        data = response.json()
        assert data["rfq_id"] == "rfq_ff88d4dd6ba0"
        assert data["urgency"] == "urgent", f"Expected urgency='urgent', got '{data.get('urgency')}'"
        print(f"RFQ found: {data['title']}, urgency: {data['urgency']}, status: {data['status']}")

    def test_urgent_rfq_matched_vendors_have_availability_data(self, buyer_token):
        """
        Test that matched vendors for urgent RFQ contain availability fields:
        - has_available_machine
        - availability_score
        - available_machine_count
        """
        headers = {"Authorization": f"Bearer {buyer_token}"}
        response = requests.get(f"{BASE_URL}/api/rfqs/rfq_ff88d4dd6ba0", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        matched_vendors = data.get("matched_vendors", [])
        assert len(matched_vendors) > 0, "No matched vendors found for urgent RFQ"
        
        # Check first vendor for availability fields
        first_vendor = matched_vendors[0]
        
        # Verify availability data fields exist
        assert "has_available_machine" in first_vendor, "Missing 'has_available_machine' field"
        assert "availability_score" in first_vendor, "Missing 'availability_score' field"
        assert "available_machine_count" in first_vendor, "Missing 'available_machine_count' field"
        assert "total_matching_machines" in first_vendor, "Missing 'total_matching_machines' field"
        
        print(f"First vendor availability data:")
        print(f"  has_available_machine: {first_vendor.get('has_available_machine')}")
        print(f"  availability_score: {first_vendor.get('availability_score')}")
        print(f"  available_machine_count: {first_vendor.get('available_machine_count')}")
        print(f"  total_matching_machines: {first_vendor.get('total_matching_machines')}")

    def test_trigger_matching_returns_urgency_flags(self, buyer_token):
        """
        Test triggering vendor matching for an urgent RFQ returns:
        - urgency_applied: true
        - availability_prioritized: true
        """
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Trigger matching again
        response = requests.post(f"{BASE_URL}/api/rfqs/rfq_ff88d4dd6ba0/match", headers=headers)
        
        assert response.status_code == 200, f"Failed to trigger matching: {response.status_code} - {response.text}"
        
        data = response.json()
        
        # Check for urgency flags in response
        assert data.get("urgency_applied") == True, f"Expected urgency_applied=True, got {data.get('urgency_applied')}"
        assert data.get("availability_prioritized") == True, f"Expected availability_prioritized=True, got {data.get('availability_prioritized')}"
        assert data.get("rfq_urgency") == "urgent", f"Expected rfq_urgency='urgent', got {data.get('rfq_urgency')}"
        
        print(f"Matching response urgency flags:")
        print(f"  rfq_urgency: {data.get('rfq_urgency')}")
        print(f"  urgency_applied: {data.get('urgency_applied')}")
        print(f"  availability_prioritized: {data.get('availability_prioritized')}")
        print(f"  total_matches: {data.get('total_matches')}")

    def test_machine_details_include_availability_status(self, buyer_token):
        """
        Test that matched vendors' machine_details include availability status:
        - availability_status (available, engaged, maintenance, offline)
        - is_available (boolean)
        """
        headers = {"Authorization": f"Bearer {buyer_token}"}
        response = requests.get(f"{BASE_URL}/api/rfqs/rfq_ff88d4dd6ba0", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        matched_vendors = data.get("matched_vendors", [])
        assert len(matched_vendors) > 0, "No matched vendors found"
        
        # Find a vendor with machine_details
        found_machine_details = False
        for vendor in matched_vendors:
            machine_details = vendor.get("machine_details", [])
            if machine_details:
                found_machine_details = True
                first_machine = machine_details[0]
                
                # Verify machine availability fields
                assert "availability_status" in first_machine, "Missing 'availability_status' in machine_details"
                assert "is_available" in first_machine, "Missing 'is_available' in machine_details"
                
                print(f"Vendor {vendor.get('company_name')} machine details:")
                for machine in machine_details[:3]:  # First 3 machines
                    print(f"  Machine: {machine.get('name')}")
                    print(f"    availability_status: {machine.get('availability_status')}")
                    print(f"    is_available: {machine.get('is_available')}")
                break
        
        assert found_machine_details, "No vendor found with machine_details"

    def test_vendors_with_available_machines_get_higher_scores(self, buyer_token):
        """
        Test that vendors with available machines get bonus scoring for urgent RFQs.
        Check that availability_score > 0 for vendors with available machines.
        """
        headers = {"Authorization": f"Bearer {buyer_token}"}
        response = requests.get(f"{BASE_URL}/api/rfqs/rfq_ff88d4dd6ba0", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        matched_vendors = data.get("matched_vendors", [])
        assert len(matched_vendors) > 0, "No matched vendors found"
        
        print("\nVendor availability scoring:")
        for vendor in matched_vendors:
            has_available = vendor.get("has_available_machine", False)
            availability_score = vendor.get("availability_score", 0)
            suitability_score = vendor.get("suitability_score", 0)
            available_count = vendor.get("available_machine_count", 0)
            
            print(f"  {vendor.get('company_name')}:")
            print(f"    has_available_machine: {has_available}")
            print(f"    availability_score: {availability_score}")
            print(f"    suitability_score: {suitability_score}")
            print(f"    available_machine_count: {available_count}")
            
            # For urgent RFQ, vendors with available machines should have availability_score > 0
            if has_available:
                assert availability_score > 0, f"Vendor with available machines should have availability_score > 0, got {availability_score}"

    def test_create_urgent_rfq_and_verify_matching(self, buyer_token):
        """
        Test creating a new urgent RFQ and verifying matching applies availability prioritization
        """
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Create new urgent RFQ
        rfq_data = {
            "title": "TEST_Urgent_Availability_Test_Part",
            "description": "Test part for availability prioritization testing",
            "material_type": "Steel",
            "quantity": 5,
            "tolerance": 0.1,
            "urgency": "urgent",
            "deadline": "2026-01-25"
        }
        
        response = requests.post(f"{BASE_URL}/api/rfqs", headers=headers, json=rfq_data)
        assert response.status_code == 200, f"Failed to create RFQ: {response.status_code} - {response.text}"
        
        new_rfq = response.json()
        rfq_id = new_rfq["rfq_id"]
        print(f"Created urgent RFQ: {rfq_id}")
        
        # Trigger matching
        response = requests.post(f"{BASE_URL}/api/rfqs/{rfq_id}/match", headers=headers)
        assert response.status_code == 200, f"Failed to trigger matching: {response.status_code} - {response.text}"
        
        match_result = response.json()
        
        # Verify urgency flags
        assert match_result.get("urgency_applied") == True, "urgency_applied should be True"
        assert match_result.get("availability_prioritized") == True, "availability_prioritized should be True"
        
        # Check matched vendors have availability data
        matched_vendors = match_result.get("matched_vendors", [])
        if matched_vendors:
            first_vendor = matched_vendors[0]
            assert "has_available_machine" in first_vendor, "Missing availability data"
            assert "availability_score" in first_vendor, "Missing availability_score"
            print(f"First matched vendor: {first_vendor.get('company_name')}")
            print(f"  availability_score: {first_vendor.get('availability_score')}")
            print(f"  has_available_machine: {first_vendor.get('has_available_machine')}")
        
        print(f"PASS: Urgent RFQ matching correctly applies availability prioritization")
        
        # Cleanup - delete test RFQ (optional)
        # requests.delete(f"{BASE_URL}/api/rfqs/{rfq_id}", headers=headers)


class TestNormalRFQNoAvailabilityBonus:
    """Test that normal priority RFQs don't get availability bonus"""
    
    def test_normal_rfq_no_availability_prioritization(self, buyer_token):
        """
        Test that normal priority RFQs return urgency_applied: false
        """
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Create normal priority RFQ
        rfq_data = {
            "title": "TEST_Normal_Priority_Part",
            "description": "Test part for normal priority",
            "material_type": "Steel",
            "quantity": 10,
            "tolerance": 0.1,
            "urgency": "normal"
        }
        
        response = requests.post(f"{BASE_URL}/api/rfqs", headers=headers, json=rfq_data)
        assert response.status_code == 200, f"Failed to create RFQ: {response.status_code}"
        
        new_rfq = response.json()
        rfq_id = new_rfq["rfq_id"]
        
        # Trigger matching
        response = requests.post(f"{BASE_URL}/api/rfqs/{rfq_id}/match", headers=headers)
        assert response.status_code == 200
        
        match_result = response.json()
        
        # Normal RFQ should not have urgency flags
        assert match_result.get("urgency_applied") == False, f"Normal RFQ should have urgency_applied=False, got {match_result.get('urgency_applied')}"
        assert match_result.get("availability_prioritized") == False, f"Normal RFQ should have availability_prioritized=False"
        
        print(f"PASS: Normal RFQ correctly does NOT apply availability prioritization")


class TestHighPriorityRFQ:
    """Test high priority RFQs get partial availability bonus"""
    
    def test_high_priority_rfq_partial_availability_bonus(self, buyer_token):
        """
        Test that high priority RFQs get partial availability bonus (but less than urgent)
        """
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Create high priority RFQ
        rfq_data = {
            "title": "TEST_High_Priority_Part",
            "description": "Test part for high priority",
            "material_type": "Steel",
            "quantity": 10,
            "tolerance": 0.1,
            "urgency": "high"
        }
        
        response = requests.post(f"{BASE_URL}/api/rfqs", headers=headers, json=rfq_data)
        assert response.status_code == 200
        
        new_rfq = response.json()
        rfq_id = new_rfq["rfq_id"]
        
        # Trigger matching
        response = requests.post(f"{BASE_URL}/api/rfqs/{rfq_id}/match", headers=headers)
        assert response.status_code == 200
        
        match_result = response.json()
        
        # High priority RFQ should have urgency flags
        assert match_result.get("urgency_applied") == True, f"High priority RFQ should have urgency_applied=True"
        assert match_result.get("availability_prioritized") == True, f"High priority RFQ should have availability_prioritized=True"
        assert match_result.get("rfq_urgency") == "high"
        
        print(f"PASS: High priority RFQ correctly applies availability prioritization")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
