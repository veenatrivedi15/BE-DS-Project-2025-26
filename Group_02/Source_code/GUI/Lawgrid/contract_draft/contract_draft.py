from flask import Flask, request, jsonify, send_from_directory, Response
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

app = Flask(__name__)
CORS(app)

# This will create a directory for uploads if it doesn't exist
UPLOAD_FOLDER = 'uploaded_documents'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database setup
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

# Initialize the database when the app starts
init_db()

def extract_text(file_path, file_extension):
    """
    Extracts text from a given file path based on its extension.
    Supports .docx, .pdf, image formats (.jpg, .jpeg, .png), and .txt.
    """
    try:
        if file_extension in ['.docx']:
            # Uses docx2txt for .docx files
            return docx2txt.process(file_path)
        elif file_extension in ['.pdf']:
            # Uses pdfplumber for .pdf files
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
            return text
        elif file_extension in ['.jpg', '.jpeg', '.png']:
            # Uses Tesseract (OCR) for images
            return pytesseract.image_to_string(Image.open(file_path))
        elif file_extension in ['.txt']:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return None
    except Exception as e:
        print(f"Error extracting text from {file_path}: {e}")
        return None

def find_dates_and_events(text):
    """
    Parses text to find date and event pairs.
    It looks for common date formats and captures the surrounding text as the event.
    Returns a list of tuples: [('YYYY-MM-DD', 'Event Description')]
    """
    found_events = []
    
    # Combined regex to find various date formats (DD/MM/YYYY, YYYY-MM-DD, Month Day, Year, etc.)
    # We will prioritize capturing the event text immediately following or preceding the date.
    date_patterns = [
        # YYYY-MM-DD or YYYY/MM/DD
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
        # MM/DD/YYYY or M/D/YY
        r'(\d{1,2}[/]\d{1,2}[/]\d{2,4})',
        # Month Day, Year (e.g., January 15, 2024)
        r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s*\d{4})?)',
    ]

    # Pre-processing to standardize dates to YYYY-MM-DD and capture event context
    # This is a simplified approach, a more robust solution would involve NLP.
    
    lines = text.split('\n')
    for i, line in enumerate(lines):
        # Look for a date pattern in the line
        for pattern in date_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                date_string = match.group(1).strip()
                
                # Simple attempt to convert date string to a standardized format
                try:
                    # Try to parse common formats
                    dt_obj = None
                    formats = ['%Y-%m-%d', '%Y/%m/%d', '%m/%d/%Y', '%m/%d/%y', '%B %d, %Y', '%b %d, %Y']
                    
                    for fmt in formats:
                        try:
                            # Handle cases with st/nd/rd/th (remove them before parsing)
                            cleaned_date_string = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_string, flags=re.IGNORECASE)
                            dt_obj = datetime.strptime(cleaned_date_string, fmt)
                            break
                        except ValueError:
                            continue
                    
                    if dt_obj:
                        standard_date = dt_obj.strftime('%Y-%m-%d')
                        
                        # Use the entire line as the event description
                        event_desc = line.strip()
                        
                        # Check the next line for continuation of the event
                        if i + 1 < len(lines):
                            next_line = lines[i+1].strip()
                            # If the next line is not empty and doesn't contain a date itself, append it
                            is_next_line_date = any(re.search(p, next_line, re.IGNORECASE) for p in date_patterns)
                            if next_line and not is_next_line_date:
                                event_desc += " " + next_line
                        
                        found_events.append((standard_date, event_desc))
                        # Stop searching other patterns once a match is found in the line
                        break
                except Exception as date_e:
                    # Ignore date parsing errors and continue
                    # print(f"Could not parse date '{date_string}': {date_e}")
                    continue
                    
    return found_events

def store_events(events, source_doc):
    """Stores a list of events into the database."""
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        for date, event in events:
            # Check if the event already exists to prevent duplicates
            cursor.execute('SELECT id FROM events WHERE date = ? AND event = ? AND source_doc = ?', 
                           (date, event, source_doc))
            if cursor.fetchone() is None:
                cursor.execute('INSERT INTO events (date, event, source_doc) VALUES (?, ?, ?)', 
                               (date, event, source_doc))
        conn.commit()

