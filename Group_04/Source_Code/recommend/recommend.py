import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from groq import Groq
import requests
from deep_translator import GoogleTranslator

load_dotenv()

app = Flask(__name__)

# Configure Groq API
client = Groq(
    api_key=os.getenv("GROQ_API_KEY"),
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message')
    target_language = data.get('language', 'en')
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an eye-care assistant. You give general advice only. You are NOT a doctor. You must ALWAYS include a disclaimer: 'This chatbot does not provide medical diagnosis.' at the end of your response. If symptoms seem serious, suggest visiting an eye specialist."
                },
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
            model="llama-3.3-70b-versatile",
        )
        bot_reply = chat_completion.choices[0].message.content
        
        # Translate response if target language is not English
        if target_language != 'en':
            try:
                bot_reply = GoogleTranslator(source='auto', target=target_language).translate(bot_reply)
            except Exception as trans_e:
                print(f"Translation Error: {trans_e}")
                # Fallback to English but append a note? Or just leave it as is.
                pass
        
        # Check for trigger phrases to suggest finding a clinic
        trigger_phrases = ["consult an eye specialist", "find a nearby clinic", "see a doctor", "visit an eye specialist", "ophthalmologist"]
        should_search = any(phrase in bot_reply.lower() for phrase in trigger_phrases)

        return jsonify({'response': bot_reply, 'should_search': should_search})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/search_clinics', methods=['POST'])
def search_clinics():
    location = request.json.get('location')  # Can be "City, State" or "lat,long"
    if not location:
        return jsonify({'error': 'No location provided'}), 400

    api_key = os.getenv("GOMAPS_API_KEY")
    if not api_key:
        return jsonify({'error': 'GOMAPS_API_KEY is not configured'}), 500

    try:
        parts = location.split(',')
        lat = float(parts[0].strip())
        lng = float(parts[1].strip())
    except (ValueError, IndexError):
        return jsonify({'error': 'Invalid location format. Expected "lat,lng"'}), 400

    try:
        params = {
            "location": f"{lat},{lng}",
            "radius": 5000,
            "keyword": "eye specialist ophthalmologist optometrist",
            "type": "hospital",
            "key": api_key,
        }

        response = requests.get(
            "https://maps.gomaps.pro/maps/api/place/nearbysearch/json",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") not in {"OK", "ZERO_RESULTS"}:
            return jsonify({'error': payload.get('error_message') or payload.get('status', 'Unknown map API error')}), 502

        local_results = payload.get("results", [])
        
        clinics = []
        for result in local_results:
            geometry = result.get("geometry", {})
            coords = geometry.get("location", {})
            clinics.append({
                "name": result.get("name"),
                "address": result.get("vicinity"),
                "rating": result.get("rating"),
                "latitude": coords.get("lat"),
                "longitude": coords.get("lng")
            })
            
        return jsonify({'clinics': clinics})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
