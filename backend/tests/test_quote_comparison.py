"""
Test Quote Comparison Feature
Tests the enhanced quotes API endpoint that returns enriched vendor data for quote comparison

Features tested:
- GET /api/quotes/rfq/{rfq_id} - Returns quotes with enriched vendor data
- Quote fields: vendor_name, vendor_rating, vendor_location, vendor_machines, vendor_certifications, vendor_acceptance_rate
- Badge calculation: Best Price, Fastest, Top Rated
"""
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

class TestQuoteComparisonAPI:
    """Tests for the enhanced quotes API for comparison feature"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test by getting auth token"""
        self.buyer_token = None
        self.admin_token = None
        
        # Login as buyer
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "buyer@offoadex.com",
            "password": "buyer123"
        })
        if response.status_code == 200:
            self.buyer_token = response.json().get("access_token")
        
        # Login as admin
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@offoadex.com",
            "password": "admin123"
        })
        if response.status_code == 200:
            self.admin_token = response.json().get("access_token")
    
    def test_get_quotes_for_comparison_rfq(self):
        """Test that quotes endpoint returns enriched vendor data for rfq_b125b67d20d8"""
        if not self.buyer_token:
            pytest.skip("Buyer login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/quotes/rfq/rfq_b125b67d20d8",
            headers={"Authorization": f"Bearer {self.buyer_token}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        quotes = response.json()
        
        # Should have 4 test quotes
        assert len(quotes) >= 4, f"Expected at least 4 quotes, got {len(quotes)}"
        print(f"✓ Found {len(quotes)} quotes for comparison")
    
    def test_quotes_have_vendor_name(self):
        """Test that quotes include vendor_name field"""
        if not self.buyer_token:
            pytest.skip("Buyer login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/quotes/rfq/rfq_b125b67d20d8",
            headers={"Authorization": f"Bearer {self.buyer_token}"}
        )
        
        assert response.status_code == 200
        quotes = response.json()
        
        for quote in quotes:
            assert "vendor_name" in quote, f"Missing vendor_name in quote {quote.get('quote_id')}"
            assert quote["vendor_name"], f"Empty vendor_name in quote {quote.get('quote_id')}"
        
        vendor_names = [q["vendor_name"] for q in quotes]
        print(f"✓ Vendor names: {vendor_names}")
    
    def test_quotes_have_vendor_rating(self):
        """Test that quotes include vendor_rating field"""
        if not self.buyer_token:
            pytest.skip("Buyer login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/quotes/rfq/rfq_b125b67d20d8",
            headers={"Authorization": f"Bearer {self.buyer_token}"}
        )
        
        assert response.status_code == 200
        quotes = response.json()
        
        for quote in quotes:
            assert "vendor_rating" in quote, f"Missing vendor_rating in quote {quote.get('quote_id')}"
            assert isinstance(quote["vendor_rating"], (int, float)), "vendor_rating should be numeric"
        
        # Verify we have the expected top rating (4.9)
        ratings = [q["vendor_rating"] for q in quotes]
        max_rating = max(ratings)
        print(f"✓ Vendor ratings: {ratings}, Top rated: {max_rating}")
        assert max_rating == 4.9, f"Expected top rating 4.9, got {max_rating}"
    
    def test_quotes_have_vendor_location(self):
        """Test that quotes include vendor_location field"""
        if not self.buyer_token:
            pytest.skip("Buyer login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/quotes/rfq/rfq_b125b67d20d8",
            headers={"Authorization": f"Bearer {self.buyer_token}"}
        )
        
        assert response.status_code == 200
        quotes = response.json()
        
        for quote in quotes:
            assert "vendor_location" in quote, f"Missing vendor_location in quote {quote.get('quote_id')}"
        
        locations = [q["vendor_location"] for q in quotes]
        print(f"✓ Vendor locations: {locations}")
    
    def test_quotes_have_vendor_machines(self):
        """Test that quotes include vendor_machines array"""
        if not self.buyer_token:
            pytest.skip("Buyer login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/quotes/rfq/rfq_b125b67d20d8",
            headers={"Authorization": f"Bearer {self.buyer_token}"}
        )
        
        assert response.status_code == 200
        quotes = response.json()
        
        for quote in quotes:
            assert "vendor_machines" in quote, f"Missing vendor_machines in quote {quote.get('quote_id')}"
            assert isinstance(quote["vendor_machines"], list), "vendor_machines should be a list"
        
        # Count quotes with machines
        quotes_with_machines = sum(1 for q in quotes if len(q["vendor_machines"]) > 0)
        print(f"✓ {quotes_with_machines}/{len(quotes)} quotes have machine info")
    
    def test_quotes_have_vendor_certifications(self):
        """Test that quotes include vendor_certifications array"""
        if not self.buyer_token:
            pytest.skip("Buyer login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/quotes/rfq/rfq_b125b67d20d8",
            headers={"Authorization": f"Bearer {self.buyer_token}"}
        )
        
        assert response.status_code == 200
        quotes = response.json()
        
        for quote in quotes:
            assert "vendor_certifications" in quote, f"Missing vendor_certifications in quote {quote.get('quote_id')}"
            assert isinstance(quote["vendor_certifications"], list), "vendor_certifications should be a list"
        
        # Show certifications
        for quote in quotes:
            print(f"  {quote['vendor_name']}: {quote['vendor_certifications']}")
    
    def test_quotes_have_vendor_acceptance_rate(self):
        """Test that quotes include vendor_acceptance_rate field"""
        if not self.buyer_token:
            pytest.skip("Buyer login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/quotes/rfq/rfq_b125b67d20d8",
            headers={"Authorization": f"Bearer {self.buyer_token}"}
        )
        
        assert response.status_code == 200
        quotes = response.json()
        
        for quote in quotes:
            assert "vendor_acceptance_rate" in quote, f"Missing vendor_acceptance_rate in quote {quote.get('quote_id')}"
            assert isinstance(quote["vendor_acceptance_rate"], (int, float)), "vendor_acceptance_rate should be numeric"
            assert 0 <= quote["vendor_acceptance_rate"] <= 100, "Acceptance rate should be 0-100"
        
        rates = [q["vendor_acceptance_rate"] for q in quotes]
        print(f"✓ Acceptance rates: {rates}")
    
    def test_quotes_have_vendor_ref_ids(self):
        """Test that quotes include vendor_id_ref and vendor_user_id for linking"""
        if not self.buyer_token:
            pytest.skip("Buyer login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/quotes/rfq/rfq_b125b67d20d8",
            headers={"Authorization": f"Bearer {self.buyer_token}"}
        )
        
        assert response.status_code == 200
        quotes = response.json()
        
        for quote in quotes:
            assert "vendor_id_ref" in quote, f"Missing vendor_id_ref in quote {quote.get('quote_id')}"
            assert "vendor_user_id" in quote, f"Missing vendor_user_id in quote {quote.get('quote_id')}"
            assert quote["vendor_id_ref"], "vendor_id_ref should not be empty"
            assert quote["vendor_user_id"], "vendor_user_id should not be empty"
        
        print(f"✓ All {len(quotes)} quotes have vendor reference IDs")
    
    def test_best_price_badge_calculation(self):
        """Test that Best Price badge would go to lowest price quote ($2,200)"""
        if not self.buyer_token:
            pytest.skip("Buyer login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/quotes/rfq/rfq_b125b67d20d8",
            headers={"Authorization": f"Bearer {self.buyer_token}"}
        )
        
        assert response.status_code == 200
        quotes = response.json()
        
        # Filter pending quotes only
        pending_quotes = [q for q in quotes if q.get("status") == "pending"]
        assert len(pending_quotes) >= 2, "Need at least 2 pending quotes"
        
        # Find lowest price
        lowest_price = min(q["price"] for q in pending_quotes)
        best_price_vendors = [q["vendor_name"] for q in pending_quotes if q["price"] == lowest_price]
        
        assert lowest_price == 2200, f"Expected lowest price $2,200, got ${lowest_price}"
        print(f"✓ Best Price: ${lowest_price} - {best_price_vendors}")
    
    def test_fastest_badge_calculation(self):
        """Test that Fastest badge would go to shortest lead time (10 days)"""
        if not self.buyer_token:
            pytest.skip("Buyer login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/quotes/rfq/rfq_b125b67d20d8",
            headers={"Authorization": f"Bearer {self.buyer_token}"}
        )
        
        assert response.status_code == 200
        quotes = response.json()
        
        # Filter pending quotes only
        pending_quotes = [q for q in quotes if q.get("status") == "pending"]
        
        # Find fastest lead time
        fastest = min(q["lead_time_days"] for q in pending_quotes)
        fastest_vendors = [q["vendor_name"] for q in pending_quotes if q["lead_time_days"] == fastest]
        
        assert fastest == 10, f"Expected fastest lead time 10 days, got {fastest}"
        print(f"✓ Fastest: {fastest} days - {fastest_vendors}")
    
    def test_top_rated_badge_calculation(self):
        """Test that Top Rated badge would go to highest rating (4.9)"""
        if not self.buyer_token:
            pytest.skip("Buyer login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/quotes/rfq/rfq_b125b67d20d8",
            headers={"Authorization": f"Bearer {self.buyer_token}"}
        )
        
        assert response.status_code == 200
        quotes = response.json()
        
        # Filter pending quotes only
        pending_quotes = [q for q in quotes if q.get("status") == "pending"]
        
        # Find highest rating
        highest_rating = max(q["vendor_rating"] for q in pending_quotes)
        top_rated_vendors = [q["vendor_name"] for q in pending_quotes if q["vendor_rating"] == highest_rating]
        
        assert highest_rating == 4.9, f"Expected highest rating 4.9, got {highest_rating}"
        print(f"✓ Top Rated: {highest_rating} - {top_rated_vendors}")
    
    def test_all_badges_go_to_correct_vendors(self):
        """Test that all three badges (Best Price, Fastest, Top Rated) are assigned correctly"""
        if not self.buyer_token:
            pytest.skip("Buyer login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/quotes/rfq/rfq_b125b67d20d8",
            headers={"Authorization": f"Bearer {self.buyer_token}"}
        )
        
        assert response.status_code == 200
        quotes = response.json()
        pending_quotes = [q for q in quotes if q.get("status") == "pending"]
        
        lowest_price = min(q["price"] for q in pending_quotes)
        fastest = min(q["lead_time_days"] for q in pending_quotes)
        highest_rating = max(q["vendor_rating"] for q in pending_quotes)
        
        # Expected values
        assert lowest_price == 2200, "Best Price should be $2,200"
        assert fastest == 10, "Fastest should be 10 days"
        assert highest_rating == 4.9, "Top Rated should be 4.9"
        
        # Find which vendor gets each badge
        best_price_vendor = next(q["vendor_name"] for q in pending_quotes if q["price"] == lowest_price)
        fastest_vendor = next(q["vendor_name"] for q in pending_quotes if q["lead_time_days"] == fastest)
        top_rated_vendor = next(q["vendor_name"] for q in pending_quotes if q["vendor_rating"] == highest_rating)
        
        print(f"✓ Best Price Badge: {best_price_vendor} (${lowest_price})")
        print(f"✓ Fastest Badge: {fastest_vendor} ({fastest} days)")
        print(f"✓ Top Rated Badge: {top_rated_vendor} ({highest_rating} rating)")
    
    def test_quotes_endpoint_requires_auth(self):
        """Test that quotes endpoint requires authentication"""
        response = requests.get(f"{BASE_URL}/api/quotes/rfq/rfq_b125b67d20d8")
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        print("✓ Quotes endpoint correctly requires authentication")
    
    def test_nonexistent_rfq_quotes(self):
        """Test that requesting quotes for non-existent RFQ returns empty list"""
        if not self.buyer_token:
            pytest.skip("Buyer login failed")
        
        response = requests.get(
            f"{BASE_URL}/api/quotes/rfq/nonexistent_rfq_12345",
            headers={"Authorization": f"Bearer {self.buyer_token}"}
        )
        
        # Should return 200 with empty list (not 404)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        quotes = response.json()
        assert isinstance(quotes, list), "Response should be a list"
        print(f"✓ Non-existent RFQ returns empty list: {len(quotes)} quotes")


class TestQuoteAcceptFromComparison:
    """Test accepting quotes from comparison view"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test by getting auth token"""
        self.buyer_token = None
        
        # Login as buyer
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "buyer@offoadex.com",
            "password": "buyer123"
        })
        if response.status_code == 200:
            self.buyer_token = response.json().get("access_token")
    
    def test_accept_quote_endpoint_exists(self):
        """Test that POST /api/quotes/{quote_id}/accept endpoint exists"""
        if not self.buyer_token:
            pytest.skip("Buyer login failed")
        
        # Try to accept a non-existent quote to verify endpoint exists
        response = requests.post(
            f"{BASE_URL}/api/quotes/nonexistent_quote/accept",
            headers={"Authorization": f"Bearer {self.buyer_token}"}
        )
        
        # Should return 404 (quote not found), not 405 (method not allowed)
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        print("✓ Accept quote endpoint exists and returns 404 for non-existent quote")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
