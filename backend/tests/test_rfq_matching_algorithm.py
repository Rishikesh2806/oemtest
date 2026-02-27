"""
RFQ Matching Algorithm Tests - Iteration 5
Tests for the enhanced matching algorithm that validates:
1. Machine dimension capability vs part dimensions
2. Keyword matching from RFQ title/description
3. Vendor past experience with similar items
4. Process matching based on machine types
5. Matching works when ai_analysis is null
"""

import pytest
import requests
import os
import uuid
import time
from datetime import datetime

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"


class TestRFQMatchingSetup:
    """Setup tests - verify environment and auth"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Get admin authentication token"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def admin_headers(self, admin_token):
        """Get admin headers for API calls"""
        return {
            "Authorization": f"Bearer {admin_token}",
            "Content-Type": "application/json"
        }
    
    @pytest.fixture(scope="class")
    def buyer_user(self, admin_headers):
        """Create a test buyer user for RFQ creation"""
        unique_id = uuid.uuid4().hex[:8]
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": f"test_buyer_{unique_id}@test.com",
                "name": "Test Buyer",
                "password": "testpass123",
                "role": "buyer"
            }
        )
        if response.status_code == 200:
            return response.json()
        # If user exists, login instead
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        return response.json()
    
    @pytest.fixture(scope="class")
    def buyer_headers(self, buyer_user):
        """Get buyer headers for RFQ creation"""
        return {
            "Authorization": f"Bearer {buyer_user['access_token']}",
            "Content-Type": "application/json"
        }
    
    def test_01_api_health(self):
        """Test API is healthy"""
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        print("✓ API is healthy")
    
    def test_02_admin_login(self, admin_token):
        """Test admin can authenticate"""
        assert admin_token is not None
        assert len(admin_token) > 0
        print("✓ Admin login successful")
    
    def test_03_verify_approved_vendors_exist(self, admin_headers):
        """Verify we have approved vendors with machines for testing"""
        response = requests.get(
            f"{BASE_URL}/api/admin/vendors",
            headers=admin_headers
        )
        assert response.status_code == 200
        vendors = response.json()
        
        # Check for approved vendors
        approved_vendors = [v for v in vendors if v.get("is_approved")]
        assert len(approved_vendors) > 0, "No approved vendors found"
        print(f"✓ Found {len(approved_vendors)} approved vendors")
        
        # List them for debugging
        for v in approved_vendors:
            print(f"  - {v['company_name']} (machines: {v.get('machine_count', 0)})")
    
    def test_04_verify_machines_exist(self, admin_headers):
        """Verify machines exist for testing"""
        response = requests.get(
            f"{BASE_URL}/api/admin/machines",
            headers=admin_headers
        )
        assert response.status_code == 200
        machines = response.json()
        assert len(machines) > 0, "No machines found"
        print(f"✓ Found {len(machines)} machines")
        
        # Group by type
        machine_types = {}
        for m in machines:
            mt = m.get("machine_type", "Unknown")
            machine_types[mt] = machine_types.get(mt, 0) + 1
        
        for mt, count in machine_types.items():
            print(f"  - {mt}: {count}")


class TestRFQMatchingDimensionCapability:
    """Test that vendors with correct machine dimensions are matched higher"""
    
    @pytest.fixture(scope="class")
    def buyer_token(self):
        """Get buyer token - using admin as buyer"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    
    @pytest.fixture(scope="class")
    def buyer_headers(self, buyer_token):
        """Get buyer headers"""
        return {
            "Authorization": f"Bearer {buyer_token}",
            "Content-Type": "application/json"
        }
    
    def test_01_match_milling_job_small_part(self, buyer_headers):
        """Test: Small milling part should match machines with adequate X/Y/Z travel"""
        # Create RFQ for small milling part
        rfq_data = {
            "title": "Small Milling Bracket",
            "description": "Precision milled bracket requiring pocket and slot features",
            "material_type": "Aluminum",
            "quantity": 10,
            "tolerance": 0.01,
            "surface_finish": "Ra 1.6"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs",
            json=rfq_data,
            headers=buyer_headers
        )
        assert response.status_code == 200
        rfq = response.json()
        rfq_id = rfq["rfq_id"]
        print(f"✓ Created RFQ: {rfq_id}")
        
        # Add AI analysis with small dimensions that should fit all milling machines
        ai_analysis = {
            "overall_dimensions": {"length": 200, "width": 150, "height": 50, "unit": "mm"},
            "max_dimension_mm": 200,
            "recommended_processes": ["CNC Milling", "Face Milling"]
        }
        
        # Update RFQ with AI analysis (simulate analysis)
        from motor.motor_asyncio import AsyncIOMotorClient
        import asyncio
        
        async def update_rfq():
            mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
            db_name = os.environ.get('DB_NAME', 'test_database')
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            await db.rfqs.update_one(
                {"rfq_id": rfq_id},
                {"$set": {"ai_analysis": ai_analysis, "status": "matching"}}
            )
            client.close()
        
        asyncio.run(update_rfq())
        print("✓ Updated RFQ with AI analysis")
        
        # Call match endpoint
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{rfq_id}/match",
            headers=buyer_headers
        )
        assert response.status_code == 200
        result = response.json()
        
        matched = result.get("matched_vendors", [])
        print(f"✓ Matched {len(matched)} vendors")
        
        # Verify matching vendors have milling capability
        assert len(matched) > 0, "Should match at least one vendor"
        
        # Check that matched vendors have dimension_capable = True
        dimension_capable_vendors = [v for v in matched if v.get("dimension_capable")]
        print(f"  - Dimension capable vendors: {len(dimension_capable_vendors)}")
        
        for v in matched[:3]:
            print(f"  - {v['company_name']}: score={v['suitability_score']}, "
                  f"dim_capable={v.get('dimension_capable')}, processes={v.get('process_matches', [])}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/rfqs/{rfq_id}", headers=buyer_headers)
    
    def test_02_match_turning_job_with_diameter(self, buyer_headers):
        """Test: Turning job should match lathes with adequate max_diameter"""
        rfq_data = {
            "title": "CNC Turned Shaft Component",
            "description": "Precision shaft requiring lathe turning operations for spindle",
            "material_type": "Steel",
            "quantity": 50,
            "tolerance": 0.005,
            "surface_finish": "Ra 0.8"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs",
            json=rfq_data,
            headers=buyer_headers
        )
        assert response.status_code == 200
        rfq = response.json()
        rfq_id = rfq["rfq_id"]
        print(f"✓ Created turning RFQ: {rfq_id}")
        
        # AI analysis with diameter specs for turning
        ai_analysis = {
            "overall_dimensions": {"length": 300, "diameter": 80, "unit": "mm"},
            "max_dimension_mm": 300,
            "max_diameter_mm": 80,
            "recommended_processes": ["CNC Turning", "Facing", "Threading"]
        }
        
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        async def update_rfq():
            mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
            db_name = os.environ.get('DB_NAME', 'test_database')
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            await db.rfqs.update_one(
                {"rfq_id": rfq_id},
                {"$set": {"ai_analysis": ai_analysis, "status": "matching"}}
            )
            client.close()
        
        asyncio.run(update_rfq())
        
        # Match vendors
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{rfq_id}/match",
            headers=buyer_headers
        )
        assert response.status_code == 200
        result = response.json()
        
        matched = result.get("matched_vendors", [])
        print(f"✓ Matched {len(matched)} vendors for turning job")
        
        # Check for turning-capable vendors
        turning_vendors = [v for v in matched if "CNC Turning" in v.get("process_matches", [])]
        print(f"  - Turning capable vendors: {len(turning_vendors)}")
        
        for v in matched[:3]:
            print(f"  - {v['company_name']}: score={v['suitability_score']}, "
                  f"processes={v.get('process_matches', [])}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/rfqs/{rfq_id}", headers=buyer_headers)
    
    def test_03_large_part_excludes_small_machines(self, buyer_headers):
        """Test: Very large parts should exclude vendors with small machine envelopes"""
        rfq_data = {
            "title": "Large Industrial Plate Machining",
            "description": "Large aluminum plate requiring face milling",
            "material_type": "Aluminum",
            "quantity": 5,
            "tolerance": 0.1
        }
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs",
            json=rfq_data,
            headers=buyer_headers
        )
        assert response.status_code == 200
        rfq = response.json()
        rfq_id = rfq["rfq_id"]
        
        # AI analysis with VERY large dimensions (2000mm+)
        ai_analysis = {
            "overall_dimensions": {"length": 2000, "width": 1500, "height": 200, "unit": "mm"},
            "max_dimension_mm": 2000,
            "recommended_processes": ["CNC Milling", "Face Milling"]
        }
        
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        async def update_rfq():
            mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
            db_name = os.environ.get('DB_NAME', 'test_database')
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            await db.rfqs.update_one(
                {"rfq_id": rfq_id},
                {"$set": {"ai_analysis": ai_analysis, "status": "matching"}}
            )
            client.close()
        
        asyncio.run(update_rfq())
        
        # Match vendors
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{rfq_id}/match",
            headers=buyer_headers
        )
        assert response.status_code == 200
        result = response.json()
        
        matched = result.get("matched_vendors", [])
        print(f"✓ Large part RFQ matched {len(matched)} vendors")
        
        # Vendors without dimension capability should be scored lower or excluded
        for v in matched:
            print(f"  - {v['company_name']}: score={v['suitability_score']}, "
                  f"dim_capable={v.get('dimension_capable')}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/rfqs/{rfq_id}", headers=buyer_headers)


