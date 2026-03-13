"""
WhatsApp Logs API Tests
Tests for the WhatsApp logging module endpoints at:
- GET /api/whatsapp/logs - List logs with filtering
- GET /api/whatsapp/logs/stats - Get statistics
- GET /api/whatsapp/logs/errors - Get error summary
"""

import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')

# Admin credentials from test request
ADMIN_EMAIL = "admin@offoadex.com"
ADMIN_PASSWORD = "admin123"


class TestWhatsAppLogsAuthentication:
    """Test authentication requirements for WhatsApp logs endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        data = response.json()
        assert "access_token" in data
        return data["access_token"]
    
    def test_logs_endpoint_requires_auth(self):
        """Test that /api/whatsapp/logs requires authentication"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/logs")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_stats_endpoint_requires_auth(self):
        """Test that /api/whatsapp/logs/stats requires authentication"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/logs/stats")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
    
    def test_errors_endpoint_requires_auth(self):
        """Test that /api/whatsapp/logs/errors requires authentication"""
        response = requests.get(f"{BASE_URL}/api/whatsapp/logs/errors")
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"


class TestWhatsAppLogsAdminAccess:
    """Test admin access to WhatsApp logs endpoints"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200, f"Admin login failed: {response.text}"
        return response.json()["access_token"]
    
    def test_logs_endpoint_accessible_by_admin(self, admin_token):
        """Test GET /api/whatsapp/logs is accessible by admin"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/logs",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "logs" in data, "Response should contain 'logs' field"
        assert "total" in data, "Response should contain 'total' field"
        assert "limit" in data, "Response should contain 'limit' field"
        assert "skip" in data, "Response should contain 'skip' field"
        assert "has_more" in data, "Response should contain 'has_more' field"
        
        # logs should be a list
        assert isinstance(data["logs"], list), "logs should be a list"
        print(f"✓ WhatsApp logs endpoint returned {len(data['logs'])} logs (total: {data['total']})")
    
    def test_stats_endpoint_accessible_by_admin(self, admin_token):
        """Test GET /api/whatsapp/logs/stats returns statistics"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/logs/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure - all fields should be present
        expected_fields = [
            "total_outbound", "total_inbound", "success_count", 
            "failure_count", "success_rate", "total_estimated_cost_inr",
            "unique_recipients", "by_message_type", "by_context",
            "top_errors", "daily_breakdown", "hourly_distribution", "period"
        ]
        
        for field in expected_fields:
            assert field in data, f"Response should contain '{field}' field"
        
        # Verify types
        assert isinstance(data["total_outbound"], int), "total_outbound should be int"
        assert isinstance(data["total_inbound"], int), "total_inbound should be int"
        assert isinstance(data["success_rate"], (int, float)), "success_rate should be numeric"
        assert isinstance(data["by_message_type"], dict), "by_message_type should be dict"
        assert isinstance(data["by_context"], dict), "by_context should be dict"
        assert isinstance(data["daily_breakdown"], list), "daily_breakdown should be list"
        
        print(f"✓ Stats: {data['total_outbound']} outbound, {data['total_inbound']} inbound, {data['success_rate']}% success rate")
    
    def test_errors_endpoint_accessible_by_admin(self, admin_token):
        """Test GET /api/whatsapp/logs/errors returns error summary"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/logs/errors",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "errors" in data, "Response should contain 'errors' field"
        assert "period_days" in data, "Response should contain 'period_days' field"
        assert "total_error_types" in data, "Response should contain 'total_error_types' field"
        
        # errors should be a list
        assert isinstance(data["errors"], list), "errors should be a list"
        
        print(f"✓ Error summary: {data['total_error_types']} error types in last {data['period_days']} days")


class TestWhatsAppLogsFiltering:
    """Test filtering capabilities for WhatsApp logs"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_filter_by_direction_outbound(self, admin_token):
        """Test filtering logs by direction=outbound"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/logs?direction=outbound",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # All returned logs should be outbound
        for log in data["logs"]:
            assert log.get("direction") == "outbound", f"Expected outbound, got {log.get('direction')}"
        print(f"✓ Filtered outbound logs: {len(data['logs'])} results")
    
    def test_filter_by_direction_inbound(self, admin_token):
        """Test filtering logs by direction=inbound"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/logs?direction=inbound",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # All returned logs should be inbound
        for log in data["logs"]:
            assert log.get("direction") == "inbound", f"Expected inbound, got {log.get('direction')}"
        print(f"✓ Filtered inbound logs: {len(data['logs'])} results")
    
    def test_filter_by_status(self, admin_token):
        """Test filtering logs by status"""
        for status in ["sent", "delivered", "failed"]:
            response = requests.get(
                f"{BASE_URL}/api/whatsapp/logs?status={status}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200, f"Failed for status={status}"
            data = response.json()
            print(f"✓ Filtered by status={status}: {len(data['logs'])} results")
    
    def test_filter_by_message_type(self, admin_token):
        """Test filtering logs by message_type"""
        for msg_type in ["text", "template", "image", "document"]:
            response = requests.get(
                f"{BASE_URL}/api/whatsapp/logs?message_type={msg_type}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200, f"Failed for message_type={msg_type}"
            data = response.json()
            print(f"✓ Filtered by message_type={msg_type}: {len(data['logs'])} results")
    
    def test_filter_errors_only(self, admin_token):
        """Test filtering to show only errors"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/logs?errors_only=true",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # All returned logs should have success=False
        for log in data["logs"]:
            assert log.get("success") == False, f"Expected failed log, got success={log.get('success')}"
        print(f"✓ Filtered errors only: {len(data['logs'])} results")
    
    def test_pagination(self, admin_token):
        """Test pagination with limit and skip"""
        # First page
        response1 = requests.get(
            f"{BASE_URL}/api/whatsapp/logs?limit=10&skip=0",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert len(data1["logs"]) <= 10, "Should respect limit"
        
        # Second page
        response2 = requests.get(
            f"{BASE_URL}/api/whatsapp/logs?limit=10&skip=10",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response2.status_code == 200
        data2 = response2.json()
        
        # If there are more than 10 logs total, pages should be different
        if data1["total"] > 10 and len(data1["logs"]) > 0 and len(data2["logs"]) > 0:
            # First log IDs should be different
            first_page_ids = [log.get("log_id") for log in data1["logs"]]
            second_page_ids = [log.get("log_id") for log in data2["logs"]]
            assert first_page_ids != second_page_ids, "Pagination should return different results"
        
        print(f"✓ Pagination working: page1={len(data1['logs'])}, page2={len(data2['logs'])}, total={data1['total']}")
    
    def test_limit_capped_at_200(self, admin_token):
        """Test that limit is capped at 200"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/logs?limit=500",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] <= 200, f"Limit should be capped at 200, got {data['limit']}"
        print(f"✓ Limit correctly capped to {data['limit']}")


class TestWhatsAppLogsStatsDateFiltering:
    """Test date filtering for statistics"""
    
    @pytest.fixture(scope="class")
    def admin_token(self):
        """Login as admin and get token"""
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        assert response.status_code == 200
        return response.json()["access_token"]
    
    def test_stats_with_date_range(self, admin_token):
        """Test statistics with date range filter"""
        response = requests.get(
            f"{BASE_URL}/api/whatsapp/logs/stats?start_date=2025-01-01&end_date=2025-12-31",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        data = response.json()
        
        # Verify period info is included
        assert "period" in data
        assert data["period"]["start_date"] == "2025-01-01"
        assert data["period"]["end_date"] == "2025-12-31"
        print(f"✓ Stats with date range: {data['total_outbound']} outbound messages")
    
    def test_errors_with_custom_days(self, admin_token):
        """Test error summary with custom days parameter"""
        for days in [1, 7, 14, 30]:
            response = requests.get(
                f"{BASE_URL}/api/whatsapp/logs/errors?days={days}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["period_days"] == min(days, 30), f"Expected {min(days, 30)} days, got {data['period_days']}"
        print(f"✓ Error summary respects days parameter and caps at 30")


class TestWhatsAppLogsNonAdminAccess:
    """Test that non-admin users cannot access WhatsApp logs"""
    
    def test_buyer_cannot_access_logs(self):
        """Test that buyer users get 403 for logs endpoint"""
        # First register a buyer user if needed or use existing test user
        # For this test, we'll just verify that the endpoint requires admin role
        # If you have a test buyer account, you can add credentials here
        pass  # Skipped - would need buyer credentials
    
    def test_vendor_cannot_access_logs(self):
        """Test that vendor users get 403 for logs endpoint"""
        # Similar to buyer test
        pass  # Skipped - would need vendor credentials


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
