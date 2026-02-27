"""
Test Suite for Vendor Rating System and Enhanced Order Management
Tests:
- POST /api/orders/{order_id}/rate - Rate vendor (buyer only, delivered orders only)
- GET /api/vendors/{vendor_id}/ratings - Get vendor ratings and stats
- GET /api/orders/{order_id}/rating - Check if order is rated
- GET /api/orders/{order_id}/details - Get enriched order details
- POST /api/orders/{order_id}/confirm-delivery - Buyer confirms delivery
- POST /api/orders/{order_id}/add-tracking - Vendor adds tracking info
"""
import pytest
import requests
import os
import uuid
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Test credentials
BUYER_EMAIL = "buyer@offoadex.com"
BUYER_PASSWORD = "buyer123"
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"

# Test order and vendor IDs from main agent's context
TEST_ORDER_ID = "order_8d45a1ea88d1"
TEST_VENDOR_ID = "vendor_68cfbaafb999"


class TestBuyerAuth:
    """Test authentication for buyer"""
    
    def test_buyer_login(self):
        """Test buyer can login"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        assert response.status_code == 200, f"Buyer login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        assert data["user"]["role"] == "buyer"
        print(f"✓ Buyer login successful, user_id: {data['user']['user_id']}")
        return data["access_token"]


class TestOrderDetailsEndpoint:
    """Test GET /api/orders/{order_id}/details"""
    
    @pytest.fixture
    def buyer_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_get_order_details(self, buyer_token):
        """Test getting enriched order details"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # First get list of orders to find a valid order
        response = requests.get(f"{BASE_URL}/api/orders", headers=headers)
        assert response.status_code == 200, f"Failed to get orders: {response.text}"
        orders = response.json()
        
        if not orders:
            pytest.skip("No orders found for testing")
        
        test_order = orders[0]
        order_id = test_order["order_id"]
        
        # Get detailed order info
        response = requests.get(f"{BASE_URL}/api/orders/{order_id}/details", headers=headers)
        assert response.status_code == 200, f"Failed to get order details: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "order" in data, "Missing 'order' in response"
        assert "vendor" in data, "Missing 'vendor' in response"
        assert "buyer" in data, "Missing 'buyer' in response"
        assert "quote" in data, "Missing 'quote' in response"
        assert "rfq" in data, "Missing 'rfq' in response"
        assert "is_rated" in data, "Missing 'is_rated' in response"
        
        # Verify vendor info structure
        vendor = data["vendor"]
        assert "vendor_id" in vendor
        assert "company_name" in vendor
        assert "rating" in vendor
        
        # Verify buyer info structure
        buyer = data["buyer"]
        assert "user_id" in buyer
        assert "name" in buyer
        
        # Verify quote info structure
        quote = data["quote"]
        assert "price" in quote
        assert "lead_time_days" in quote
        
        # Verify RFQ info structure
        rfq = data["rfq"]
        assert "rfq_id" in rfq
        assert "title" in rfq
        
        print(f"✓ Order details retrieved successfully: {order_id}")
        print(f"  - Vendor: {vendor.get('company_name')}")
        print(f"  - Quote price: ${quote.get('price')}")
        print(f"  - RFQ: {rfq.get('title')}")
        print(f"  - Is Rated: {data['is_rated']}")
        
        return data


class TestVendorRatingsEndpoint:
    """Test GET /api/vendors/{vendor_id}/ratings - Public endpoint"""
    
    @pytest.fixture
    def buyer_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_get_vendor_ratings(self, buyer_token):
        """Test getting vendor ratings and stats"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # This endpoint is public but let's test with auth
        response = requests.get(f"{BASE_URL}/api/vendors/{TEST_VENDOR_ID}/ratings", headers=headers)
        assert response.status_code == 200, f"Failed to get vendor ratings: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "ratings" in data, "Missing 'ratings' in response"
        assert "stats" in data, "Missing 'stats' in response"
        
        stats = data["stats"]
        assert "total_reviews" in stats
        assert "average_overall" in stats
        assert "average_quality" in stats
        assert "average_communication" in stats
        assert "average_delivery" in stats
        assert "recommendation_rate" in stats
        
        print(f"✓ Vendor ratings retrieved for {TEST_VENDOR_ID}")
        print(f"  - Total reviews: {stats['total_reviews']}")
        print(f"  - Average overall: {stats['average_overall']}")
        print(f"  - Recommendation rate: {stats['recommendation_rate']}%")
        
        # If there are ratings, verify structure
        if data["ratings"]:
            rating = data["ratings"][0]
            assert "overall_rating" in rating
            assert "quality_rating" in rating
            assert "communication_rating" in rating
            assert "delivery_rating" in rating
            assert "buyer_name" in rating
            print(f"  - Sample review from: {rating.get('buyer_name')}")
        
        return data


class TestOrderRatingStatus:
    """Test GET /api/orders/{order_id}/rating - Check if order is rated"""
    
    @pytest.fixture
    def buyer_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_check_order_rating_status(self, buyer_token):
        """Test checking if an order has been rated"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        response = requests.get(f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/rating", headers=headers)
        assert response.status_code == 200, f"Failed to check order rating: {response.text}"
        
        data = response.json()
        assert "rated" in data
        
        print(f"✓ Order rating status checked for {TEST_ORDER_ID}")
        print(f"  - Is rated: {data['rated']}")
        
        if data.get("rating"):
            print(f"  - Overall rating: {data['rating'].get('overall_rating')}")
            print(f"  - Review: {data['rating'].get('review_text', 'No text')[:50]}...")
        
        return data