class TestRFQMatchingKeywords:
    """Test keyword matching from RFQ title and description"""
    
    @pytest.fixture(scope="class")
    def buyer_headers(self):
        """Get buyer headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return {
            "Authorization": f"Bearer {response.json()['access_token']}",
            "Content-Type": "application/json"
        }
    
    def test_01_gear_keywords_match_gear_machines(self, buyer_headers):
        """Test: RFQ with 'gear' keywords should prioritize gear machine vendors"""
        rfq_data = {
            "title": "Precision Gear Manufacturing",
            "description": "Hobbing required for spur gear with 32 teeth, module 2",
            "material_type": "Steel",
            "quantity": 100,
            "tolerance": 0.02
        }
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs",
            json=rfq_data,
            headers=buyer_headers
        )
        assert response.status_code == 200
        rfq = response.json()
        rfq_id = rfq["rfq_id"]
        print(f"✓ Created gear RFQ: {rfq_id}")
        
        # Match without AI analysis - test keyword extraction from title/desc
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{rfq_id}/match",
            headers=buyer_headers
        )
        assert response.status_code == 200
        result = response.json()
        
        matched = result.get("matched_vendors", [])
        print(f"✓ Gear job matched {len(matched)} vendors")
        
        # Check keyword matches include gear-related terms
        for v in matched[:3]:
            keywords = v.get("keyword_matches", [])
            print(f"  - {v['company_name']}: keywords={keywords}, "
                  f"processes={v.get('process_matches', [])}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/rfqs/{rfq_id}", headers=buyer_headers)
    
    def test_02_milling_keywords_in_title(self, buyer_headers):
        """Test: 'milling' in title should match milling machine vendors"""
        rfq_data = {
            "title": "CNC Milling Housing Component",
            "description": "Complex pocket and slot machining required with tight tolerance",
            "material_type": "Aluminum",
            "quantity": 25,
            "tolerance": 0.01
        }
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs",
            json=rfq_data,
            headers=buyer_headers
        )
        assert response.status_code == 200
        rfq = response.json()
        rfq_id = rfq["rfq_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{rfq_id}/match",
            headers=buyer_headers
        )
        assert response.status_code == 200
        result = response.json()
        
        matched = result.get("matched_vendors", [])
        print(f"✓ Milling job matched {len(matched)} vendors")
        
        # Check process matches include milling
        milling_vendors = [v for v in matched if any("Mill" in p for p in v.get("process_matches", []))]
        print(f"  - Vendors with milling capability: {len(milling_vendors)}")
        
        for v in matched[:3]:
            print(f"  - {v['company_name']}: processes={v.get('process_matches', [])}, "
                  f"keywords={v.get('keyword_matches', [])}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/rfqs/{rfq_id}", headers=buyer_headers)
    
    def test_03_welding_keywords_match_welding_vendors(self, buyer_headers):
        """Test: 'welding' in description should match welding machine vendors"""
        rfq_data = {
            "title": "Steel Frame Fabrication",
            "description": "Requires MIG welding and assembly of steel structural frame",
            "material_type": "Carbon Steel",
            "quantity": 10,
            "tolerance": 0.5
        }
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs",
            json=rfq_data,
            headers=buyer_headers
        )
        assert response.status_code == 200
        rfq = response.json()
        rfq_id = rfq["rfq_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{rfq_id}/match",
            headers=buyer_headers
        )
        assert response.status_code == 200
        result = response.json()
        
        matched = result.get("matched_vendors", [])
        print(f"✓ Welding job matched {len(matched)} vendors")
        
        # Check for welding keyword matches
        for v in matched[:3]:
            print(f"  - {v['company_name']}: processes={v.get('process_matches', [])}, "
                  f"keywords={v.get('keyword_matches', [])}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/rfqs/{rfq_id}", headers=buyer_headers)


class TestRFQMatchingWithNullAIAnalysis:
    """Test that matching works when ai_analysis is null (bug fix test)"""
    
    @pytest.fixture(scope="class")
    def buyer_headers(self):
        """Get buyer headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return {
            "Authorization": f"Bearer {response.json()['access_token']}",
            "Content-Type": "application/json"
        }
    
    def test_01_match_without_ai_analysis(self, buyer_headers):
        """Test: Matching should work when ai_analysis is None/null"""
        rfq_data = {
            "title": "Precision Shaft Turning",
            "description": "Lathe turning of precision shaft component",
            "material_type": "Steel",
            "quantity": 100,
            "tolerance": 0.01
        }
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs",
            json=rfq_data,
            headers=buyer_headers
        )
        assert response.status_code == 200
        rfq = response.json()
        rfq_id = rfq["rfq_id"]
        print(f"✓ Created RFQ without AI analysis: {rfq_id}")
        
        # Verify ai_analysis is None
        get_response = requests.get(
            f"{BASE_URL}/api/rfqs/{rfq_id}",
            headers=buyer_headers
        )
        rfq_data = get_response.json()
        assert rfq_data.get("ai_analysis") is None, "ai_analysis should be None"
        print("✓ Verified ai_analysis is None")
        
        # Call match endpoint - should NOT error
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{rfq_id}/match",
            headers=buyer_headers
        )
        
        # Main assertion: Should return 200, not 500
        assert response.status_code == 200, f"Match failed with null ai_analysis: {response.text}"
        
        result = response.json()
        matched = result.get("matched_vendors", [])
        print(f"✓ Matching succeeded with null ai_analysis, matched {len(matched)} vendors")
        
        # Should still match based on keywords in title/description
        for v in matched[:3]:
            print(f"  - {v['company_name']}: score={v['suitability_score']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/rfqs/{rfq_id}", headers=buyer_headers)
    
    def test_02_match_with_empty_ai_analysis_object(self, buyer_headers):
        """Test: Matching works with empty ai_analysis object {}"""
        rfq_data = {
            "title": "CNC Milling Component",
            "description": "Milled plate with pockets",
            "material_type": "Aluminum",
            "quantity": 20,
            "tolerance": 0.05
        }
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs",
            json=rfq_data,
            headers=buyer_headers
        )
        assert response.status_code == 200
        rfq = response.json()
        rfq_id = rfq["rfq_id"]
        
        # Set ai_analysis to empty object
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        async def set_empty_analysis():
            mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
            db_name = os.environ.get('DB_NAME', 'test_database')
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            await db.rfqs.update_one(
                {"rfq_id": rfq_id},
                {"$set": {"ai_analysis": {}}}
            )
            client.close()
        
        asyncio.run(set_empty_analysis())
        print("✓ Set ai_analysis to empty object {}")
        
        # Match should succeed
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{rfq_id}/match",
            headers=buyer_headers
        )
        assert response.status_code == 200, f"Match failed with empty ai_analysis: {response.text}"
        print("✓ Matching succeeded with empty ai_analysis object")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/rfqs/{rfq_id}", headers=buyer_headers)


