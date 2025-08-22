import requests

def test_subscriptions_api():
    # Your API access key (replace with your actual key)
    api_key = "80d06c01ec7f96ba3fcf22493acdccd0e899d2f87767c80e1bc46acaa0887eec"
    
    # Set up headers with API key
    headers = {
        "Hydrus-Client-API-Access-Key": api_key
    }
    
    try:
        # Make GET request to the subscriptions endpoint
        # The endpoint is registered directly under manage_subscriptions/get_subscriptions
        response = requests.get(
            'http://127.0.0.1:45869/manage_subscriptions/get_subscriptions',
            headers=headers
        )
        
        # Print status code and raw response
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the Hydrus client. Make sure it's running and the API is enabled.")
    except Exception as e:
        print(f"Error: An unexpected error occurred: {str(e)}")

if __name__ == '__main__':
    test_subscriptions_api()