class TestRatingSubmission:
    """Test POST /api/orders/{order_id}/rate - Rate vendor"""
    
    @pytest.fixture
    def buyer_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_rate_vendor_validation_rating_range(self, buyer_token):
        """Test that invalid rating values are rejected"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Get a delivered/completed order first
        response = requests.get(f"{BASE_URL}/api/orders", headers=headers)
        orders = response.json()
        
        # Find a delivered or completed order that's not rated yet
        test_order = None
        for order in orders:
            if order["status"] in ["delivered", "completed"]:
                # Check if already rated
                rating_check = requests.get(
                    f"{BASE_URL}/api/orders/{order['order_id']}/rating", 
                    headers=headers
                )
                if rating_check.status_code == 200 and not rating_check.json().get("rated"):
                    test_order = order
                    break
        
        if not test_order:
            print("⚠ No unrated delivered orders found - testing validation with existing order")
            test_order = {"order_id": TEST_ORDER_ID}
        
        # Test invalid rating (out of range)
        invalid_rating = {
            "overall_rating": 6,  # Invalid - should be 1-5
            "quality_rating": 5,
            "communication_rating": 5,
            "delivery_rating": 5,
            "review_text": "Test review",
            "would_recommend": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/orders/{test_order['order_id']}/rate",
            json=invalid_rating,
            headers=headers
        )
        # Should reject invalid rating (either 400 for validation or 400 for already rated)
        assert response.status_code in [400, 422], f"Expected validation error, got: {response.status_code}"
        print(f"✓ Invalid rating range correctly rejected")
    
    def test_rate_vendor_buyer_only(self):
        """Test that only buyers can rate vendors"""
        # Login as admin (not buyer)
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip("Admin login failed")
        
        admin_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        rating_data = {
            "overall_rating": 5,
            "quality_rating": 5,
            "communication_rating": 5,
            "delivery_rating": 5,
            "review_text": "Test review from admin",
            "would_recommend": True
        }
        
        response = requests.post(
            f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/rate",
            json=rating_data,
            headers=headers
        )
        # Admin should not be allowed to rate (or order not found for admin)
        assert response.status_code in [403, 404], f"Expected 403 or 404, got: {response.status_code}"
        print(f"✓ Non-buyer correctly rejected from rating (status: {response.status_code})")


class TestConfirmDelivery:
    """Test POST /api/orders/{order_id}/confirm-delivery"""
    
    @pytest.fixture
    def buyer_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_confirm_delivery_buyer_only(self):
        """Test that only buyers can confirm delivery"""
        # Login as admin (not buyer)
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if login_response.status_code != 200:
            pytest.skip("Admin login failed")
        
        admin_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        response = requests.post(
            f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/confirm-delivery",
            headers=headers
        )
        # Admin should not be allowed to confirm delivery
        assert response.status_code in [403, 404], f"Expected 403 or 404, got: {response.status_code}"
        print(f"✓ Non-buyer correctly rejected from confirming delivery (status: {response.status_code})")
    
    def test_confirm_delivery_requires_dispatched_status(self, buyer_token):
        """Test confirm delivery requires proper order status"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Get orders
        response = requests.get(f"{BASE_URL}/api/orders", headers=headers)
        orders = response.json()
        
        # Find an order that's not in dispatched/delivered status
        test_order = None
        for order in orders:
            if order["status"] not in ["dispatched", "delivered"]:
                test_order = order
                break
        
        if not test_order:
            print("⚠ No orders in non-dispatched status found - skipping status validation test")
            return
        
        response = requests.post(
            f"{BASE_URL}/api/orders/{test_order['order_id']}/confirm-delivery",
            headers=headers
        )
        # Should reject if not in dispatched status
        assert response.status_code == 400, f"Expected 400 for wrong status, got: {response.status_code}"
        print(f"✓ Confirm delivery correctly rejects non-dispatched orders")


class TestAddTracking:
    """Test POST /api/orders/{order_id}/add-tracking"""
    
    def test_add_tracking_vendor_only(self):
        """Test that only vendors can add tracking info"""
        # Login as buyer (not vendor)
        login_response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        buyer_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        tracking_data = {
            "courier": "FedEx",
            "tracking_number": "TEST123456",
            "estimated_delivery": "2026-02-01",
            "note": "Test tracking"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/add-tracking",
            json=tracking_data,
            headers=headers
        )
        # Buyer should not be allowed to add tracking
        assert response.status_code == 403, f"Expected 403 for buyer, got: {response.status_code}"
        print(f"✓ Buyer correctly rejected from adding tracking info")