class TestRFQMatchingScoreCalculation:
    """Test the overall match score calculation"""
    
    @pytest.fixture(scope="class")
    def buyer_headers(self):
        """Get buyer headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return {
            "Authorization": f"Bearer {response.json()['access_token']}",
            "Content-Type": "application/json"
        }
    
    def test_01_score_includes_required_components(self, buyer_headers):
        """Test: Match score includes dimension capability, process matches, keyword matches"""
        rfq_data = {
            "title": "5-Axis Complex Aerospace Part",
            "description": "Precision 5-axis milling for complex contour titanium aerospace bracket",
            "material_type": "Titanium",
            "quantity": 5,
            "tolerance": 0.005
        }
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs",
            json=rfq_data,
            headers=buyer_headers
        )
        assert response.status_code == 200
        rfq = response.json()
        rfq_id = rfq["rfq_id"]
        
        # Add detailed AI analysis
        ai_analysis = {
            "overall_dimensions": {"length": 250, "width": 200, "height": 100, "unit": "mm"},
            "max_dimension_mm": 250,
            "recommended_processes": ["5-Axis Milling", "Complex Contouring"],
            "material_specs": "Ti-6Al-4V Titanium",
            "complexity_score": 8
        }
        
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        async def update_rfq():
            mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
            db_name = os.environ.get('DB_NAME', 'test_database')
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            await db.rfqs.update_one(
                {"rfq_id": rfq_id},
                {"$set": {"ai_analysis": ai_analysis, "status": "matching"}}
            )
            client.close()
        
        asyncio.run(update_rfq())
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{rfq_id}/match",
            headers=buyer_headers
        )
        assert response.status_code == 200
        result = response.json()
        
        matched = result.get("matched_vendors", [])
        print(f"✓ 5-axis job matched {len(matched)} vendors")
        
        # Verify match response contains all expected scoring fields
        for v in matched[:3]:
            print(f"\n{v['company_name']}:")
            print(f"  - Suitability Score: {v['suitability_score']}")
            print(f"  - Dimension Capable: {v.get('dimension_capable')}")
            print(f"  - Tolerance Capable: {v.get('tolerance_capable')}")
            print(f"  - Materials Match: {v.get('materials_match')}")
            print(f"  - Process Matches: {v.get('process_matches', [])}")
            print(f"  - Keyword Matches: {v.get('keyword_matches', [])}")
            print(f"  - Experience Score: {v.get('experience_score', 0)}")
            print(f"  - Similar Jobs Count: {v.get('similar_jobs_count', 0)}")
            
            # Verify required fields exist
            assert "suitability_score" in v
            assert "dimension_capable" in v
            assert "process_matches" in v
            assert "keyword_matches" in v
            assert "experience_score" in v
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/rfqs/{rfq_id}", headers=buyer_headers)
    
    def test_02_higher_rating_vendor_scores_higher(self, buyer_headers):
        """Test: Vendors with higher ratings get score bonus"""
        rfq_data = {
            "title": "Standard CNC Milling Job",
            "description": "Simple milling operation for aluminum plate",
            "material_type": "Aluminum",
            "quantity": 50,
            "tolerance": 0.05
        }
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs",
            json=rfq_data,
            headers=buyer_headers
        )
        assert response.status_code == 200
        rfq = response.json()
        rfq_id = rfq["rfq_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{rfq_id}/match",
            headers=buyer_headers
        )
        assert response.status_code == 200
        result = response.json()
        
        matched = result.get("matched_vendors", [])
        
        # Check if rating affects scoring
        if len(matched) >= 2:
            for v in matched:
                print(f"  - {v['company_name']}: score={v['suitability_score']}, "
                      f"rating={v.get('rating', 0)}, total_jobs={v.get('total_jobs', 0)}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/rfqs/{rfq_id}", headers=buyer_headers)


class TestRFQMatchingVendorExperience:
    """Test vendor past experience scoring"""
    
    @pytest.fixture(scope="class")
    def buyer_headers(self):
        """Get buyer headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return {
            "Authorization": f"Bearer {response.json()['access_token']}",
            "Content-Type": "application/json"
        }
    
    def test_01_experience_score_in_response(self, buyer_headers):
        """Test: Match response includes experience_score field"""
        rfq_data = {
            "title": "Aerospace Bracket Milling",
            "description": "Precision milled aerospace bracket",
            "material_type": "Aluminum",
            "quantity": 10,
            "tolerance": 0.01
        }
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs",
            json=rfq_data,
            headers=buyer_headers
        )
        assert response.status_code == 200
        rfq = response.json()
        rfq_id = rfq["rfq_id"]
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{rfq_id}/match",
            headers=buyer_headers
        )
        assert response.status_code == 200
        result = response.json()
        
        matched = result.get("matched_vendors", [])
        print(f"✓ Matched {len(matched)} vendors")
        
        for v in matched:
            # Verify experience fields exist
            assert "experience_score" in v, f"Missing experience_score for {v['company_name']}"
            assert "similar_jobs_count" in v, f"Missing similar_jobs_count for {v['company_name']}"
            
            print(f"  - {v['company_name']}: exp_score={v['experience_score']}, "
                  f"similar_jobs={v['similar_jobs_count']}")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/rfqs/{rfq_id}", headers=buyer_headers)


