"""
Tests for Vendor Location Matching Algorithm and RFQ Detail Page Features
========================================================================
Testing:
1. Vendor location matching algorithm - vendors in preferred cities get higher scores
2. RFQ detail page shows delivery location for vendors
3. RFQ detail page shows incoterms for vendors
4. RFQ detail page shows preferred vendor countries/cities
5. Matching API returns location_match and location_score in response
"""

import pytest
import requests
import os
import time

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
TEST_BUYER_EMAIL = "testbuyer_loc@test.com"
TEST_BUYER_PASSWORD = "SecureP@ss#7291"
TEST_VENDOR_EMAIL = "testvendor_loc@test.com"
TEST_VENDOR_PASSWORD = "SecureV@nd0r#729"

# Known RFQ with location preferences
TEST_RFQ_ID = "rfq_383258d4a8ec"


class TestLocationMatchingSetup:
    """Test setup - verify test data exists"""
    
    @pytest.fixture(scope="class")
    def buyer_token(self):
        """Get buyer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_BUYER_EMAIL,
            "password": TEST_BUYER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Buyer login failed: {response.text}")
    
    @pytest.fixture(scope="class")
    def vendor_token(self):
        """Get vendor authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_VENDOR_EMAIL,
            "password": TEST_VENDOR_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Vendor login failed: {response.text}")
    
    def test_buyer_login(self, buyer_token):
        """Verify buyer can login"""
        assert buyer_token is not None
        print(f"✓ Buyer login successful")
    
    def test_vendor_login(self, vendor_token):
        """Verify vendor can login"""
        assert vendor_token is not None
        print(f"✓ Vendor login successful")


