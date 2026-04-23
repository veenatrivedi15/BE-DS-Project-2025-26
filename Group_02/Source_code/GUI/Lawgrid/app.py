# app.py
from flask import Flask, request, jsonify, send_from_directory, render_template, Response
from flask_cors import CORS
import os
import re
import docx2txt
import pdfplumber
import pytesseract
from PIL import Image
from datetime import datetime
import sqlite3
import csv
import io

# Import chatbot logic
from chatbot.chatbot_code import get_chatbot_response, get_tts_audio

# ---------------------- APP SETUP ----------------------
app = Flask(__name__)
CORS(app)

# ---------------------- FILE UPLOAD CONFIG ----------------------
UPLOAD_FOLDER = 'uploaded_documents'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---------------------- DATABASE CONFIG ----------------------
DATABASE = 'database.db'

def init_db():
    """Initializes the SQLite database and creates the events table."""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY,
                date TEXT NOT NULL,
                event TEXT NOT NULL,
                source_doc TEXT NOT NULL
            )
        ''')
        conn.commit()

# Initialize database
init_db()

# ---------------------- TEXT EXTRACTION ----------------------
def extract_text(file_path, file_extension):
    """Extract text from file based on extension."""
    try:
        if file_extension == '.docx':
            return docx2txt.process(file_path)
        elif file_extension == '.pdf':
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        elif file_extension in ['.jpg', '.jpeg', '.png']:
            return pytesseract.image_to_string(Image.open(file_path))
        elif file_extension == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        return None
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return None

# ---------------------- EVENT EXTRACTION ----------------------
def find_dates_and_events(text):
    """Finds date and event pairs from text."""
    found_events = []
    date_patterns = [
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        r'(\d{1,2}[/]\d{1,2}[/]\d{2,4})',
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s*\d{4})?)',
    ]
    lines = text.split('\n')
    for i, line in enumerate(lines):
        for pattern in date_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                try:
                    dt_obj = None
                    for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%m/%d/%y', '%B %d, %Y', '%b %d, %Y']:
                        try:
                            cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
                            dt_obj = datetime.strptime(cleaned, fmt)
                            break
                        except ValueError:
                            continue
                    if dt_obj:
                        standard_date = dt_obj.strftime('%Y-%m-%d')
                        event_desc = line.strip()
                        if i + 1 < len(lines):
                            next_line = lines[i + 1].strip()
                            is_next_date = any(re.search(p, next_line, re.IGNORECASE) for p in date_patterns)
                            if next_line and not is_next_date:
                                event_desc += " " + next_line
                        found_events.append((standard_date, event_desc))
                        break
                except Exception:
                    continue
    return found_events

def store_events(events, source_doc):
    """Store events in DB."""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        for date, event in events:
            cursor.execute('SELECT id FROM events WHERE date=? AND event=? AND source_doc=?', (date, event, source_doc))
            if cursor.fetchone() is None:
                cursor.execute('INSERT INTO events (date, event, source_doc) VALUES (?, ?, ?)', (date, event, source_doc))
        conn.commit()

# ---------------------- ROUTES ----------------------

# ----- Home and Feature Pages -----
@app.route('/')
def home():
    """Main homepage route."""
    return render_template('index.html')

@app.route('/contract_draft')
def contract_draft():
    """Route for Contract Drafting feature."""
    return render_template('contract_draft.html')

@app.route('/chatbot')
def chatbot_page():
    """Renders chatbot page."""
    return render_template('chatbot.html')


# ----- File Upload Feature -----
@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles file upload, text extraction, and storing events."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    text = extract_text(file_path, ext)
    if text is None:
        os.remove(file_path)
        return jsonify({'error': f'Failed to extract text from {ext}'}), 400

    events = find_dates_and_events(text)
    if events:
        store_events(events, filename)
        msg = f'Processed "{filename}" and stored {len(events)} events.'
    else:
        msg = f'Processed "{filename}", but found no events.'
    return jsonify({'message': msg}), 200


@app.route('/schedule', methods=['GET'])
def get_schedule():
    """Return all events, split into upcoming and past."""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT date, event, source_doc FROM events ORDER BY date')
        rows = cursor.fetchall()

    today = datetime.now().strftime('%Y-%m-%d')
    upcoming = []
    past = []
    for d, e, s in rows:
        item = {'date': d, 'event': e, 'source_doc': s}
        if d >= today:
            upcoming.append(item)
        else:
            past.append(item)
    return jsonify({'upcoming_schedule': upcoming, 'past_schedule': past}), 200


@app.route('/get_files', methods=['GET'])
def get_files():
    """List uploaded files."""
    files = [f for f in os.listdir(UPLOAD_FOLDER) if os.path.isfile(os.path.join(UPLOAD_FOLDER, f))]
    return jsonify({'files': [{'filename': f} for f in files]}), 200


@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete a file and its events."""
    path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM events WHERE source_doc=?', (filename,))
            conn.commit()
        return jsonify({'message': f'{filename} deleted successfully'}), 200
    return jsonify({'error': f'{filename} not found'}), 404


@app.route('/download', methods=['GET'])
def download_schedule():
    """Download upcoming events as CSV."""
    today = datetime.now().strftime('%Y-%m-%d')
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT date, event, source_doc FROM events WHERE date >= ? ORDER BY date', (today,))
        data = cursor.fetchall()
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Date', 'Event', 'Source Document'])
    cw.writerows(data)
    output = Response(si.getvalue(), mimetype='text/csv')
    output.headers['Content-Disposition'] = 'attachment; filename=upcoming_schedule.csv'
    return output


# ----- Chatbot and Text-to-Speech -----
@app.route('/chat', methods=['POST'])
def chat():
    """Chatbot response endpoint."""
    user_msg = request.json.get('message', '').lower()
    if not user_msg:
        return jsonify({"error": "No message provided"}), 400
    try:
        ai_resp = get_chatbot_response(user_msg)
        return jsonify({"response": ai_resp})
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({"error": "Chat processing failed"}), 500


@app.route('/tts', methods=['POST'])
def tts():
    """Text-to-speech endpoint."""
    text_to_speak = request.json.get('text')
    if not text_to_speak:
        return jsonify({"error": "No text provided"}), 400
    try:
        audio_data, mime_type = get_tts_audio(text_to_speak)
        if audio_data and mime_type and mime_type.startswith("audio/"):
            return jsonify({"audioData": audio_data, "mimeType": mime_type})
        return jsonify({"error": "Audio generation failed"}), 500
    except Exception as e:
        print(f"Error in TTS endpoint: {e}")
        return jsonify({"error": "An error occurred generating audio"}), 500


# ---------------------- MAIN ENTRY ----------------------
if __name__ == '__main__':
    if not os.path.exists('templates'):
        os.makedirs('templates')
    app.run(debug=True, port=5000)