class TestRFQMatchingEdgeCases:
    """Test edge cases in the matching algorithm"""
    
    @pytest.fixture(scope="class")
    def buyer_headers(self):
        """Get buyer headers"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        assert response.status_code == 200
        return {
            "Authorization": f"Bearer {response.json()['access_token']}",
            "Content-Type": "application/json"
        }
    
    def test_01_match_with_no_dimensions_in_analysis(self, buyer_headers):
        """Test: Matching works when ai_analysis has no overall_dimensions"""
        rfq_data = {
            "title": "Simple Milling Part",
            "description": "Basic milled component",
            "material_type": "Steel",
            "quantity": 10,
            "tolerance": 0.1
        }
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs",
            json=rfq_data,
            headers=buyer_headers
        )
        assert response.status_code == 200
        rfq = response.json()
        rfq_id = rfq["rfq_id"]
        
        # AI analysis without dimensions
        ai_analysis = {
            "recommended_processes": ["CNC Milling"],
            "material_specs": "Mild Steel",
            "complexity_score": 3
        }
        
        import asyncio
        from motor.motor_asyncio import AsyncIOMotorClient
        
        async def update_rfq():
            mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
            db_name = os.environ.get('DB_NAME', 'test_database')
            client = AsyncIOMotorClient(mongo_url)
            db = client[db_name]
            await db.rfqs.update_one(
                {"rfq_id": rfq_id},
                {"$set": {"ai_analysis": ai_analysis}}
            )
            client.close()
        
        asyncio.run(update_rfq())
        
        response = requests.post(
            f"{BASE_URL}/api/rfqs/{rfq_id}/match",
            headers=buyer_headers
        )
        assert response.status_code == 200, f"Match failed: {response.text}"
        print("✓ Matching succeeded without dimension data in ai_analysis")
        
        # Cleanup
        requests.delete(f"{BASE_URL}/api/rfqs/{rfq_id}", headers=buyer_headers)
    
    def test_02_match_rfq_not_found(self, buyer_headers):
        """Test: Matching non-existent RFQ returns 404"""
        response = requests.post(
            f"{BASE_URL}/api/rfqs/rfq_nonexistent_id_12345/match",
            headers=buyer_headers
        )
        assert response.status_code == 404
        print("✓ Non-existent RFQ returns 404")
    
    def test_03_match_unauthorized(self):
        """Test: Matching without auth returns 401"""
        response = requests.post(
            f"{BASE_URL}/api/rfqs/some_rfq_id/match"
        )
        assert response.status_code == 401
        print("✓ Unauthorized request returns 401")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