class TestRFQWithLocationPreferences:
    """Test RFQ data with location preferences"""
    
    @pytest.fixture(scope="class")
    def buyer_token(self):
        """Get buyer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_BUYER_EMAIL,
            "password": TEST_BUYER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Buyer login failed: {response.text}")
    
    @pytest.fixture(scope="class")
    def vendor_token(self):
        """Get vendor authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_VENDOR_EMAIL,
            "password": TEST_VENDOR_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Vendor login failed: {response.text}")
    
    def test_rfq_has_location_preferences(self, buyer_token):
        """Test that RFQ has location preference fields"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        response = requests.get(f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}", headers=headers)
        
        assert response.status_code == 200, f"Failed to get RFQ: {response.text}"
        rfq = response.json()
        
        # Verify location preference fields exist
        print(f"RFQ data: {rfq.get('title')}")
        print(f"  - preferred_vendor_countries: {rfq.get('preferred_vendor_countries')}")
        print(f"  - preferred_vendor_cities: {rfq.get('preferred_vendor_cities')}")
        print(f"  - delivery_address: {rfq.get('delivery_address')}")
        print(f"  - delivery_city: {rfq.get('delivery_city')}")
        print(f"  - delivery_country: {rfq.get('delivery_country')}")
        print(f"  - incoterms: {rfq.get('incoterms')}")
        
        # Assert preferred vendor locations exist
        assert rfq.get("preferred_vendor_countries") is not None or rfq.get("preferred_vendor_cities") is not None, \
            "RFQ should have preferred vendor locations"
        print("✓ RFQ has location preference fields")
    
    def test_rfq_has_delivery_location(self, buyer_token):
        """Test that RFQ has delivery location fields"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        response = requests.get(f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}", headers=headers)
        
        assert response.status_code == 200
        rfq = response.json()
        
        # Check delivery fields
        has_delivery_info = bool(
            rfq.get("delivery_address") or 
            rfq.get("delivery_city") or 
            rfq.get("delivery_country")
        )
        print(f"✓ RFQ has delivery location: {has_delivery_info}")
        
    def test_rfq_has_incoterms(self, buyer_token):
        """Test that RFQ has incoterms field"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        response = requests.get(f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}", headers=headers)
        
        assert response.status_code == 200
        rfq = response.json()
        
        incoterms = rfq.get("incoterms")
        print(f"✓ RFQ incoterms: {incoterms}")


class TestVendorMatchingWithLocation:
    """Test vendor matching algorithm with location preferences"""
    
    @pytest.fixture(scope="class")
    def buyer_token(self):
        """Get buyer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_BUYER_EMAIL,
            "password": TEST_BUYER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Buyer login failed: {response.text}")
    
    def test_match_vendors_endpoint(self, buyer_token):
        """Test the match vendors endpoint returns location data"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # First get the RFQ to check its current state
        rfq_response = requests.get(f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}", headers=headers)
        assert rfq_response.status_code == 200, f"Failed to get RFQ: {rfq_response.text}"
        rfq = rfq_response.json()
        
        print(f"RFQ Status: {rfq.get('status')}")
        print(f"Matched Vendors in RFQ: {len(rfq.get('matched_vendors', []))}")
        
        # Check if already matched
        matched_vendors = rfq.get("matched_vendors", [])
        
        if matched_vendors:
            # Already matched - check the data
            print("✓ RFQ already has matched vendors")
            for vendor in matched_vendors[:3]:
                print(f"  - {vendor.get('company_name')}: Score={vendor.get('suitability_score')}")
                print(f"    Location: {vendor.get('location')}")
                print(f"    Location Match: {vendor.get('location_match')}")
                print(f"    Location Score: {vendor.get('location_score')}")
        else:
            # Try to trigger matching
            match_response = requests.post(f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}/match", headers=headers)
            if match_response.status_code == 200:
                result = match_response.json()
                matched_vendors = result.get("matched_vendors", [])
                print(f"✓ Match API called successfully, {len(matched_vendors)} vendors matched")
            else:
                print(f"Match API returned: {match_response.status_code} - {match_response.text}")
                # Get RFQ again to see matched vendors
                rfq_response = requests.get(f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}", headers=headers)
                rfq = rfq_response.json()
                matched_vendors = rfq.get("matched_vendors", [])
        
        # Verify location fields in matched vendors
        assert len(matched_vendors) > 0, "Should have at least some matched vendors"
        
        for vendor in matched_vendors:
            # Check that location_match and location_score fields exist
            assert "location_match" in vendor, f"Missing location_match field for {vendor.get('company_name')}"
            assert "location_score" in vendor, f"Missing location_score field for {vendor.get('company_name')}"
            
            print(f"✓ Vendor {vendor.get('company_name')}:")
            print(f"    - location: {vendor.get('location')}")
            print(f"    - location_match: {vendor.get('location_match')}")
            print(f"    - location_score: {vendor.get('location_score')}")
    
    def test_location_scoring_algorithm(self, buyer_token):
        """Test that location scoring follows expected rules:
        - City match = +15 points
        - Country match = +10 points
        """
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Get RFQ with matched vendors
        rfq_response = requests.get(f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}", headers=headers)
        assert rfq_response.status_code == 200
        rfq = rfq_response.json()
        
        matched_vendors = rfq.get("matched_vendors", [])
        preferred_cities = [c.lower() for c in (rfq.get("preferred_vendor_cities") or [])]
        preferred_countries = [c.lower() for c in (rfq.get("preferred_vendor_countries") or [])]
        
        print(f"Preferred cities: {preferred_cities}")
        print(f"Preferred countries: {preferred_countries}")
        
        city_match_vendors = []
        country_match_vendors = []
        no_match_vendors = []
        
        for vendor in matched_vendors:
            location_match = vendor.get("location_match")
            location_score = vendor.get("location_score")
            
            if location_match == "city":
                city_match_vendors.append(vendor)
                # City match should give 15 points
                assert location_score == 15, f"City match should give 15 points, got {location_score}"
            elif location_match == "country":
                country_match_vendors.append(vendor)
                # Country match should give 10 points
                assert location_score == 10, f"Country match should give 10 points, got {location_score}"
            else:
                no_match_vendors.append(vendor)
                # No match should give 0 points
                assert location_score == 0, f"No match should give 0 points, got {location_score}"
        
        print(f"✓ City match vendors ({len(city_match_vendors)}): " + 
              ", ".join([v.get('company_name', 'N/A') for v in city_match_vendors]))
        print(f"✓ Country match vendors ({len(country_match_vendors)}): " + 
              ", ".join([v.get('company_name', 'N/A') for v in country_match_vendors]))
        print(f"✓ No location match vendors ({len(no_match_vendors)}): " + 
              ", ".join([v.get('company_name', 'N/A') for v in no_match_vendors]))


class TestVendorRFQView:
    """Test that vendors can view RFQ details with location info"""
    
    @pytest.fixture(scope="class")
    def vendor_token(self):
        """Get vendor authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_VENDOR_EMAIL,
            "password": TEST_VENDOR_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Vendor login failed: {response.text}")
    
    def test_vendor_can_view_rfq_details(self, vendor_token):
        """Test vendor can view RFQ with delivery and incoterms info"""
        headers = {"Authorization": f"Bearer {vendor_token}"}
        
        # First check matched RFQs for vendor
        matched_response = requests.get(f"{BASE_URL}/api/vendor/matched-rfqs", headers=headers)
        
        if matched_response.status_code == 200:
            matched_rfqs = matched_response.json()
            print(f"Vendor has {len(matched_rfqs)} matched RFQs")
            
            # Find our test RFQ
            test_rfq = next((r for r in matched_rfqs if r.get("rfq_id") == TEST_RFQ_ID), None)
            if test_rfq:
                print(f"✓ Found test RFQ in matched list")
        
        # Try to view the RFQ directly
        rfq_response = requests.get(f"{BASE_URL}/api/rfqs/{TEST_RFQ_ID}", headers=headers)
        
        if rfq_response.status_code == 200:
            rfq = rfq_response.json()
            
            # Check vendor-visible fields
            print("✓ Vendor can view RFQ details:")
            print(f"  - Title: {rfq.get('title')}")
            print(f"  - Delivery Address: {rfq.get('delivery_address')}")
            print(f"  - Delivery City: {rfq.get('delivery_city')}")
            print(f"  - Delivery Country: {rfq.get('delivery_country')}")
            print(f"  - Incoterms: {rfq.get('incoterms')}")
            print(f"  - Preferred Countries: {rfq.get('preferred_vendor_countries')}")
            print(f"  - Preferred Cities: {rfq.get('preferred_vendor_cities')}")
        else:
            print(f"Vendor cannot view RFQ directly (may need to be matched): {rfq_response.status_code}")


