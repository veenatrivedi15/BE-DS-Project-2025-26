import requests 
r=requests.post(\" "http://127.0.0.1:5000/api/chatbot\, json={\message\:\hello\}) 
print(r.status_code) ; echo print(r.text) ; venv310\Scripts\python.exe test_chatbot.py
