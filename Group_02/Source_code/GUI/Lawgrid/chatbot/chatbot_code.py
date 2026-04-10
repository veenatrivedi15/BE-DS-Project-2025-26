# chatbot_code.py
import os, json, requests
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file. Please set it.")

GEMINI_TEXT_MODEL = "gemini-2.5-flash-preview-05-20"
GEMINI_TTS_MODEL = "gemini-2.5-flash-preview-tts"
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

DISCLAIMER_TEXT = """

"""

# --- Helper ---
def make_gemini_api_call(url, payload, max_retries=5, base_delay=2):
    import time
    retries = 0
    while retries < max_retries:
        try:
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:  # Too Many Requests
                delay = base_delay * (2 ** retries)
                print(f"Rate limit hit. Retrying in {delay}s... (Attempt {retries+1}/{max_retries})")
                time.sleep(delay)
                retries += 1
            else:
                raise
        except requests.exceptions.RequestException as e:
            delay = base_delay * (2 ** retries)
            print(f"Request failed: {e}, retrying in {delay}s... (Attempt {retries+1}/{max_retries})")
            time.sleep(delay)
            retries += 1
    raise Exception("Max retries exceeded for API call.")

# --- Chatbot Functions ---
def get_chatbot_response(user_message: str) -> str:
    prompt = f"""Act as an AI legal information assistant. Provide a concise summary of the legal topic in 3-5 bullet points. 
For each point, **bold the key term** followed by its explanation. Do NOT include any disclaimer in your response; 
it will be added by the system.

User query: {user_message}"""

    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    url = f"{GEMINI_API_BASE_URL}/{GEMINI_TEXT_MODEL}:generateContent?key={GEMINI_API_KEY}"

    result = make_gemini_api_call(url, payload)
    if result and result.get('candidates'):
        text = result['candidates'][0]['content']['parts'][0]['text']
    else:
        text = "Sorry, I could not get a response from the AI."

    return text + DISCLAIMER_TEXT


def get_tts_audio(text_to_speak: str):
    payload = {
        "contents": [{"parts": [{"text": text_to_speak}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Kore"}}}
        },
        "model": GEMINI_TTS_MODEL
    }
    url = f"{GEMINI_API_BASE_URL}/{GEMINI_TTS_MODEL}:generateContent?key={GEMINI_API_KEY}"
    result = make_gemini_api_call(url, payload)

    if result and result.get('candidates'):
        inline_data = result['candidates'][0]['content']['parts'][0].get('inlineData')
        if inline_data:
            return inline_data.get('data'), inline_data.get('mimeType')
    return None, None
