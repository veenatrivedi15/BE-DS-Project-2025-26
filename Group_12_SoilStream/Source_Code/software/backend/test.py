import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash')
response = model.generate_content("Provide farming recommendations for coconut: water needs, soil type, fertilizer, climate, care tips.")
print(response.text)