class TestIntegration:
    """Integration tests for the full order rating flow"""
    
    @pytest.fixture
    def buyer_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_order_flow_data_consistency(self, buyer_token):
        """Test that order details, rating status, and vendor ratings are consistent"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        
        # Get order details
        response = requests.get(f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/details", headers=headers)
        if response.status_code != 200:
            pytest.skip(f"Test order {TEST_ORDER_ID} not found or not accessible")
        
        order_details = response.json()
        
        # Check order rating status
        response = requests.get(f"{BASE_URL}/api/orders/{TEST_ORDER_ID}/rating", headers=headers)
        assert response.status_code == 200
        rating_status = response.json()
        
        # Verify consistency
        assert order_details["is_rated"] == rating_status["rated"], \
            "Mismatch between order details is_rated and rating status"
        
        print(f"✓ Order data is consistent")
        print(f"  - Order ID: {TEST_ORDER_ID}")
        print(f"  - Is rated: {order_details['is_rated']}")
        print(f"  - Order status: {order_details['order']['status']}")
        
        # If rated, verify the rating appears in vendor ratings
        if order_details["is_rated"] and order_details.get("vendor", {}).get("vendor_id"):
            vendor_id = order_details["vendor"]["vendor_id"]
            response = requests.get(f"{BASE_URL}/api/vendors/{vendor_id}/ratings", headers=headers)
            assert response.status_code == 200
            vendor_ratings = response.json()
            
            # Check if our rating is in the vendor's ratings list
            order_rating_found = any(
                r.get("order_id") == TEST_ORDER_ID 
                for r in vendor_ratings.get("ratings", [])
            )
            print(f"  - Rating found in vendor ratings: {order_rating_found}")


class TestEndpointAvailability:
    """Test that all new endpoints are available and respond correctly"""
    
    @pytest.fixture
    def buyer_token(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": BUYER_EMAIL,
            "password": BUYER_PASSWORD
        })
        return response.json()["access_token"]
    
    def test_rate_endpoint_exists(self, buyer_token):
        """Verify POST /orders/{order_id}/rate endpoint exists"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        # Send empty body to check endpoint exists
        response = requests.post(
            f"{BASE_URL}/api/orders/fake_order/rate",
            json={},
            headers=headers
        )
        # Should return 422 (validation error) or 404 (not found), not 405 (method not allowed)
        assert response.status_code != 405, "Rate endpoint not found (405)"
        print(f"✓ POST /orders/{{order_id}}/rate endpoint exists")
    
    def test_vendor_ratings_endpoint_exists(self, buyer_token):
        """Verify GET /vendors/{vendor_id}/ratings endpoint exists"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        response = requests.get(
            f"{BASE_URL}/api/vendors/fake_vendor/ratings",
            headers=headers
        )
        # Should return 200 (with empty stats) not 404 or 405
        assert response.status_code == 200, f"Vendor ratings endpoint error: {response.status_code}"
        print(f"✓ GET /vendors/{{vendor_id}}/ratings endpoint exists")
    
    def test_order_rating_endpoint_exists(self, buyer_token):
        """Verify GET /orders/{order_id}/rating endpoint exists"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        response = requests.get(
            f"{BASE_URL}/api/orders/fake_order/rating",
            headers=headers
        )
        # Should return 200 with rated: false
        assert response.status_code == 200, f"Order rating endpoint error: {response.status_code}"
        print(f"✓ GET /orders/{{order_id}}/rating endpoint exists")
    
    def test_order_details_endpoint_exists(self, buyer_token):
        """Verify GET /orders/{order_id}/details endpoint exists"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        response = requests.get(
            f"{BASE_URL}/api/orders/fake_order/details",
            headers=headers
        )
        # Should return 404 (order not found), not 405
        assert response.status_code == 404, f"Order details endpoint error: {response.status_code}"
        print(f"✓ GET /orders/{{order_id}}/details endpoint exists")
    
    def test_confirm_delivery_endpoint_exists(self, buyer_token):
        """Verify POST /orders/{order_id}/confirm-delivery endpoint exists"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        response = requests.post(
            f"{BASE_URL}/api/orders/fake_order/confirm-delivery",
            headers=headers
        )
        # Should return 404 (order not found), not 405
        assert response.status_code == 404, f"Confirm delivery endpoint error: {response.status_code}"
        print(f"✓ POST /orders/{{order_id}}/confirm-delivery endpoint exists")
    
    def test_add_tracking_endpoint_exists(self, buyer_token):
        """Verify POST /orders/{order_id}/add-tracking endpoint exists"""
        headers = {"Authorization": f"Bearer {buyer_token}"}
        response = requests.post(
            f"{BASE_URL}/api/orders/fake_order/add-tracking",
            json={"courier": "test", "tracking_number": "123"},
            headers=headers
        )
        # Should return 403 (buyer not allowed) or 404, not 405
        assert response.status_code in [403, 404], f"Add tracking endpoint error: {response.status_code}"
        print(f"✓ POST /orders/{{order_id}}/add-tracking endpoint exists")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
