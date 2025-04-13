import subprocess  
import time  
import requests  
import sys  
import signal  
  
# Define the base URL for the API  
BASE_URL = "http://127.0.0.1:5000"  
  
# Start the Flask application as a subprocess  
def start_service():  
    service_process = subprocess.Popen([sys.executable, 'app.py'])  
    print("Starting Flask service...")  
    time.sleep(3)  # Wait for service to start  
    return service_process  
  
# Stop the Flask service gracefully  
def stop_service(service_process):  
    print("\nStopping Flask service...")  
    service_process.send_signal(signal.SIGINT)  
    service_process.wait()  
  
# Helper function to print test results  
def print_result(endpoint, success, response=None):  
    if success:  
        print(f"[PASS] {endpoint}")  
    else:  
        print(f"[FAIL] {endpoint}")  
        if response:  
            print(f"   Status Code: {response.status_code}")  
            print(f"   Response: {response.text}")  
  
# Test endpoints  
def test_customers():  
    endpoint = "/customers"  
    response = requests.get(BASE_URL + endpoint)  
    print(response.json())  # Print the response for debugging  
    success = response.status_code == 200 and isinstance(response.json(), list)  
    print_result(endpoint, success, response)  
  
def test_get_customer(customer_id):  
    endpoint = f"/customer/{customer_id}"  
    response = requests.get(BASE_URL + endpoint)  
    success = response.status_code == 200 and "customer_id" in response.json()  
    print_result(endpoint, success, response)  
  
def test_get_subscription(subscription_id):  
    endpoint = f"/subscription/{subscription_id}"  
    response = requests.get(BASE_URL + endpoint)  
    success = response.status_code == 200 and "subscription_id" in response.json()  
    print_result(endpoint, success, response)  
  
def test_promotions():  
    endpoint = "/promotions"  
    response = requests.get(BASE_URL + endpoint)  
    success = response.status_code == 200 and isinstance(response.json(), list)  
    print_result(endpoint, success, response)  
  
def test_kb_search(query):  
    endpoint = f"/kb/search?query={query}"  
    response = requests.get(BASE_URL + endpoint)  
    print(response.json())  # Print the response for debugging  
    success = response.status_code == 200 and isinstance(response.json(), list)  
    print_result(endpoint, success, response)  
  
def test_security_logs(customer_id):  
    endpoint = f"/customer/{customer_id}/security_logs"  
    response = requests.get(BASE_URL + endpoint)  
    success = response.status_code == 200 and isinstance(response.json(), list)  
    print_result(endpoint, success, response)  
  
def test_orders(customer_id):  
    endpoint = f"/customer/{customer_id}/orders"  
    response = requests.get(BASE_URL + endpoint)  
    success = response.status_code == 200 and isinstance(response.json(), list)  
    print_result(endpoint, success, response)  
  
# Main test runner  
def run_tests():  
    service_process = start_service()  
    try:  
        print("\nRunning test cases...\n")  
        test_customers()  
        test_get_customer(101)        # Replace with valid customer_id  
        test_get_customer(99999)      # Invalid customer_id to test error handling  
        test_get_subscription(1)      # Replace with valid subscription_id  
        test_promotions()  
        test_kb_search("Invoice Adjustment")  # Sample KB search query  
        test_security_logs(1)         # Replace with valid customer_id  
        test_orders(1)                # Replace with valid customer_id  
    except requests.exceptions.ConnectionError as e:  
        print("Connection error. Is the service running?")  
        print(e)  
    finally:  
        stop_service(service_process)  
  
if __name__ == "__main__":  
    run_tests()  