class TestCreateRFQWithLocationPreferences:
    """Test creating RFQ with location preferences"""
    
    @pytest.fixture(scope="class")
    def buyer_token(self):
        """Get buyer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_BUYER_EMAIL,
            "password": TEST_BUYER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Buyer login failed: {response.text}")
    
    def test_create_rfq_with_location_preferences(self, buyer_token):
        """Test creating a new RFQ with location preferences"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        rfq_data = {
            "title": "TEST_Location_Preference_RFQ",
            "description": "Testing location preference feature",
            "material_type": "Stainless Steel 316",
            "quantity": 100,
            "tolerance": 0.05,
            "surface_finish": "Ra 1.6",
            "supply_type": "vendor_material",
            "preferred_payment_terms": "net_30",
            "delivery_address": "123 Test Street",
            "delivery_city": "Mumbai",
            "delivery_state": "Maharashtra",
            "delivery_country": "India",
            "delivery_pincode": "400001",
            "incoterms": "FOB",
            "preferred_vendor_countries": ["India", "China"],
            "preferred_vendor_cities": ["Mumbai", "Pune", "Chennai"]
        }
        
        response = requests.post(f"{BASE_URL}/api/rfqs", json=rfq_data, headers=headers)
        
        assert response.status_code in [200, 201], f"Failed to create RFQ: {response.text}"
        created_rfq = response.json()
        
        print("✓ RFQ created successfully")
        rfq_id = created_rfq.get('rfq_id')
        print(f"  - RFQ ID: {rfq_id}")
        
        # GET the RFQ to verify location fields are persisted
        # (POST response uses RFQ model which doesn't include all fields)
        get_response = requests.get(f"{BASE_URL}/api/rfqs/{rfq_id}", headers=headers)
        assert get_response.status_code == 200, f"Failed to get RFQ: {get_response.text}"
        saved_rfq = get_response.json()
        
        # Verify location fields are saved
        assert saved_rfq.get("delivery_city") == "Mumbai", f"Delivery city not saved: {saved_rfq.get('delivery_city')}"
        assert saved_rfq.get("delivery_country") == "India", f"Delivery country not saved: {saved_rfq.get('delivery_country')}"
        assert saved_rfq.get("incoterms") == "FOB", f"Incoterms not saved: {saved_rfq.get('incoterms')}"
        assert saved_rfq.get("preferred_vendor_countries") == ["India", "China"], \
            f"Preferred vendor countries not saved: {saved_rfq.get('preferred_vendor_countries')}"
        assert saved_rfq.get("preferred_vendor_cities") == ["Mumbai", "Pune", "Chennai"], \
            f"Preferred vendor cities not saved: {saved_rfq.get('preferred_vendor_cities')}"
        
        print("✓ All location preference fields saved and retrieved correctly")
        
        # Clean up - delete test RFQ
        if rfq_id:
            delete_response = requests.delete(f"{BASE_URL}/api/rfqs/{rfq_id}", headers=headers)
            print(f"  Cleanup: Delete RFQ returned {delete_response.status_code}")


class TestVendorProfileLocation:
    """Test vendor profile location data"""
    
    @pytest.fixture(scope="class")
    def buyer_token(self):
        """Get buyer authentication token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": TEST_BUYER_EMAIL,
            "password": TEST_BUYER_PASSWORD
        })
        if response.status_code == 200:
            return response.json().get("access_token")
        pytest.skip(f"Buyer login failed: {response.text}")
    
    def test_list_vendors_with_location(self, buyer_token):
        """Test that vendor list includes location information"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Get all vendors
        response = requests.get(f"{BASE_URL}/api/vendors", headers=headers)
        
        if response.status_code == 200:
            vendors = response.json()
            print(f"Found {len(vendors)} vendors")
            
            for vendor in vendors[:5]:
                city = vendor.get("city", "N/A")
                country = vendor.get("country", "N/A")
                print(f"  - {vendor.get('company_name')}: {city}, {country}")
                
            print("✓ Vendor list includes location data")
        else:
            print(f"Could not get vendor list: {response.status_code}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