@app.route('/')
def index():
    """Serves the main HTML file."""
    return send_from_directory('templates', 'index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles file upload, text extraction, and event storage."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        filename = file.filename
        file_extension = os.path.splitext(filename)[1].lower()
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # 1. Extract Text
        extracted_text = extract_text(file_path, file_extension)
        if extracted_text is None:
            os.remove(file_path) # Clean up file if extraction fails
            return jsonify({'error': f'Unsupported file type or extraction failed for {file_extension}'}), 400

        # 2. Find Dates and Events
        events = find_dates_and_events(extracted_text)

        # 3. Store Events
        if events:
            store_events(events, filename)
            message = f'File "{filename}" processed. Found and stored {len(events)} events.'
        else:
            message = f'File "{filename}" processed. No events found.'
            
        return jsonify({'message': message}), 200
    
    return jsonify({'error': 'An unknown error occurred during upload.'}), 500

@app.route('/schedule', methods=['GET'])
def get_schedule():
    """
    Fetches all events and separates them into upcoming and past events.
    Returns: JSON object with 'upcoming_schedule' and 'past_schedule' lists.
    """
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        # Fetch all events, ordered by date
        cursor.execute('SELECT date, event, source_doc FROM events ORDER BY date')
        schedule_items = [{'date': row[0], 'event': row[1], 'source_doc': row[2]} for row in cursor.fetchall()]
        
        # Get today's date in the same format as stored in the database ('YYYY-MM-DD')
        today = datetime.now().strftime('%Y-%m-%d')
        
        upcoming_schedule = []
        past_schedule = []
        
        # Separate into upcoming and past by comparing date strings
        for item in schedule_items:
            if item['date'] >= today:
                upcoming_schedule.append(item)
            else:
                past_schedule.append(item)

    # Return both lists to the frontend
    return jsonify({
        'upcoming_schedule': upcoming_schedule, 
        'past_schedule': past_schedule
    }), 200

def get_upcoming_schedule_data():
    """
    Helper function to query and return only the upcoming schedule data.
    Used by the /download endpoint.
    """
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        # Get today's date in 'YYYY-MM-DD' format
        today = datetime.now().strftime('%Y-%m-%d')
        # Fetch events where the date is greater than or equal to today's date
        cursor.execute('SELECT date, event, source_doc FROM events WHERE date >= ? ORDER BY date', (today,))
        upcoming_data = cursor.fetchall()
    return upcoming_data


@app.route('/get_files', methods=['GET'])
def get_files():
    """Returns a list of all uploaded file names."""
    # Filter for only files in the UPLOAD_FOLDER
    files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], f))]
    file_list = [{'filename': f} for f in files]
    return jsonify({'files': file_list}), 200

@app.route('/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    """Deletes a file and all associated events from the database."""
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            # Delete associated events
            cursor.execute('DELETE FROM events WHERE source_doc = ?', (filename, ))
            conn.commit()
        return jsonify({'message': f'File "{filename}" and its events deleted successfully'}), 200
    else:
        return jsonify({'error': f'File "{filename}" not found'}), 404

@app.route('/download', methods=['GET'])
def download_schedule():
    """Generates a CSV file containing only the UPCOMING schedule data."""
    # Use the helper function to get only upcoming data
    data = get_upcoming_schedule_data()
    
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Date', 'Event', 'Source Document'])
    cw.writerows(data)
    
    output = Response(si.getvalue(), mimetype='text/csv')
    # Use a descriptive filename for upcoming data
    output.headers['Content-Disposition'] = 'attachment; filename=upcoming_schedule.csv'
    return output

if __name__ == '__main__':
    # Creates the 'templates' directory and the 'index.html' file if they don't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    # Note: Flask serves from the 'templates' directory by default for render_template, 
    # but for send_from_directory, we explicitly point to it.
    
    # In a real-world scenario, you might use a production WSGI server like Gunicorn
    # For this example, we use Flask's built-in server.
    app.run(debug=True, port=5000)
