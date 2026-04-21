import requests

try:
    response = requests.get('http://localhost:8000/')
    print(f"Status code: {response.status_code}")
    if response.status_code == 200:
        print("Server is running!")
    else:
        print(f"Server returned status code: {response.status_code}")
except Exception as e:
    print(f"Error connecting to server: {e}") 