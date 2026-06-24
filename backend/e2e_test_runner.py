"""
E2E Test Runner - Comprehensive End-to-End Testing
Tests all major features before production deployment
"""

import requests
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Load .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env.development'
if env_path.exists():
    load_dotenv(env_path)
else:
    load_dotenv()

# Configuration
API_BASE_URL = "http://localhost:5001"
TEST_EMAIL = "test@tradosphere.com"
TEST_PASSWORD = "Test@2024"

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

class E2ETester:
    """Comprehensive E2E test suite"""
    
    def __init__(self):
        self.results = []
        self.token = None
        self.user_id = None
        
    def log_test(self, status, message):
        """Log test result"""
        symbol = "✅" if status else "❌"
        color = GREEN if status else RED
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{color}{symbol} {timestamp} {message}{RESET}")
        self.results.append((status, message))
    
    def test_server_health(self):
        """Test 1: Server health check"""
        print(f"\n{BLUE}═══ TEST 1: SERVER HEALTH CHECK ═══{RESET}")
        try:
            response = requests.get(f"{API_BASE_URL}/api/health", timeout=5)
            if response.status_code == 200:
                self.log_test(True, "Server is running")
                data = response.json()
                status = data.get("status")
                if status in ["operational", "healthy"]:
                    self.log_test(True, f"Server status: {status}")
                else:
                    self.log_test(False, f"Server status: {status}")
            else:
                self.log_test(False, f"Server returned {response.status_code}")
        except Exception as e:
            self.log_test(False, f"Server health check failed: {e}")
    
    def test_status_endpoint(self):
        """Test 2: API Status endpoint"""
        print(f"\n{BLUE}═══ TEST 2: API STATUS ═══{RESET}")
        try:
            response = requests.get(f"{API_BASE_URL}/api/status", timeout=5)
            if response.status_code == 200:
                self.log_test(True, "Status endpoint responding")
                data = response.json()
                self.log_test(True, f"Service: {data.get('data', {}).get('service', 'N/A')}")
            else:
                self.log_test(False, f"Status endpoint returned {response.status_code}")
        except Exception as e:
            self.log_test(False, f"Status check failed: {e}")
    
    def test_user_signup(self):
        """Test 3: User registration"""
        print(f"\n{BLUE}═══ TEST 3: USER REGISTRATION ═══{RESET}")
        try:
            payload = {
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "username": "testuser"
            }
            response = requests.post(
                f"{API_BASE_URL}/api/auth/signup",
                json=payload,
                timeout=5
            )
            
            if response.status_code in [201, 200]:
                self.log_test(True, "User signup successful")
                data = response.json()
                if data.get("status") == "success":
                    self.log_test(True, "Signup response valid")
            elif response.status_code == 409:
                self.log_test(True, "User already exists (expected)")
            else:
                self.log_test(False, f"Signup returned {response.status_code}")
                
        except Exception as e:
            self.log_test(False, f"User signup failed: {e}")
    
    def test_user_login(self):
        """Test 4: User login"""
        print(f"\n{BLUE}═══ TEST 4: USER LOGIN ═══{RESET}")
        try:
            payload = {
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
            response = requests.post(
                f"{API_BASE_URL}/api/auth/login",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                self.log_test(True, "User login successful")
                data = response.json()
                if "data" in data and "access_token" in data["data"]:
                    self.token = data["data"]["access_token"]
                    self.log_test(True, "JWT token received")
                else:
                    self.log_test(False, "Token not in response")
            else:
                self.log_test(False, f"Login returned {response.status_code}")
                
        except Exception as e:
            self.log_test(False, f"User login failed: {e}")
    
    def test_market_data(self):
        """Test 5: Market data endpoints"""
        print(f"\n{BLUE}═══ TEST 5: MARKET DATA ═══{RESET}")
        
        if not self.token:
            self.log_test(False, "No token available for market data test")
            return
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            # Test live prices
            response = requests.get(
                f"{API_BASE_URL}/api/market/live",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                self.log_test(True, "Market live prices endpoint working")
                data = response.json()
                if "data" in data:
                    self.log_test(True, f"Received market data")
            else:
                self.log_test(False, f"Market data returned {response.status_code}")
                
        except Exception as e:
            self.log_test(False, f"Market data test failed: {e}")
    
    def test_signals(self):
        """Test 6: Signal generation"""
        print(f"\n{BLUE}═══ TEST 6: SIGNAL GENERATION ═══{RESET}")
        
        if not self.token:
            self.log_test(False, "No token available for signals test")
            return
        
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/signals",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                self.log_test(True, "Signals endpoint working")
                data = response.json()
                if "data" in data and "signals" in data["data"]:
                    signals = data["data"]["signals"]
                    if signals:
                        signal = signals[0]
                        self.log_test(True, f"Generated {signal.get('signal', 'HOLD')} signal")
                        if "confidence" in signal:
                            self.log_test(True, f"Confidence: {signal['confidence']}%")
            else:
                self.log_test(False, f"Signals returned {response.status_code}")
                
        except Exception as e:
            self.log_test(False, f"Signals test failed: {e}")
    
    def test_error_handling(self):
        """Test 7: Error handling"""
        print(f"\n{BLUE}═══ TEST 7: ERROR HANDLING ═══{RESET}")
        
        # Test 404
        try:
            response = requests.get(f"{API_BASE_URL}/api/nonexistent", timeout=5)
            if response.status_code == 404:
                self.log_test(True, "404 error handling working")
            else:
                self.log_test(False, f"Expected 404, got {response.status_code}")
        except Exception as e:
            self.log_test(False, f"404 test failed: {e}")
        
        # Test 401
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/signals",
                headers={"Authorization": "Bearer invalid"},
                timeout=5
            )
            if response.status_code == 401:
                self.log_test(True, "401 authentication error handling working")
            else:
                self.log_test(False, f"Expected 401, got {response.status_code}")
        except Exception as e:
            self.log_test(False, f"401 test failed: {e}")
    
    def test_logging(self):
        """Test 8: Logging system"""
        print(f"\n{BLUE}═══ TEST 8: LOGGING SYSTEM ═══{RESET}")
        
        from pathlib import Path
        import os
        
        # Check if logs directory exists
        logs_dir = Path("logs")
        if logs_dir.exists():
            self.log_test(True, "Logs directory exists")
            
            # Check if log files exist
            log_files = list(logs_dir.glob("*.log"))
            if log_files:
                self.log_test(True, f"Log files present ({len(log_files)} files)")
            else:
                self.log_test(False, "No log files found")
        else:
            self.log_test(False, "Logs directory not found")
    
    def test_database(self):
        """Test 9: Database connectivity"""
        print(f"\n{BLUE}═══ TEST 9: DATABASE ═══{RESET}")

        try:
            import sqlite3
            from pathlib import Path

            # Try multiple possible database locations
            possible_locations = [
                Path(__file__).parent / "tradosphere_dev.db",  # backend/tradosphere_dev.db
                Path(__file__).parent.parent / "tradosphere_dev.db",  # root/tradosphere_dev.db
                Path(__file__).parent.parent / "instance" / "tradosphere_dev.db"  # instance/tradosphere_dev.db
            ]

            db_file = None
            tables_found = 0

            for location in possible_locations:
                if location.exists():
                    try:
                        conn = sqlite3.connect(str(location))
                        cursor = conn.cursor()
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                        tables = cursor.fetchall()
                        conn.close()

                        if len(tables) > 0:
                            db_file = location
                            tables_found = len(tables)
                            break
                    except:
                        continue

            if db_file:
                self.log_test(True, f"Database file exists: {db_file.name}")
                self.log_test(True, f"Database connected ({tables_found} tables)")
            else:
                self.log_test(False, "Database file not found or has no tables")

        except Exception as e:
            self.log_test(False, f"Database test failed: {e}")
    
    def test_dependencies(self):
        """Test 10: Critical dependencies"""
        print(f"\n{BLUE}═══ TEST 10: DEPENDENCIES ═══{RESET}")
        
        dependencies = [
            "flask",
            "sqlalchemy",
            "jwt",
            "scipy",
            "anthropic",
            "sentry_sdk",
            "colorlog"
        ]
        
        for dep in dependencies:
            try:
                __import__(dep.replace("-", "_"))
                self.log_test(True, f"{dep} installed")
            except ImportError:
                self.log_test(False, f"{dep} not installed")
    
    def run_all_tests(self):
        """Run all tests"""
        print(f"\n{BLUE}╔════════════════════════════════════════════════════════════════╗{RESET}")
        print(f"{BLUE}║     🧪 COMPREHENSIVE E2E TEST SUITE - TRADOSPHERE V3.1 🧪        ║{RESET}")
        print(f"{BLUE}╚════════════════════════════════════════════════════════════════╝{RESET}")
        
        print(f"\n{YELLOW}Starting tests at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
        print(f"{YELLOW}API Base URL: {API_BASE_URL}{RESET}\n")
        
        # Run all tests
        self.test_dependencies()
        self.test_server_health()
        self.test_status_endpoint()
        self.test_logging()
        self.test_database()
        self.test_user_signup()
        self.test_user_login()
        self.test_market_data()
        self.test_signals()
        self.test_error_handling()
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print(f"\n{BLUE}╔════════════════════════════════════════════════════════════════╗{RESET}")
        print(f"{BLUE}║                    📊 TEST SUMMARY 📊                            ║{RESET}")
        print(f"{BLUE}╚════════════════════════════════════════════════════════════════╝{RESET}\n")
        
        passed = sum(1 for status, _ in self.results if status)
        total = len(self.results)
        
        print(f"Total Tests: {total}")
        print(f"{GREEN}Passed: {passed}{RESET}")
        print(f"{RED}Failed: {total - passed}{RESET}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        if passed == total:
            print(f"\n{GREEN}✅ ALL TESTS PASSED - READY FOR DEPLOYMENT! 🚀{RESET}")
        else:
            print(f"\n{RED}❌ SOME TESTS FAILED - FIX ISSUES BEFORE DEPLOYMENT{RESET}")
        
        print(f"\n{BLUE}Completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}\n")

if __name__ == "__main__":
    tester = E2ETester()
    tester.run_all_tests()
