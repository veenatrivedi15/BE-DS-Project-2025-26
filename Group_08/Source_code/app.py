import os
import difflib
import queue
import select
import sys
import threading
import uuid
import tempfile
import subprocess
import time
import shutil
import re
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session as flask_session
import flask
from flask_socketio import SocketIO, emit, join_room
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()  # Load .env file if it exists
    print("✅ Loaded environment variables from .env file")
except ImportError:
    print("⚠️ python-dotenv not installed. Using system environment variables only.")

# MySQL direct connection
try:
    import mysql.connector
    from mysql.connector import Error
    DB_AVAILABLE = True
    print("✅ MySQL connector available")
except ImportError:
    DB_AVAILABLE = False
    print("⚠️ mysql-connector-python not installed. Database features will be disabled.")

# Simple auth decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in flask_session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get current logged in user from session"""
    if 'user_id' in flask_session:
        return {
            'id': flask_session['user_id'],
            'username': flask_session.get('username'),
            'email': flask_session.get('email')
        }
    return None

# Groq and Mistral API imports (for AI summaries)
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("⚠️ groq library not installed. Groq summaries disabled.")

MISTRAL_AVAILABLE = False
try:
    # Prefer lightweight HTTP if package missing; detect via env.
    import requests
    MISTRAL_AVAILABLE = True
except Exception:
    print("⚠️ requests not available for Mistral API calls.")

# Local seq2seq guidance model (trained checkpoint under outputs/final_model)
LOCAL_GUIDANCE_MODEL_PATH = os.environ.get(
    "GUIDANCE_MODEL_PATH",
    os.path.join(os.getcwd(), "outputs", "final_model")
)
LOCAL_GUIDANCE_MODEL_DEVICE = None
LOCAL_GUIDANCE_MODEL_READY = False
_local_guidance_model = None
_local_guidance_tokenizer = None
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

    LOCAL_GUIDANCE_MODEL_DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if os.path.isdir(LOCAL_GUIDANCE_MODEL_PATH):
        LOCAL_GUIDANCE_MODEL_READY = True
        print(f"✅ Local guidance model path detected: {LOCAL_GUIDANCE_MODEL_PATH}")
    else:
        print(f"ℹ️ Local guidance model path not found at {LOCAL_GUIDANCE_MODEL_PATH}; using rule-based guidance.")
except ImportError:
    print("⚠️ torch/transformers not installed. Local guidance model disabled.")
    LOCAL_GUIDANCE_MODEL_READY = False

# Flask app initialization
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key')

# MySQL Database Configuration
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_PORT = int(os.environ.get('DB_PORT', '3306'))
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
DB_NAME = os.environ.get('DB_NAME', 'sciam')

# ===================== ACTIVITY CREDITS / LEVELS =====================
POINTS_PER_ACTIVITY = int(os.environ.get('POINTS_PER_ACTIVITY', '10'))
POINTS_PER_LEVEL = int(os.environ.get('POINTS_PER_LEVEL', '100'))

# In-memory fallback if DB is unavailable
credit_store = {}  # user_id -> {total_points, total_sessions, last_level, history: []}

def get_db_connection():
    """Create and return a MySQL database connection"""
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return connection
    except Error as e:
        print(f"❌ Error connecting to MySQL: {e}")
        return None

if DB_AVAILABLE:
    # Test connection
    test_conn = get_db_connection()
    if test_conn:
        print(f"✅ MySQL connected: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
        test_conn.close()
    else:
        print("⚠️ Could not connect to MySQL database")
        DB_AVAILABLE = False


def _level_from_points(points):
    """Simple game-like level formula."""
    pts = max(0, int(points or 0))
    return max(1, (pts // max(1, POINTS_PER_LEVEL)) + 1)


def _level_progress(points):
    """Return level progress details for UI display."""
    pts = max(0, int(points or 0))
    level = _level_from_points(pts)
    current_floor = (level - 1) * POINTS_PER_LEVEL
    next_level_points = level * POINTS_PER_LEVEL
    in_level = pts - current_floor
    percent = round((in_level / max(1, POINTS_PER_LEVEL)) * 100, 1)
    return {
        "level": level,
        "current_floor": current_floor,
        "next_level_points": next_level_points,
        "progress_percent": max(0, min(100, percent))
    }


def ensure_credit_tables():
    """Create tables required for persistent activity credits, if they don't exist."""
    if not DB_AVAILABLE:
        return False

    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_credits (
                user_id INT PRIMARY KEY,
                total_points INT NOT NULL DEFAULT 0,
                total_sessions INT NOT NULL DEFAULT 0,
                last_level INT NOT NULL DEFAULT 1,
                updated_at DATETIME NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_credit_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(64) NOT NULL,
                user_id INT NOT NULL,
                points_awarded INT NOT NULL DEFAULT 0,
                activity_score INT NOT NULL DEFAULT 0,
                total_edits INT NOT NULL DEFAULT 0,
                turns_count INT NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL,
                UNIQUE KEY uniq_session_user (session_id, user_id),
                INDEX idx_user_created (user_id, created_at)
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"⚠️ Failed to ensure credit tables: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return False


CREDIT_DB_READY = ensure_credit_tables() if DB_AVAILABLE else False


def _build_activity_by_sid(session):
    """Build per-user activity using sid as identity in the active session."""
    edit_counts = session.get("edit_counts", {}) or {}
    turns_by_sid = {}
    for msg in session.get("chat_messages", []) or []:
        sid = msg.get("sender_sid")
        if sid:
            turns_by_sid[sid] = turns_by_sid.get(sid, 0) + 1

    participants = session.get("participants", {}) or {}
    name_by_sid = session.get("name_by_sid", {}) or {}
    user_id_by_sid = session.get("user_id_by_sid", {}) or {}

    all_sids = set(edit_counts.keys()) | set(turns_by_sid.keys()) | set(name_by_sid.keys()) | set(participants.keys())
    activity = {}

    for sid in all_sids:
        part = participants.get(sid, {})
        name = part.get("name") or name_by_sid.get(sid) or f"user-{str(sid)[:4]}"
        user_id = part.get("user_id") or user_id_by_sid.get(sid)
        edits = int(edit_counts.get(sid, 0) or 0)
        turns = int(turns_by_sid.get(sid, 0) or 0)
        activity_score = edits + turns

        activity[sid] = {
            "sid": sid,
            "name": name,
            "user_id": user_id,
            "total_edits": edits,
            "turns_count": turns,
            "activity_score": activity_score,
            "points_awarded": activity_score * POINTS_PER_ACTIVITY
        }

    return activity


def _award_points_fallback(session_id, user_activity):
    """In-memory fallback for awarding credits."""
    user_id = user_activity.get("user_id")
    if not user_id:
        return None

    store = credit_store.setdefault(user_id, {
        "total_points": 0,
        "total_sessions": 0,
        "last_level": 1,
        "history": []
    })

    # Idempotency: skip if this session already awarded
    if any(h.get("session_id") == session_id for h in store.get("history", [])):
        prog = _level_progress(store.get("total_points", 0))
        return {
            "user_id": user_id,
            "username": user_activity.get("name"),
            "points_awarded": 0,
            "total_points": store.get("total_points", 0),
            "total_sessions": store.get("total_sessions", 0),
            "level": prog["level"]
        }

    points = int(max(0, user_activity.get("points_awarded", 0) or 0))
    activity_score = int(max(0, user_activity.get("activity_score", 0) or 0))

    store["total_points"] += points
    store["total_sessions"] += 1
    store["last_level"] = _level_from_points(store["total_points"])
    store["history"].append({
        "session_id": session_id,
        "points_awarded": points,
        "activity_score": activity_score,
        "total_edits": int(user_activity.get("total_edits", 0) or 0),
        "turns_count": int(user_activity.get("turns_count", 0) or 0),
        "created_at": datetime.utcnow().isoformat()
    })
    store["history"] = store["history"][-20:]

    return {
        "user_id": user_id,
        "username": user_activity.get("name"),
        "points_awarded": points,
        "total_points": store["total_points"],
        "total_sessions": store["total_sessions"],
        "level": store["last_level"]
    }


def _award_points_db(session_id, user_activity):
    """Persist awarded points into MySQL."""
    user_id = user_activity.get("user_id")
    if not user_id:
        return None

    if not (DB_AVAILABLE and CREDIT_DB_READY):
        return None

    conn = get_db_connection()
    if not conn:
        return None

    try:
        cursor = conn.cursor(dictionary=True)

        # Idempotency guard (host retries end_session)
        cursor.execute(
            "SELECT points_awarded FROM user_credit_history WHERE session_id = %s AND user_id = %s",
            (session_id, user_id)
        )
        existing = cursor.fetchone()

        points = int(max(0, user_activity.get("points_awarded", 0) or 0))
        activity_score = int(max(0, user_activity.get("activity_score", 0) or 0))
        edits = int(max(0, user_activity.get("total_edits", 0) or 0))
        turns = int(max(0, user_activity.get("turns_count", 0) or 0))

        if not existing:
            cursor.execute(
                """
                INSERT INTO user_credit_history
                (session_id, user_id, points_awarded, activity_score, total_edits, turns_count, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (session_id, user_id, points, activity_score, edits, turns, datetime.utcnow())
            )

            cursor.execute(
                """
                INSERT INTO user_credits (user_id, total_points, total_sessions, last_level, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    total_points = total_points + VALUES(total_points),
                    total_sessions = total_sessions + VALUES(total_sessions),
                    last_level = VALUES(last_level),
                    updated_at = VALUES(updated_at)
                """,
                (user_id, points, 1, _level_from_points(points), datetime.utcnow())
            )

            # Recompute last_level from updated total_points
            cursor.execute("SELECT total_points, total_sessions FROM user_credits WHERE user_id = %s", (user_id,))
            row = cursor.fetchone() or {"total_points": 0, "total_sessions": 0}
            total_points = int(row.get("total_points") or 0)
            total_sessions = int(row.get("total_sessions") or 0)
            level = _level_from_points(total_points)
            cursor.execute(
                "UPDATE user_credits SET last_level = %s, updated_at = %s WHERE user_id = %s",
                (level, datetime.utcnow(), user_id)
            )
        else:
            cursor.execute("SELECT total_points, total_sessions, last_level FROM user_credits WHERE user_id = %s", (user_id,))
            row = cursor.fetchone() or {"total_points": 0, "total_sessions": 0, "last_level": 1}
            total_points = int(row.get("total_points") or 0)
            total_sessions = int(row.get("total_sessions") or 0)
            level = int(row.get("last_level") or _level_from_points(total_points))
            points = 0  # avoid double-counting on repeated end_session call

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "user_id": user_id,
            "username": user_activity.get("name"),
            "points_awarded": points,
            "total_points": total_points,
            "total_sessions": total_sessions,
            "level": level
        }
    except Exception as e:
        print(f"⚠️ Failed to award DB credits for user {user_id}: {e}")
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass
        return None


def award_session_credits(session_id, session):
    """Award per-user credits after session close from activity score."""
    activity_by_sid = _build_activity_by_sid(session)
    awards = []

    for _, activity in activity_by_sid.items():
        if not activity.get("user_id"):
            # skip guests without user account
            continue

        result = _award_points_db(session_id, activity)
        if not result:
            result = _award_points_fallback(session_id, activity)
        if result:
            awards.append(result)

    # Save in report payload convenience
    session["credit_awards"] = awards
    return awards


def get_user_credit_profile(user_id, recent_limit=10):
    """Fetch user credit totals + recent points history."""
    if not user_id:
        return {
            "total_points": 0,
            "total_sessions": 0,
            "level": 1,
            "progress": _level_progress(0),
            "recent_history": []
        }

    # DB first
    if DB_AVAILABLE and CREDIT_DB_READY:
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute(
                    "SELECT total_points, total_sessions, last_level FROM user_credits WHERE user_id = %s",
                    (user_id,)
                )
                totals = cursor.fetchone() or {}

                cursor.execute(
                    """
                    SELECT session_id, points_awarded, activity_score, total_edits, turns_count, created_at
                    FROM user_credit_history
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (user_id, int(max(1, recent_limit)))
                )
                history = cursor.fetchall() or []
                cursor.close()
                conn.close()

                total_points = int(totals.get("total_points") or 0)
                level = int(totals.get("last_level") or _level_from_points(total_points))
                progress = _level_progress(total_points)
                progress["level"] = level

                return {
                    "total_points": total_points,
                    "total_sessions": int(totals.get("total_sessions") or 0),
                    "level": level,
                    "progress": progress,
                    "recent_history": history
                }
            except Exception as e:
                print(f"⚠️ Failed to fetch DB credit profile for user {user_id}: {e}")
                try:
                    conn.close()
                except Exception:
                    pass

    # Fallback
    store = credit_store.get(user_id, {})
    total_points = int(store.get("total_points") or 0)
    level = int(store.get("last_level") or _level_from_points(total_points))
    return {
        "total_points": total_points,
        "total_sessions": int(store.get("total_sessions") or 0),
        "level": level,
        "progress": _level_progress(total_points),
        "recent_history": (store.get("history") or [])[::-1][:recent_limit]
    }

GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
MISTRAL_API_KEY = os.environ.get('MISTRAL_API_KEY')

groq_client = None
if GROQ_API_KEY and GROQ_AVAILABLE:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        print(f"✅ Groq client initialized (key: ...{GROQ_API_KEY[-4:]})")
    except Exception as e:
        print(f"⚠️ Failed to init Groq client: {e}")
else:
    if not GROQ_API_KEY:
        print("ℹ️ GROQ_API_KEY not set; Groq summaries disabled.")

if MISTRAL_API_KEY and MISTRAL_AVAILABLE:
    print(f"✅ Mistral API configured (key: ...{MISTRAL_API_KEY[-4:]})")
else:
    if not MISTRAL_API_KEY:
        print("ℹ️ MISTRAL_API_KEY not set; Mistral summaries disabled.")

# Use threading async_mode for better compatibility
socketio = SocketIO(app, 
                   cors_allowed_origins="*",
                   async_mode='threading')

# ===================== DATABASE HELPER FUNCTIONS =====================

# Store sessions in memory (for backward compatibility)
sessions = {}
running_processes = {}
input_queues = {}
process_needs_input = {}
execution_index_by_pid = {}


# ================= ONLINE USER TRACKING =================
# Track users by user_id with their socket connections
# A user can have multiple sockets (homepage, editor, etc.)
online_users = {}  # user_id -> {username, sids: [sid1, sid2, ...], last_seen}
socket_to_user = {}  # sid -> user_id (for reverse lookup on disconnect)

@socketio.on("connect")
def on_connect():
    """Track user as online when they connect to ANY page (homepage, editor, etc.)"""
    user_id = flask_session.get("user_id")
    username = flask_session.get("username")
    sid = request.sid
    
    if user_id:
        # Record this socket -> user mapping for disconnect
        socket_to_user[sid] = user_id
        
        # Initialize or update user's online record
        if user_id not in online_users:
            # First connection from this user
            online_users[user_id] = {
                "username": username,
                "sids": [sid],  # Track all socket connections
                "last_seen": datetime.utcnow().isoformat()
            }
            print(f"🟢 {username} is online (new connection)")
        else:
            # User already online but connecting from another page/tab
            if sid not in online_users[user_id]["sids"]:
                online_users[user_id]["sids"].append(sid)
            online_users[user_id]["last_seen"] = datetime.utcnow().isoformat()
            print(f"🟢 {username} connected from another page (total connections: {len(online_users[user_id]['sids'])})")

@socketio.on("disconnect")
def on_disconnect():
    """Remove socket from user's connection list. Only mark offline if no other sockets remain."""
    sid = request.sid
    
    if sid not in socket_to_user:
        return
    
    user_id = socket_to_user[sid]
    del socket_to_user[sid]
    
    if user_id not in online_users:
        return
    
    # Remove this socket from user's list
    if sid in online_users[user_id]["sids"]:
        online_users[user_id]["sids"].remove(sid)
    
    # If user has no remaining connections, mark as offline
    if not online_users[user_id]["sids"]:
        username = online_users[user_id]["username"]
        del online_users[user_id]
        print(f"🔴 {username} is offline (all connections closed)")
    else:
        # User still has other connections open
        username = online_users[user_id]["username"]
        print(f"⚪ {username} still online ({len(online_users[user_id]['sids'])} connection(s) remaining)")

def _log_control_event(session, action, from_sid=None, to_sid=None, reason=""):
    """Record control / writer handover events for timeline intelligence."""
    try:
        name_by_sid = session.get("name_by_sid", {})
        participants = session.get("participants", {})
        from_name = None
        to_name = None
        if from_sid:
            from_name = participants.get(from_sid, {}).get("name") or name_by_sid.get(from_sid)
        if to_sid:
            to_name = participants.get(to_sid, {}).get("name") or name_by_sid.get(to_sid)

        session.setdefault("control_events", []).append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "from_sid": from_sid,
            "to_sid": to_sid,
            "from_name": from_name,
            "to_name": to_name,
            "reason": reason
        })
    except Exception:
        # Never allow timeline logging to break main flow
        pass

# Root for storing uploaded datasets per session
UPLOAD_ROOT = os.path.join(os.getcwd(), "data", "sessions")
os.makedirs(UPLOAD_ROOT, exist_ok=True)

# Root for storing latency logs
LATENCY_LOG_DIR = os.path.join(os.getcwd(), "data", "latency_logs")
os.makedirs(LATENCY_LOG_DIR, exist_ok=True)

# Limit uploads to 200 MB per file (adjust if needed)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024

# ===================== AI GUIDANCE MAPS =====================

WHY_MAP = {
    "ZeroDivisionError": "A division operation was attempted with zero as the denominator, which Python does not allow.",
    "IndexError": "The code attempts to access a list element using an index outside the valid range.",
    "KeyError": "The program tries to access a dictionary key that does not exist.",
    "TypeError": "An operation was performed on incompatible data types.",
    "SyntaxError": "The code violates Python syntax rules and cannot be executed.",
    "IndentationError": "Python requires consistent indentation to define code blocks.",
    "ValueError": "A function received a valid type but an invalid value.",
    "InputError": "The program crashed due to invalid user input. User-provided data was not validated before use."
}

HOW_MAP = {
    "ZeroDivisionError": [
        "Check the divisor before performing division",
        "Validate input values",
        "Handle zero values explicitly"
    ],
    "IndexError": [
        "Check the length of the list",
        "Ensure index stays within valid bounds",
        "Review loop logic"
    ],
    "KeyError": [
        "Verify the key exists before access",
        "Use safe dictionary access",
        "Inspect dictionary structure"
    ],
    "TypeError": [
        "Ensure compatible data types",
        "Convert values to expected types",
        "Inspect variable types"
    ],
    "SyntaxError": [
        "Check syntax near the highlighted line",
        "Look for missing colons or brackets",
        "Follow Python block rules"
    ],
    "InputError": [
        "Add try-except blocks around input conversion",
        "Validate user input before using it",
        "Provide clear error messages to users",
        "Use default values for invalid input"
    ]
}

# ===================== SAFE CODE EXAMPLES =====================
# Curated examples inspired by Python documentation and best practices
# These are ILLUSTRATIVE only - NOT automatic fixes

SAFE_EXAMPLES = {
    "ZeroDivisionError": {
        "title": "Safe Division Pattern",
        "source": "Python best practice",
        "code": """# Check divisor before division
divisor = get_value()
if divisor != 0:
    result = numerator / divisor
else:
    result = 0  # or handle appropriately
    print("Cannot divide by zero")"""
    },
    "IndexError": {
        "title": "Safe List Access",
        "source": "Python documentation idiom",
        "code": """# Check list length before access
my_list = [1, 2, 3]
index = 5

if 0 <= index < len(my_list):
    value = my_list[index]
else:
    print(f"Index {index} out of range")"""
    },
    "KeyError": {
        "title": "Safe Dictionary Access",
        "source": "Python documentation idiom",
        "code": """# Use .get() for safe access
my_dict = {'name': 'Alice', 'age': 30}

# Safe approach
value = my_dict.get('email', 'default@example.com')

# Or check if key exists
if 'email' in my_dict:
    value = my_dict['email']"""
    },
    "TypeError": {
        "title": "Type Checking Pattern",
        "source": "Python best practice",
        "code": """# Check types before operations
value = input("Enter number: ")

# Convert to correct type
try:
    number = int(value)
    result = number * 2
except ValueError:
    print("Invalid number format")"""
    },
    "ValueError": {
        "title": "Input Validation",
        "source": "Python best practice",
        "code": """# Validate input before conversion
user_input = "abc"

try:
    number = int(user_input)
except ValueError:
    print("Please enter a valid integer")
    number = 0  # default value"""
    },
    "NameError": {
        "title": "Variable Initialization",
        "source": "Python best practice",
        "code": """# Initialize variables before use
result = 0  # Initialize first

for i in range(10):
    result += i

print(result)"""
    },
    "AttributeError": {
        "title": "Attribute Checking",
        "source": "Python documentation idiom",
        "code": """# Check if attribute exists
obj = MyClass()

if hasattr(obj, 'method_name'):
    obj.method_name()
else:
    print("Method not found")"""
    },
    "InputError": {
        "title": "Safe Input Validation",
        "source": "Python best practice",
        "code": """# Always validate user input
while True:
    user_input = input("Enter a number: ")
    try:
        number = int(user_input)
        if number != 0:  # Additional validation
            result = 100 / number
            print(f"Result: {result}")
            break
        else:
            print("Cannot divide by zero. Try again.")
    except ValueError:
        print("Invalid input. Please enter a number.")"""
    }
}

def classify_error_type(error_subtype, code_text):
    """
    Lightweight classification to detect if a runtime error is input-related.
    
    Args:
        error_subtype: The original Python error type (e.g., 'ValueError')
        code_text: The user's code as a string
    
    Returns:
        'InputError' if the error is likely caused by user input, otherwise the original error_subtype
    """
    # Errors that can be caused by bad user input
    input_related_errors = {'ValueError', 'TypeError', 'ZeroDivisionError'}
    
    # Check if code contains input() calls
    has_input = 'input(' in code_text
    
    # Classify as InputError if both conditions are met
    if error_subtype in input_related_errors and has_input:
        return 'InputError'
    
    return error_subtype


def _load_local_guidance_model():
    """Lazy-load the local seq2seq guidance model if available."""
    global _local_guidance_model, _local_guidance_tokenizer

    if not LOCAL_GUIDANCE_MODEL_READY:
        return None, None, None

    if _local_guidance_model is not None and _local_guidance_tokenizer is not None:
        return _local_guidance_model, _local_guidance_tokenizer, LOCAL_GUIDANCE_MODEL_DEVICE

    if not os.path.isdir(LOCAL_GUIDANCE_MODEL_PATH):
        print(f"ℹ️ Guidance model path missing: {LOCAL_GUIDANCE_MODEL_PATH}")
        return None, None, None

    try:
        _local_guidance_tokenizer = AutoTokenizer.from_pretrained(LOCAL_GUIDANCE_MODEL_PATH)
        _local_guidance_model = AutoModelForSeq2SeqLM.from_pretrained(
            LOCAL_GUIDANCE_MODEL_PATH,
            use_safetensors=True
        ).to(LOCAL_GUIDANCE_MODEL_DEVICE)
        _local_guidance_model.eval()
        print(f"✅ Loaded local guidance model on {LOCAL_GUIDANCE_MODEL_DEVICE}")
        return _local_guidance_model, _local_guidance_tokenizer, LOCAL_GUIDANCE_MODEL_DEVICE
    except Exception as e:
        print(f"⚠️ Failed to load local guidance model: {e}")
        _local_guidance_model = None
        _local_guidance_tokenizer = None
        return None, None, None


def _generate_local_guidance_text(code, error_subtype, traceback_text=None, severity="High"):
    """Generate guidance text using the local checkpoint, if available."""
    model, tokenizer, device = _load_local_guidance_model()
    if not model or not tokenizer:
        return None

    # Keep the prompt concise to avoid GPU/CPU overload
    code_snippet = code.strip() if code else ""
    if len(code_snippet) > 4000:
        code_snippet = code_snippet[:4000] + "\n...\n[truncated]"

    tb_snippet = ""
    if traceback_text:
        tb_compact = traceback_text.strip()
        if len(tb_compact) > 1500:
            tb_compact = tb_compact[-1500:]
        tb_snippet = f"\nTraceback:\n{tb_compact}"

    prompt = f"""Analyze the error and provide a guided suggestion.

Buggy Code:
{code_snippet}

Error Type: Runtime Error
Error Subtype: {error_subtype}
Severity: {severity}{tb_snippet}
"""

    try:
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=512
        ).to(device)

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_length=220,
                num_beams=4,
                early_stopping=True
            )

        return tokenizer.decode(outputs[0], skip_special_tokens=True)
    except Exception as e:
        print(f"⚠️ Local guidance model inference failed: {e}")
        return None


def build_ai_guidance_payload(code, error_subtype, line_number=None, traceback_text=""):
    """Generate guidance using the local model first, then fall back to rule-based hints."""
    classified_error = classify_error_type(error_subtype, code)

    model_output = _generate_local_guidance_text(
        code=code,
        error_subtype=classified_error,
        traceback_text=traceback_text,
        severity="High" if classified_error not in {"InputError"} else "Medium"
    )

    source = "Local model (outputs/final_model)" if model_output else "Rule-based guidance"
    summary_text = model_output or f"The error '{classified_error}' occurred while executing the code."

    guidance = build_guidance(summary_text, classified_error)
    guidance["source"] = source
    if line_number:
        guidance["line_number"] = line_number

    return guidance, classified_error


def check_ollama_health():
    """
    Check if Ollama is running and accessible.
    
    Returns:
        bool: True if Ollama is available, False otherwise
    """
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except Exception as e:
        print(f"⚠️ Ollama health check failed: {e}")
        return False

def get_ollama_code_analysis(code, mode="error_analysis", error_type=None, error_message=None, line_number=None, stderr_content=None):
    """
    Call Ollama's local API to generate code analysis.
    
    Args:
        code: The full source code to analyze
        mode: 'error_analysis' or 'logic_review'
        error_type: The Python error type (for error_analysis mode)
        error_message: The error message (for error_analysis mode)
        line_number: The line number where the error occurred (for error_analysis mode)
        stderr_content: The full stderr output (for error_analysis mode)
    
    Returns:
        A dictionary with code analysis or None if the API call fails
    """
    try:
        # Extract the faulty code line if possible
        faulty_line = ""
        if line_number and code:
            lines = code.split('\n')
            if 0 < line_number <= len(lines):
                faulty_line = lines[line_number - 1].strip()
        
        # Create mode-specific prompts
        if mode == "error_analysis":
            prompt = f"""Analyze this Python error. Be CONCISE and DIRECT.

ERROR: {error_type} at line {line_number}
CODE:
```python
{code}
```

FORMAT YOUR RESPONSE EXACTLY AS:

1. Logic Analysis:
   - [3-5 short bullet points about what went wrong]
   - [Focus only on the logical issue]
   - [One line per bullet]

2. Code Quality:
   - [3-5 short bullets on code readability/structure]
   - [No beginner explanations]
   - [One line per bullet]

3. Suggestions:
   - [3-5 actionable debugging steps]
   - [No code rewrites]
   - [One line per bullet]

RULES: No paragraphs. No verbose explanations. No code fixes. Maximum 15 total lines."""
        else:  # logic_review
            prompt = f"""Review this Python code professionally. Be CONCISE and STRUCTURED.

CODE:
```python
{code}
```

FORMAT YOUR RESPONSE EXACTLY AS:

1. Logic Analysis:
   - [3-5 short bullets about logical risks or edge cases]
   - [Focus on potential bugs]
   - [One line per bullet]

2. Code Quality:
   - [3-5 short bullets on readability and structure]
   - [No obvious explanations]
   - [One line per bullet]

3. Suggestions:
   - [3-5 actionable improvements]
   - [No code rewrites]
   - [One line per bullet]

RULES: No paragraphs. No verbose text. No beginner lessons. Maximum 15 total lines."""
        
        print(f"🔍 Calling Ollama API for {mode}...")
        
        # Call Ollama API
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "deepseek-coder:6.7b",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Lower temperature for more focused responses
                    "top_p": 0.9,
                    "num_predict": 400,  # Limit to ~400 tokens for concise output
                    "stop": ["\n\n\n", "```"]  # Stop at excessive newlines or code blocks
                }
            },
            timeout=30  # 30 second timeout
        )
        
        print(f"✅ Ollama API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            generated_text = result.get("response", "").strip()
            
            if generated_text:
                print(f"✅ Ollama analysis completed successfully")
                return {
                    "mode": mode,
                    "content": generated_text,
                    "error_type": error_type,
                    "line_number": line_number,
                    "faulty_line": faulty_line,
                    "source": "Ollama - deepseek-coder:6.7b"
                }
        else:
            print(f"❌ Ollama API returned status {response.status_code}: {response.text[:200]}")
        
        return None
        
    except requests.exceptions.Timeout:
        print("⚠️ Ollama API timeout - request took longer than 30 seconds")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"⚠️ Cannot connect to Ollama at localhost:11434 - Connection Error: {e}")
        print("   Make sure Ollama is running: ollama serve")
        return None
    except Exception as e:
        print(f"⚠️ Unexpected error calling Ollama API: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None

def build_guidance(model_output, error_subtype):
    guidance = {
        "summary": model_output,
        "why": WHY_MAP.get(
            error_subtype,
            "The issue occurred due to an invalid operation in the code."
        ),
        "how": HOW_MAP.get(
            error_subtype,
            ["Review the logic where the error occurred"]
        ),
        "collaboration_hint":
            "Discuss this issue with collaborators and decide how to resolve it together."
    }
    
    # Add safe example if available
    example = SAFE_EXAMPLES.get(error_subtype)
    if example:
        guidance["example"] = example
    
    return guidance

def build_guidance(model_output, error_subtype):
    guidance = {
        "summary": model_output,
        "why": WHY_MAP.get(
            error_subtype,
            "The issue occurred due to an invalid operation in the code."
        ),
        "how": HOW_MAP.get(
            error_subtype,
            ["Review the logic where the error occurred"]
        ),
        "collaboration_hint":
            "Discuss this issue with collaborators and decide how to resolve it together."
    }
    
    # Add safe example if available
    example = SAFE_EXAMPLES.get(error_subtype)
    if example:
        guidance["example"] = example
    
    return guidance

@app.route("/")
def index():
    """Homepage - shows login form or session dashboard"""
    current_user = get_current_user()
    
    if current_user:
        # Show dashboard with user's completed session reports
        user_sessions = []
        user_credit_summary = get_user_credit_profile(current_user['id'], recent_limit=5)
        if DB_AVAILABLE:
            try:
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute(
                        "SELECT * FROM session_reports WHERE host_user_id = %s ORDER BY created_at DESC",
                        (current_user['id'],)
                    )
                    user_sessions = cursor.fetchall()
                    cursor.close()
                    conn.close()
            except Exception as e:
                print(f"Error fetching sessions: {e}")
        
        return render_template("homes.html", 
                             user=current_user, 
                             user_sessions=user_sessions,
                             user_credit_summary=user_credit_summary)
    else:
        # Show login/register form
        return render_template("homes.html", user=None)

@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login"""
    if get_current_user():
        return redirect(url_for('index'))
    
    if not DB_AVAILABLE:
        flash("Database not available.", "error")
        return redirect(url_for('index'))
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        
        if not username or not password:
            flash("Username and password are required.", "error")
            return redirect(url_for('login'))
        
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
                user = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if user and check_password_hash(user['password_hash'], password):
                    # Set session
                    flask_session['user_id'] = user['id']
                    flask_session['username'] = user['username']
                    flask_session['email'] = user['email']
                    flash(f"Welcome back, {user['username']}!", "success")
                    return redirect(url_for('index'))
                else:
                    flash("Invalid username or password.", "error")
        except Exception as e:
            print(f"Login error: {e}")
            flash("Login failed. Please try again.", "error")
    
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Handle user registration"""
    if get_current_user():
        return redirect(url_for('index'))
    
    if not DB_AVAILABLE:
        flash("Database not available.", "error")
        return redirect(url_for('index'))
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()
        
        # Validation
        if not username or not email or not password:
            flash("All fields are required.", "error")
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for('register'))
        
        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return redirect(url_for('register'))
        
        try:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor(dictionary=True)
                
                # Check if user exists
                cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
                if cursor.fetchone():
                    flash("Username already exists.", "error")
                    cursor.close()
                    conn.close()
                    return redirect(url_for('register'))
                
                cursor.execute("SELECT * FROM user WHERE email = %s", (email,))
                if cursor.fetchone():
                    flash("Email already registered.", "error")
                    cursor.close()
                    conn.close()
                    return redirect(url_for('register'))
                
                # Create new user
                password_hash = generate_password_hash(password)
                cursor.execute(
                    "INSERT INTO user (username, email, password_hash, created_at) VALUES (%s, %s, %s, %s)",
                    (username, email, password_hash, datetime.utcnow())
                )
                conn.commit()
                cursor.close()
                conn.close()
                
                flash("Registration successful! Please log in.", "success")
                return redirect(url_for('login'))
        except Exception as e:
            print(f"Registration error: {e}")
            flash(f"Registration failed: {str(e)}", "error")
    
    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    """Handle user logout"""
    flask_session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('index'))


@app.route("/profile")
@login_required
def profile():
    """User profile page with level, points, and recent credit history."""
    current_user = get_current_user()
    credit_profile = get_user_credit_profile(current_user['id'], recent_limit=10)
    return render_template(
        "profile.html",
        user=current_user,
        credit_profile=credit_profile,
        points_per_activity=POINTS_PER_ACTIVITY,
        points_per_level=POINTS_PER_LEVEL
    )

@app.route("/create_session", methods=["POST"])
@login_required
def create_session():
    """Create a new session"""
    session_id = str(uuid.uuid4())[:8]
    current_user = get_current_user()
    
    # Store in memory for real-time collaboration
    session_name = request.form.get("session_name", f"Session {session_id}")
    sessions[session_id] = {
        "files": {
            "main.py": "# Welcome to SCIAM Collaborative Editor\n# Start coding in Python...\nprint('Hello, World!')"
        },
        "active_file": "main.py",
        "participants": {},
        "host_id": None,
        "writer_id": None,
        "chat_messages": [],
        "edit_counts": {},
        "name_by_sid": {},
        "user_id_by_sid": {},
        "all_participants": [],
        "session_name": session_name,
        "host_user_id": current_user['id'] if current_user else None,
        "created_at": datetime.utcnow().isoformat(),
        "executions": [],
        "user_contributions": {},
        "control_events": [],
        "latency_metrics": {
            "code_sync": [],
            "chat_messages": [],
            "network_rtt": {},
            "stats": {
                "avg_code_sync_ms": 0,
                "avg_chat_ms": 0,
                "avg_network_rtt_ms": 0,
                "max_code_sync_ms": 0,
                "max_chat_ms": 0,
                "total_measurements": 0
            }
        }
    }
    
    print(f"🎉 New session created: {session_id}")
    
    return jsonify({"session_id": session_id})

@app.route("/join_session/<session_id>", methods=["GET"])
def join_session(session_id):
    """Validate if a session exists before allowing join"""
    if session_id in sessions:
        return jsonify({
            "status": "success",
            "message": "Session found",
            "session_id": session_id
        })
    else:
        return jsonify({
            "status": "error",
            "message": "Session not found. Please check the session code."
        }), 404

@app.route("/editor/<session_id>")
def editor(session_id):
    if session_id not in sessions:
        return "Session not found", 404
    # Get user name from URL parameter, default to 'Anonymous'
    user_name = request.args.get('name', 'Anonymous')
    return render_template("editors.html", session_id=session_id, user_name=user_name)

@app.route("/run_code", methods=["POST"])
def run_code():
    data = request.get_json()
    code = data.get("code", "")
    session_id = data.get("session_id")
    user_input = data.get("user_input", "")
    process_id = data.get("process_id")

    # Optional parameters
    timeout_seconds = int(data.get("timeout_seconds", 120))
    timeout_seconds = max(1, min(timeout_seconds, 300))  # allow 1..300s
    use_docker = bool(data.get("use_docker", False))
    docker_packages = data.get("docker_packages", [])  # e.g. ["numpy","pandas"]

    # If this is providing input to an existing process
    if process_id and user_input:
        if process_id in input_queues:
            input_queues[process_id].put(user_input + "\n")
            return jsonify({"status": "input_sent", "message": "Input sent to process"})
        else:
            return jsonify({"status": "error", "message": "Process not found or completed"})

    try:
        # Better detection for interactive code:
        # strip triple-quoted / quoted strings and comments first, then search for real input(...) or sys.stdin
        def _strip_strings_and_comments(s):
            s = re.sub(r'(""".*?"""|\'\'\'.*?\'\'\')', '', s, flags=re.S)  # triple-quoted
            s = re.sub(r'(".*?"|\'.*?\')', '', s, flags=re.S)               # single/double quoted
            s = re.sub(r'#.*', '', s)                                       # line comments
            return s

        cleaned = _strip_strings_and_comments(code or "")
        code_needs_input = bool(re.search(r'\binput\s*\(', cleaned)) or bool(re.search(r'\bsys\.stdin\b', cleaned))
        
        # Create a unique process ID for this execution
        process_id = str(uuid.uuid4())
        
        # Create input queue for this process (keep queue present to avoid race conditions)
        input_queues[process_id] = queue.Queue()
        process_needs_input[process_id] = code_needs_input

        # Initialize execution log for MOM
        if session_id and session_id in sessions:
            session = sessions[session_id]
            session.setdefault("executions", [])
            execution_index_by_pid[process_id] = len(session["executions"])  # map pid -> index
            session["executions"].append({
                "process_id": process_id,
                "start_time": datetime.utcnow().isoformat(),
                "end_time": None,
                "code": code,
                "needs_input": code_needs_input,
                "stdout": [],
                "stderr": [],
                "status": "running"
            })
        
        # Run the code in a separate thread to handle input and streaming
        thread = threading.Thread(
            target=run_code_with_input,
            args=(code, process_id, session_id, code_needs_input, timeout_seconds, use_docker, docker_packages)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "started", 
            "process_id": process_id,
            "needs_input": code_needs_input,
            "message": "Code execution started successfully",
            "timeout_seconds": timeout_seconds,
            "use_docker": use_docker
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error starting execution: {str(e)}"})

def _normalize_windows_paths_in_string_literals(src):
    """
    Only normalize string literals that look like file paths (contain backslashes and a file extension).
    This replaces backslashes with forward-slashes inside those literals to avoid Python unicode-escape errors
    such as '\\u...' when a filename begins with 'u' (e.g. 'ultimate...').
    """
    def repl(m):
        quote = m.group(1)
        content = m.group(2)
        # only normalize if it contains backslashes and looks like a filename (has an extension)
        if "\\" in content and re.search(r'\.\w{1,5}(?:$|\W)', content):
            new_content = content.replace("\\\\", "/")
            return quote + new_content + quote
        return m.group(0)

    # handle simple single/double-quoted strings (non-greedy)
    return re.sub(r'(["\'])(.*?)(\1)', lambda m: repl(m), src, flags=re.S)

def _copy_session_datasets_to_temp(session_id, temp_dir):
    """Copy all files from data/sessions/<session_id> into temp_dir/data/ (preserve structure).
       Also mirror them under temp_dir/datasets/<session_id>/ so user code referencing the
       'datasets/<session_id>/<file>' path will find files (this matches the download URL layout)."""
    session_dir = os.path.join(UPLOAD_ROOT, session_id)
    if not os.path.isdir(session_dir):
        return
    # primary copy location
    dest_root = os.path.join(temp_dir, "data")
    os.makedirs(dest_root, exist_ok=True)
    # mirror location matching earlier download route pattern
    mirror_root = os.path.join(temp_dir, "datasets", session_id)
    os.makedirs(mirror_root, exist_ok=True)

    for root, dirs, files in os.walk(session_dir):
        rel = os.path.relpath(root, session_dir)
        target_dir = dest_root if rel == "." else os.path.join(dest_root, rel)
        mirror_dir = mirror_root if rel == "." else os.path.join(mirror_root, rel)
        os.makedirs(target_dir, exist_ok=True)
        os.makedirs(mirror_dir, exist_ok=True)
        for f in files:
            src = os.path.join(root, f)
            dst = os.path.join(target_dir, f)
            mirror_dst = os.path.join(mirror_dir, f)
            try:
                shutil.copy2(src, dst)
            except Exception:
                pass
            try:
                shutil.copy2(src, mirror_dst)
            except Exception:
                pass

def run_code_with_input(code, process_id, session_id, code_needs_input, timeout_seconds=120, use_docker=False, docker_packages=None):
    """Run Python code with live stdout/stderr streaming. Optional Docker execution."""
    process = None
    temp_filename = None
    temp_dir = None
    
    # Error buffer for multi-line error handling
    error_buffer = []
    ai_guidance_sent = False
    
    try:
        docker_packages = docker_packages or []
        # Create a temp directory (helps for Docker volume mount)
        temp_dir = tempfile.mkdtemp(prefix="siren_exec_")
        temp_filename = os.path.join(temp_dir, "program.py")

        # Normalize potential Windows backslash paths inside string literals (conservative)
        safe_code = _normalize_windows_paths_in_string_literals(code)

        with open(temp_filename, "w", encoding="utf-8") as tmp:
            tmp.write(safe_code)
            tmp.flush()

        # Copy session datasets into the execution folder so code can access them at ./data/...
        try:
            _copy_session_datasets_to_temp(session_id, temp_dir)
            if os.path.isdir(os.path.join(temp_dir, "data")):
                socketio.emit("code_output", {
                    "process_id": process_id,
                    "output": "📁 Session datasets were copied into the execution workspace at ./data/ and ./datasets/<session_id>/\n",
                    "type": "system"
                }, room=session_id)
        except Exception:
            pass

        # Prepare command: either local python or docker run
        if use_docker:
            # Check docker availability
            if shutil.which("docker") is None:
                socketio.emit("code_output", {
                    "process_id": process_id,
                    "output": "⚠️ Docker not found on server, falling back to local execution.\n",
                    "type": "system"
                }, room=session_id)
                use_docker = False

        if use_docker:
            # Build pip install string if packages requested
            pip_cmd = ""
            if docker_packages:
                # join packages safely
                pip_cmd = "pip install --no-cache-dir " + " ".join(docker_packages) + " >/dev/null 2>&1 && "
            # Docker volume mounting: map temp_dir -> /workspace
            container_cmd = f"{pip_cmd}python /workspace/program.py"
            cmd = [
                "docker", "run", "--rm", "-i",
                "-v", f"{temp_dir}:/workspace",
                "-w", "/workspace",
                "python:3.11-slim",
                "bash", "-lc", container_cmd
            ]
            stdin_pipe = subprocess.PIPE if code_needs_input else None
        else:
            cmd = [sys.executable, temp_filename]
            stdin_pipe = subprocess.PIPE if code_needs_input else None

        # Start subprocess
        process = subprocess.Popen(
            cmd,
            stdin=stdin_pipe,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=temp_dir
        )
        running_processes[process_id] = process

        # Notify clients that execution started
        socketio.emit("code_output", {
            "process_id": process_id,
            "output": "🚀 Code execution started...\n",
            "type": "system"
        }, room=session_id)

        # Helper to stream a single stream (stdout/stderr)
        def stream_reader(stream, stream_type):
            nonlocal ai_guidance_sent
            try:
                for line in iter(stream.readline, ''):
                    if not line:
                        break

                    socketio.emit("code_output", {
                        "process_id": process_id,
                        "output": line,
                        "type": stream_type
                    }, room=session_id)

                    # Append to execution logs for MOM
                    try:
                        if session_id in sessions:
                            session = sessions[session_id]
                            idx = execution_index_by_pid.get(process_id)
                            if idx is not None and idx < len(session.get("executions", [])):
                                entry = session["executions"][idx]
                                if stream_type == "stdout":
                                    entry["stdout"].append(line)
                                else:
                                    entry["stderr"].append(line)
                    except Exception:
                        pass

                    # ========= Multi-line error handling =========
                    if stream_type == "stderr":
                        error_buffer.append(line)

                        line_number = None
                        # Try to extract line number from traceback
                        line_match = re.search(r'File ".*?", line (\d+)', line)
                        if line_match:
                            line_number = int(line_match.group(1))

                        # Trigger guidance only once, on final error line
                        match = re.search(r'(\w+Error)', line)
                        if match and not ai_guidance_sent:
                            error_subtype = match.group(1)
                            traceback_text = "".join(error_buffer)

                            guidance, classified_error = build_ai_guidance_payload(
                                code=code,
                                error_subtype=error_subtype,
                                line_number=line_number,
                                traceback_text=traceback_text
                            )

                            try:
                                print(f"🤖 Guidance generated (source: {guidance.get('source')}) for session {session_id}")
                            except Exception:
                                pass

                            socketio.emit("ai_guidance", {
                                "process_id": process_id,
                                "guidance": guidance,
                                "error_line": line_number,
                                "traceback": traceback_text
                            }, room=session_id)

                            # Persist last error for manual guidance requests
                            try:
                                if session_id in sessions:
                                    sessions[session_id]["last_error"] = {
                                        "error_type": classified_error,
                                        "raw_error_type": error_subtype,
                                        "code": code,
                                        "line_number": line_number,
                                        "traceback": traceback_text,
                                        "guidance": guidance
                                    }
                            except Exception:
                                pass

                            ai_guidance_sent = True

            except Exception as e:
                socketio.emit("code_output", {
                    "process_id": process_id,
                    "output": f"\n❌ Stream read error: {e}\n",
                    "type": "error"
                }, room=session_id)

        # Start streaming threads
        stdout_thread = threading.Thread(target=stream_reader, args=(process.stdout, "stdout"))
        stderr_thread = threading.Thread(target=stream_reader, args=(process.stderr, "stderr"))
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()

        # Main loop: monitor process and handle input queue
        start_time = time.time()
        while True:
            if process.poll() is not None:
                break  # process finished

            # Timeout enforcement
            if time.time() - start_time > timeout_seconds:
                try:
                    process.kill()
                except Exception:
                    pass
                socketio.emit("code_output", {
                    "process_id": process_id,
                    "output": f"\n⏰ Error: Code execution timed out ({timeout_seconds} seconds)\n",
                    "type": "error"
                }, room=session_id)
                break

            # Try to send input if available
            try:
                user_input = input_queues[process_id].get(timeout=0.1)
                if process.stdin:
                    try:
                        process.stdin.write(user_input)
                        process.stdin.flush()
                        socketio.emit("input_received", {
                            "process_id": process_id
                        }, room=session_id)
                    except BrokenPipeError:
                        # process ended, ignore
                        pass
            except queue.Empty:
                pass
            except KeyError:
                # input queue removed/cleanup race
                break

            time.sleep(0.05)

        # Wait a short time for streaming threads to finish sending remaining output
        try:
            stdout_thread.join(timeout=2)
            stderr_thread.join(timeout=2)
        except Exception:
            pass

        # Send completion signal
        status = "completed" if process.poll() is not None and process.returncode == 0 else "finished"
        socketio.emit("code_complete", {
            "process_id": process_id,
            "status": status
        }, room=session_id)

        # Mark execution end time and status
        try:
            if session_id in sessions:
                session = sessions[session_id]
                idx = execution_index_by_pid.get(process_id)
                if idx is not None and idx < len(session.get("executions", [])):
                    entry = session["executions"][idx]
                    entry["end_time"] = datetime.utcnow().isoformat()
                    entry["status"] = status
        except Exception:
            pass

    except Exception as e:
        socketio.emit("code_output", {
            "process_id": process_id,
            "output": f"\n❌ Execution error: {str(e)}\n",
            "type": "error"
        }, room=session_id)
    finally:
        # Cleanup
        if process_id in running_processes:
            del running_processes[process_id]
        if process_id in input_queues:
            try:
                del input_queues[process_id]
            except KeyError:
                pass
        if process_id in process_needs_input:
            try:
                del process_needs_input[process_id]
            except KeyError:
                pass
        # terminate process if still alive
        try:
            if process and process.poll() is None:
                process.kill()
        except Exception:
            pass
        # remove temp files/dir
        try:
            if temp_filename and os.path.exists(temp_filename):
                os.unlink(temp_filename)
            if temp_dir and os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception:
            pass

# Add a new endpoint to provide input to running process
@app.route("/provide_input", methods=["POST"])
def provide_input():
    data = request.get_json()
    process_id = data.get("process_id")
    user_input = data.get("user_input", "")
    
    if not process_id or not user_input:
        return jsonify({"status": "error", "message": "Process ID and input are required"})
    
    if process_id in input_queues:
        input_queues[process_id].put(user_input + "\n")
        return jsonify({"status": "success", "message": "Input sent to process"})
    else:
        return jsonify({"status": "error", "message": "Process not found or completed"})

@socketio.on("ai_guidance_request")
def handle_ai_guidance_request(data):
    """Handle AI Guidance requests using the OLD trained model (NOT Ollama)"""
    session_id = data.get("session_id")
    
    if not session_id or session_id not in sessions:
        emit("error", {"msg": "Session not found"})
        return
    
    print(f"🤖 AI Guidance requested for session {session_id} - Using local outputs model if available")
    
    # Get stored error information from session
    session = sessions[session_id]
    last_error = session.get("last_error")
    
    if not last_error:
        # No error stored - show message
        emit("ai_guidance", {
            "process_id": None,
            "guidance": {
                "summary": "No error detected in the last execution.",
                "why": "The code ran successfully or no execution has occurred yet.",
                "how": ["Run your code to detect errors", "AI Guidance will analyze any runtime or syntax errors"],
                "collaboration_hint": "Write some code and run it to see AI-powered debugging guidance."
            },
            "error_line": None,
            "traceback": ""
        })
        return
    
    # Generate AI Guidance using OLD model
    error_type = last_error.get("raw_error_type") or last_error.get("error_type")
    code = last_error.get("code", "")

    guidance = last_error.get("guidance")
    if not guidance:
        guidance, _ = build_ai_guidance_payload(
            code=code,
            error_subtype=error_type or "RuntimeError",
            line_number=last_error.get("line_number"),
            traceback_text=last_error.get("traceback", "")
        )
        try:
            last_error["guidance"] = guidance
        except Exception:
            pass

    print(f"🤖 Guidance source for session {session_id}: {guidance.get('source', 'unknown')}")

    # Emit AI Guidance event (Local model preferred)
    emit("ai_guidance", {
        "process_id": None,
        "guidance": guidance,
        "error_line": last_error.get("line_number"),
        "traceback": last_error.get("traceback", "")
    }, room=session_id)

@socketio.on("code_analyzer_request")
def handle_code_analyzer_request(data):
    """Handle Code Analyzer requests using Ollama ONLY"""
    session_id = data.get("session_id")
    code = data.get("code", "")
    
    if not code or not session_id:
        emit("code_analyzer_result", {
            "mode": "logic_review",
            "content": "No code provided for analysis.",
            "source": "System"
        })
        return
    
    print(f"🔍 Code Analyzer requested for session {session_id} - Using Ollama")
    
    # Call Ollama ONLY for logic review
    analysis = get_ollama_code_analysis(
        code=code,
        mode="logic_review"
    )
    
    if analysis:
        # Emit code review analysis
        socketio.emit("code_analyzer_result", {
            "mode": "logic_review",
            "content": analysis["content"],
            "source": analysis.get("source", "AI")
        }, room=session_id)
    else:
        # Fallback if Ollama is unavailable
        socketio.emit("code_analyzer_result", {
            "mode": "logic_review",
            "content": "**Code Analyzer unavailable**\n\nCould not connect to Ollama. Please ensure Ollama is running with:\n  ollama serve",
            "source": "System"
        }, room=session_id)

@app.route("/get_invitable_users")
def get_invitable_users():
    """Get personalized list of collaborators user has worked with, filtered by online status.
    
    Creates a gamified invite lobby showing:
    - Only collaborators from previous sessions (session history)
    - Only those currently online (real-time status)
    - Ordered by most recent collaboration
    """
    if "user_id" not in flask_session:
        return jsonify([])

    current_user_id = flask_session["user_id"]
    
    try:
        if not DB_AVAILABLE:
            # Fallback: return all online users if no database
            fallback_users = []
            for uid, data in online_users.items():
                if uid == current_user_id:
                    continue
                c = get_user_credit_profile(uid, recent_limit=1)
                fallback_users.append({
                    "id": uid,
                    "username": data.get("username", f"User {uid}"),
                    "online": True,
                    "last_seen": data.get("last_seen", datetime.utcnow().isoformat()),
                    "collaboration_count": 0,
                    "total_points": c.get("total_points", 0),
                    "level": c.get("level", 1)
                })
            return jsonify(sorted(fallback_users, key=lambda x: (-int(x.get("level", 1)), -int(x.get("total_points", 0)))))
        
        conn = get_db_connection()
        if not conn:
            return jsonify([])

        cursor = conn.cursor(dictionary=True)

        # Get collaborators: users who participated in same sessions
        if CREDIT_DB_READY:
            cursor.execute("""
            SELECT DISTINCT u.id, u.username, MAX(sp.joined_at) AS last_seen,
                   COUNT(DISTINCT sp.session_id) AS collaboration_count,
                   COALESCE(uc.total_points, 0) AS total_points,
                   COALESCE(uc.last_level, 1) AS level
            FROM session_participants sp
            JOIN session_participants sp2 ON sp.session_id = sp2.session_id
            JOIN user u ON sp.user_id = u.id
            LEFT JOIN user_credits uc ON uc.user_id = u.id
            WHERE sp2.user_id = %s
              AND sp.user_id != %s
            GROUP BY u.id, u.username, uc.total_points, uc.last_level
            ORDER BY level DESC, total_points DESC, last_seen DESC
            LIMIT 20
            """, (current_user_id, current_user_id))
        else:
            cursor.execute("""
            SELECT DISTINCT u.id, u.username, MAX(sp.joined_at) AS last_seen,
                   COUNT(DISTINCT sp.session_id) AS collaboration_count,
                   0 AS total_points,
                   1 AS level
            FROM session_participants sp
            JOIN session_participants sp2 ON sp.session_id = sp2.session_id
            JOIN user u ON sp.user_id = u.id
            WHERE sp2.user_id = %s
              AND sp.user_id != %s
            GROUP BY u.id, u.username
            ORDER BY last_seen DESC
            LIMIT 20
            """, (current_user_id, current_user_id))

        users = cursor.fetchall()
        cursor.close()
        conn.close()

        # Attach live online status and collaboration metadata
        result = []
        for u in users:
            is_online = u["id"] in online_users
            result.append({
                "id": u["id"],
                "username": u["username"],
                "online": is_online,
                "last_seen": u["last_seen"].isoformat() if u["last_seen"] else None,
                "collaboration_count": u["collaboration_count"],
                "total_points": int(u.get("total_points") or 0),
                "level": int(u.get("level") or 1)
            })

        result.sort(key=lambda x: (-int(x.get("level", 1)), -int(x.get("total_points", 0)), x.get("username", "").lower()))
        return jsonify(result)

    except Exception as e:
        print(f"❌ Invite fetch error: {e}")
        return jsonify([])


@socketio.on("send_invite")
def handle_send_invite(data):
    """Send a real-time session invitation to an online collaborator.
    
    Gamified features:
    - Only sends to online users (works across pages/tabs)
    - Includes session context and host info
    - Real-time notification with accept/decline options
    """
    target_user_id = data.get("user_id")
    session_id = data.get("session_id")
    from_name = data.get("from_name", flask_session.get("username", "Unknown"))
    sender_user_id = flask_session.get("user_id")
    
    print(f"\n📨 INVITE HANDLER: Received send_invite request")
    print(f"   From: {from_name} (user_id: {sender_user_id})")
    print(f"   To: user_id {target_user_id}")
    print(f"   Session: {session_id}")
    
    # Verify target is online
    if target_user_id not in online_users:
        print(f"❌ Target user (ID: {target_user_id}) is NOT online")
        print(f"   Online users: {list(online_users.keys())}")
        emit("invite_error", {
            "message": "User is no longer online"
        })
        return
    
    # Get target's socket IDs (they may be on multiple pages/tabs)
    target_sids = online_users[target_user_id]["sids"]
    target_username = online_users[target_user_id]["username"]
    
    print(f"✅ Target user '{target_username}' is online")
    print(f"   Sockets to send to: {target_sids}")
    
    # Get session details for context
    session_name = "Collaborative Coding Session"
    if session_id in sessions:
        session_name = sessions[session_id].get("session_name", session_name)
    
    # Prepare the invite payload
    invite_payload = {
        "session_id": session_id,
        "from_name": from_name,
        "session_name": session_name,
        "timestamp": datetime.utcnow().isoformat(),
        "invite_id": str(uuid.uuid4())[:8]
    }
    
    # Send to all the target user's sockets (they might have multiple connections)
    for i, target_sid in enumerate(target_sids, 1):
        print(f"   → Sending invite to socket {i}/{len(target_sids)}: {target_sid}")
        emit("receive_invite", invite_payload, room=target_sid)
    
    print(f"✅ Invite sent successfully to {target_username} ({len(target_sids)} connection(s))")
    print()

@socketio.on("accept_invite")
def handle_accept_invite(data):
    """Handle invitation acceptance - notify host and prepare session join.
    
    Gamified features:
    - Instant notification to host
    - Auto-redirect to session
    - Updates collaboration history
    """
    session_id = data.get("session_id")
    username = flask_session.get("username", "Guest")
    user_id = flask_session.get("user_id")
    
    if session_id not in sessions:
        emit("error", {"message": "Session no longer exists"})
        return
    
    print(f"✅ {username} accepted invite to session {session_id}")
    
    # Notify the host that someone accepted
    session = sessions[session_id]
    emit("invite_accepted", {
        "session_id": session_id,
        "username": username,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }, room=session_id)

@socketio.on("join_session")
def handle_join(data):
    session_id = data.get("session_id")
    name = data.get("name", "Anonymous")
    sid = request.sid

    if session_id not in sessions:
        emit("error", {"msg": "Session not found"})
        return

    join_room(session_id)
    session = sessions[session_id]

    # Initialize session metadata for MOM
    if "created_at" not in session:
        session["created_at"] = datetime.utcnow().isoformat()

    session.setdefault("executions", [])
    session.setdefault("name_by_sid", {})
    session.setdefault("all_participants", [])
    session.setdefault("chat_messages", [])
    session.setdefault("participants", {})

    # Set host + writer if first user
    if not session["participants"]:
        session["host_id"] = sid
        session["writer_id"] = sid
        _log_control_event(
            session,
            action="assign_host_writer",
            from_sid=None,
            to_sid=sid,
            reason=f"{name} became host and writer on session start"
        )
        print(f"👑 {name} is now host of session {session_id}")

    # Add to in-memory session
    session["participants"][sid] = {
        "name": name,
        "sid": sid,
        "user_id": flask_session.get("user_id")
    }

    session["name_by_sid"][sid] = name
    session.setdefault("user_id_by_sid", {})
    session["user_id_by_sid"][sid] = flask_session.get("user_id")
    if name not in session["all_participants"]:
        session["all_participants"].append(name)

    # ✅ STORE PARTICIPANT IN DATABASE
    if "user_id" in flask_session:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT IGNORE INTO session_participants (session_id, user_id)
                VALUES (%s, %s)
            """, (session_id, flask_session["user_id"]))

            conn.commit()
            cursor.close()
            conn.close()

            print("🗄️ Participant stored in DB")

        except Exception as e:
            print("❌ DB Error (session_participants):", e)

    # Send current files and active tab to new user
    emit("session_files", {
        "files": session.get("files", {}),
        "active_file": session.get("active_file", "main.py")
    })

    # Send chat history
    if session["chat_messages"]:
        emit("chat_history", {"messages": session["chat_messages"][-50:]})

    # Notify all users
    emit_participants_update(session_id)

    print(f"👤 {name} joined session {session_id}")

def handle_user_leave():
    """Handle when a user leaves the session"""
    sid = request.sid
    for session_id, session in sessions.items():
        if sid in session["participants"]:
            user_name = session["participants"][sid]["name"]
            
            # Remove user from participants
            del session["participants"][sid]
            
            # Handle host transfer if host left
            if session["host_id"] == sid:
                if session["participants"]:
                    # Transfer host to first available participant
                    new_host_sid = next(iter(session["participants"].keys()))
                    session["host_id"] = new_host_sid
                    session["writer_id"] = new_host_sid
                    _log_control_event(
                        session,
                        action="host_transfer",
                        from_sid=sid,
                        to_sid=new_host_sid,
                        reason=f"Host left; transferred to {session['participants'][new_host_sid]['name']}"
                    )
                    new_host_name = session["participants"][new_host_sid]["name"]
                    print(f"👑 Host transferred to {new_host_name} in session {session_id}")
                else:
                    # No participants left, clear host
                    session["host_id"] = None
                    session["writer_id"] = None
                    _log_control_event(
                        session,
                        action="host_cleared",
                        from_sid=sid,
                        to_sid=None,
                        reason="Host left and no participants remained"
                    )
            
            # Update all clients
            emit_participants_update(session_id)
            
            print(f"👤 {user_name} left session {session_id}")
            break

def emit_participants_update(session_id):
    """Send updated participants list to all clients in the session"""
    if session_id in sessions:
        session = sessions[session_id]
        emit("participants_update", {
            "participants": session["participants"],
            "writer_id": session["writer_id"],
            "host_id": session["host_id"]
        }, room=session_id)

# Add these WebRTC signaling handlers to your existing app.py

@socketio.on("get_participants")
def handle_get_participants(data):
    """Get all participants in session"""
    session_id = data.get("session_id")
    sid = request.sid
    
    if session_id in sessions:
        session = sessions[session_id]
        # Notify about existing participants
        emit("participants_update", {
            "participants": session["participants"],
            "writer_id": session["writer_id"],
            "host_id": session["host_id"]
        })

@socketio.on("code_change")
def handle_code_change(data):
    session_id = data.get("session_id")
    content = data.get("content", "")
    file_name = data.get("file_name") or data.get("file") or None
    sid = request.sid
    client_timestamp = data.get("timestamp")  # Client-side timestamp for latency tracking
    
    if session_id in sessions:
        session = sessions[session_id]
        
        # Calculate sync latency if client provided timestamp
        if client_timestamp:
            try:
                server_receive_time = datetime.utcnow().timestamp() * 1000  # milliseconds
                latency_ms = server_receive_time - client_timestamp
                
                # Initialize latency_metrics if not present (for old sessions)
                if "latency_metrics" not in session:
                    session["latency_metrics"] = {
                        "code_sync": [],
                        "chat_messages": [],
                        "network_rtt": {},
                        "stats": {
                            "avg_code_sync_ms": 0,
                            "avg_chat_ms": 0,
                            "avg_network_rtt_ms": 0,
                            "max_code_sync_ms": 0,
                            "max_chat_ms": 0,
                            "total_measurements": 0
                        }
                    }
                
                # Store latency measurement
                latency_record = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "from_sid": sid,
                    "latency_ms": round(latency_ms, 2),
                    "type": "code_sync",
                    "filename": file_name or session.get("active_file", "main.py")
                }
                session["latency_metrics"]["code_sync"].append(latency_record)
                
                # Write to log file automatically
                _write_latency_to_file(session_id, "code_sync", latency_record)
                
                # Update statistics
                _update_latency_stats(session, latency_ms, "code_sync")
            except Exception as e:
                print(f"⚠️ Latency calculation error: {e}")
        
        # Only allow the current writer to make changes
        if session["writer_id"] == sid:
            if not file_name:
                file_name = session.get("active_file", "main.py")
            
            # Update the file content
            if "files" not in session:
                session["files"] = {}
            session["files"][file_name] = content
            
            # Track edit count for this user
            if "edit_counts" not in session:
                session["edit_counts"] = {}
            session["edit_counts"][sid] = session["edit_counts"].get(sid, 0) + 1
            
            # Broadcast to other participants with server timestamp
            emit("code_update", {
                "content": content,
                "file_name": file_name,
                "writer_sid": sid,
                "server_timestamp": datetime.utcnow().timestamp() * 1000
            }, room=session_id, include_self=False)
            
            # print(f"✏️ Code updated by {session['participants'][sid]['name']} in {file_name}")

@socketio.on("add_tab")
def handle_add_tab(data):
    """Host or writer can add a new file tab."""
    session_id = data.get("session_id")
    requested_name = (data.get("file_name") or "").strip() or None
    sid = request.sid
    if session_id not in sessions:
        emit("error", {"msg": "Session not found"})
        return
    session = sessions[session_id]
    if sid not in (session.get("host_id"), session.get("writer_id")):
        emit("error", {"msg": "Only host or writer can add files"})
        return
    base_name = requested_name or "file.py"
    name = base_name
    i = 2
    if "files" not in session:
        session["files"] = {}
    while name in session["files"]:
        if "." in base_name:
            stem, ext = base_name.rsplit(".", 1)
            name = f"{stem}{i}.{ext}"
        else:
            name = f"{base_name}{i}"
        i += 1
    session["files"][name] = ""
    emit("tab_added", {"file_name": name, "content": ""}, room=session_id)
    print(f"➕ Tab added {name} in session {session_id}")

@socketio.on("remove_tab")
def handle_remove_tab(data):
    """Host or writer: remove a file tab (cannot remove last file)."""
    session_id = data.get("session_id")
    file_name = (data.get("file_name") or "").strip()
    sid = request.sid
    if session_id not in sessions:
        emit("error", {"msg": "Session not found"})
        return
    session = sessions[session_id]
    if sid not in (session.get("host_id"), session.get("writer_id")):
        emit("error", {"msg": "Only host or writer can remove files"})
        return
    if not file_name or file_name not in session.get("files", {}):
        emit("error", {"msg": "File not found"})
        return
    if len(session["files"]) <= 1:
        emit("error", {"msg": "Cannot remove the last file"})
        return
    was_active = session.get("active_file") == file_name
    del session["files"][file_name]
    new_active = session.get("active_file")
    if was_active:
        new_active = sorted(session["files"].keys())[0]
        session["active_file"] = new_active
    emit("tab_removed", {"file_name": file_name, "active_file": new_active}, room=session_id)
    print(f"➖ Tab removed {file_name} in session {session_id}")

@socketio.on("rename_tab")
def handle_rename_tab(data):
    """Host or writer can rename a file tab."""
    session_id = data.get("session_id")
    old_name = (data.get("old_name") or "").strip()
    new_name = (data.get("new_name") or "").strip()
    sid = request.sid
    if session_id not in sessions:
        emit("error", {"msg": "Session not found"})
        return
    session = sessions[session_id]
    if sid not in (session.get("host_id"), session.get("writer_id")):
        emit("error", {"msg": "Only host or writer can rename files"})
        return
    if not old_name or not new_name or old_name not in session.get("files", {}):
        emit("error", {"msg": "Invalid file name"})
        return
    if new_name in session["files"] and new_name != old_name:
        emit("error", {"msg": "A file with the new name already exists"})
        return
    session["files"][new_name] = session["files"].pop(old_name)
    if session.get("active_file") == old_name:
        session["active_file"] = new_name
    emit("tab_renamed", {"old_name": old_name, "new_name": new_name}, room=session_id)
    print(f"✏️ Tab renamed {old_name} -> {new_name} in session {session_id}")

@socketio.on("tab_change")
def handle_tab_change(data):
    """Host or writer may change the active tab for the session."""
    session_id = data.get("session_id")
    file_name = (data.get("file_name") or "").strip()
    sid = request.sid
    if session_id not in sessions:
        emit("error", {"msg": "Session not found"})
        return
    session = sessions[session_id]
    if sid not in (session.get("host_id"), session.get("writer_id")):
        return
    if not file_name or file_name not in session.get("files", {}):
        return
    session["active_file"] = file_name
    emit("active_tab_changed", {"file_name": file_name}, room=session_id)
    print(f"📄 Active tab switched to {file_name} in session {session_id}")

@socketio.on("grant_write")
def handle_grant_write(data):
    """Grant write access to another user - captures current writer's code before handover"""
    session_id = data.get("session_id")
    target_sid = data.get("target_sid")
    sid = request.sid
    
    if session_id in sessions:
        session = sessions[session_id]
        
        # Only host or current writer can grant write access
        if sid not in (session.get("host_id"), session.get("writer_id")):
            emit("error", {"msg": "Only host or current writer can grant write access"})
            return
        
        if target_sid not in session["participants"]:
            emit("error", {"msg": "Target user not in session"})
            return
        
        # Capture code contribution BEFORE transferring write permission
        current_writer_sid = session.get("writer_id")
        if current_writer_sid:
            # Get current active file content
            active_file = session.get("active_file", "main.py")
            current_code = session.get("files", {}).get(active_file, "")
            
            # Initialize user_contributions if needed
            if "user_contributions" not in session:
                session["user_contributions"] = {}
            
            if current_writer_sid not in session["user_contributions"]:
                session["user_contributions"][current_writer_sid] = {
                    "code_snapshots": [],
                    "edits": []
                }
            
            # Capture the code snapshot with timestamp
            snapshot = {
                "timestamp": datetime.utcnow().isoformat(),
                "file": active_file,
                "code": current_code,
                "handover_reason": f"Granted write to {session['participants'][target_sid]['name']}"
            }
            session["user_contributions"][current_writer_sid]["code_snapshots"].append(snapshot)
            
            print(f"📸 Captured code snapshot for {session['participants'][current_writer_sid]['name']} before handover")
        
        # Transfer write permission
        old_writer = session.get("writer_id")
        session["writer_id"] = target_sid
        
        # Log control event
        _log_control_event(
            session,
            action="grant_write",
            from_sid=sid,
            to_sid=target_sid,
            reason=f"Write permission granted to {session['participants'][target_sid]['name']}"
        )
        
        # Notify all participants
        emit_participants_update(session_id)
        
        emit("write_granted", {
            "new_writer_sid": target_sid,
            "new_writer_name": session["participants"][target_sid]["name"]
        }, room=session_id)
        
        print(f"✍️ Write access granted to {session['participants'][target_sid]['name']} in session {session_id}")

@socketio.on("revoke_write")
def handle_revoke_write(data):
    """Revoke write access (host becomes writer) - captures current writer's code before revocation"""
    session_id = data.get("session_id")
    sid = request.sid
    
    if session_id in sessions:
        session = sessions[session_id]
        
        # Only host can revoke
        if sid != session.get("host_id"):
            emit("error", {"msg": "Only host can revoke write access"})
            return
        
        # Capture code contribution BEFORE revoking write permission
        current_writer_sid = session.get("writer_id")
        if current_writer_sid and current_writer_sid != sid:
            # Get current active file content
            active_file = session.get("active_file", "main.py")
            current_code = session.get("files", {}).get(active_file, "")
            
            # Initialize user_contributions if needed
            if "user_contributions" not in session:
                session["user_contributions"] = {}
            
            if current_writer_sid not in session["user_contributions"]:
                session["user_contributions"][current_writer_sid] = {
                    "code_snapshots": [],
                    "edits": []
                }
            
            # Capture the code snapshot with timestamp
            snapshot = {
                "timestamp": datetime.utcnow().isoformat(),
                "file": active_file,
                "code": current_code,
                "handover_reason": "Host revoked write permission"
            }
            session["user_contributions"][current_writer_sid]["code_snapshots"].append(snapshot)
            
            print(f"📸 Captured code snapshot for {session['participants'][current_writer_sid]['name']} before revocation")
        
        # Revoke write permission (host becomes writer)
        old_writer = session.get("writer_id")
        session["writer_id"] = sid
        
        # Log control event
        _log_control_event(
            session,
            action="revoke_write",
            from_sid=old_writer,
            to_sid=sid,
            reason="Host revoked write permission"
        )
        
        # Notify all participants
        emit_participants_update(session_id)
        
        emit("write_revoked", {
            "new_writer_sid": sid,
            "host_name": session["participants"][sid]["name"]
        }, room=session_id)
        
        print(f"🔒 Write access revoked, host {session['participants'][sid]['name']} is now writer in session {session_id}")

# WebRTC signaling handlers for audio implementation
@socketio.on("webrtc_offer")
def handle_webrtc_offer(data):
    target_sid = data.get("target")
    offer = data.get("sdp")
    if target_sid:
        emit("webrtc_offer", {
            "sdp": offer,
            "sid": request.sid
        }, room=target_sid)

@socketio.on("webrtc_answer")
def handle_webrtc_answer(data):
    target_sid = data.get("target")
    answer = data.get("sdp")
    if target_sid:
        emit("webrtc_answer", {
            "sdp": answer,
            "sid": request.sid
        }, room=target_sid)

@socketio.on("webrtc_ice_candidate")
def handle_webrtc_ice_candidate(data):
    target_sid = data.get("target")
    candidate = data.get("candidate")
    if target_sid:
        emit("webrtc_ice_candidate", {
            "candidate": candidate,
            "sid": request.sid
        }, room=target_sid)

# ==================== CHAT FUNCTIONALITY ADDED BELOW ====================

@socketio.on("send_chat_message")
def handle_chat_message(data):
    """Handle chat messages from clients"""
    session_id = data.get("session_id")
    message_text = data.get("message", "").strip()
    sid = request.sid
    client_timestamp = data.get("timestamp")  # Client-side timestamp for latency tracking
    
    if not session_id or session_id not in sessions:
        return
    
    if not message_text:
        return
    
    session = sessions[session_id]
    if sid not in session["participants"]:
        return
    
    # Calculate message latency if client provided timestamp
    if client_timestamp:
        try:
            server_receive_time = datetime.utcnow().timestamp() * 1000  # milliseconds
            latency_ms = server_receive_time - client_timestamp
            
            # Initialize latency_metrics if not present (for old sessions)
            if "latency_metrics" not in session:
                session["latency_metrics"] = {
                    "code_sync": [],
                    "chat_messages": [],
                    "network_rtt": {},
                    "stats": {
                        "avg_code_sync_ms": 0,
                        "avg_chat_ms": 0,
                        "avg_network_rtt_ms": 0,
                        "max_code_sync_ms": 0,
                        "max_chat_ms": 0,
                        "total_measurements": 0
                    }
                }
            
            # Store latency measurement
            sender_name = session["participants"][sid]["name"]
            latency_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "from_sid": sid,
                "username": sender_name,
                "latency_ms": round(latency_ms, 2),
                "type": "chat_message"
            }
            session["latency_metrics"]["chat_messages"].append(latency_record)
            
            # Write to log file automatically
            _write_latency_to_file(session_id, "chat_message", latency_record)
            
            # Update statistics
            _update_latency_stats(session, latency_ms, "chat_message")
        except Exception as e:
            print(f"⚠️ Chat latency calculation error: {e}")
    
    # Get sender info
    sender_info = session["participants"][sid]
    sender_name = sender_info["name"]
    
    # Create chat message
    chat_message = {
        "id": str(uuid.uuid4())[:8],
        "sender_sid": sid,
        "sender_name": sender_name,
        "message": message_text,
        "timestamp": time.time(),
        "time_display": datetime.now().strftime("%H:%M"),
        "server_timestamp": datetime.utcnow().timestamp() * 1000
    }
    
    # Store message in session chat history
    session["chat_messages"].append(chat_message)
    
    # Keep only last 100 messages
    if len(session["chat_messages"]) > 100:
        session["chat_messages"] = session["chat_messages"][-100:]
    
    # Broadcast to all participants in the session
    emit("new_chat_message", chat_message, room=session_id)
    
    print(f"💬 {sender_name} sent message in session {session_id}: {message_text[:50]}...")

@socketio.on("get_chat_history")
def handle_get_chat_history(data):
    """Send chat history to joining user"""
    session_id = data.get("session_id")
    sid = request.sid
    
    if session_id in sessions and sessions[session_id]["chat_messages"]:
        session = sessions[session_id]
        chat_history = session["chat_messages"][-50:]  # Last 50 messages
        emit("chat_history", {"messages": chat_history})


def _write_latency_to_file(session_id, metric_type, data):
    """
    Automatically write latency measurement to a text file with persistence.
    Creates/appends to: data/latency_logs/session_<session_id>.txt
    This function ensures data is persisted throughout the entire session,
    even with many concurrent users.
    """
    try:
        log_file = os.path.join(LATENCY_LOG_DIR, f"session_{session_id}.txt")
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Include milliseconds
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        with open(log_file, "a", encoding="utf-8") as f:
            if metric_type == "code_sync":
                f.write(f"[{timestamp}] CODE SYNC | User: {data.get('from_sid', 'Unknown')[:8]} | "
                       f"Latency: {data.get('latency_ms')}ms | File: {data.get('filename', 'N/A')}\n")
            
            elif metric_type == "chat_message":
                f.write(f"[{timestamp}] CHAT MSG  | User: {data.get('username', 'Unknown')} | "
                       f"Latency: {data.get('latency_ms')}ms\n")
            
            elif metric_type == "network_rtt":
                f.write(f"[{timestamp}] NET RTT   | User: {data.get('username', 'Unknown')} | "
                       f"RTT: {data.get('rtt_ms')}ms\n")
            
            # Force flush to ensure data is written to disk immediately
            f.flush()
            os.fsync(f.fileno())
    
    except Exception as e:
        print(f"⚠️ Failed to write latency log: {e}")
        # Attempt recovery: create backup file if main fails
        try:
            backup_file = os.path.join(LATENCY_LOG_DIR, f"session_{session_id}_backup.txt")
            with open(backup_file, "a", encoding="utf-8") as bf:
                bf.write(f"[RECOVERY] {str(data)}\n")
                bf.flush()
        except:
            pass


def _update_latency_stats(session, latency_ms, metric_type):
    """Update latency statistics for a session."""
    stats = session["latency_metrics"]["stats"]
    
    if metric_type == "code_sync":
        code_latencies = [m["latency_ms"] for m in session["latency_metrics"]["code_sync"]]
        if code_latencies:
            stats["avg_code_sync_ms"] = round(sum(code_latencies) / len(code_latencies), 2)
            stats["max_code_sync_ms"] = round(max(code_latencies), 2)
    
    elif metric_type == "chat_message":
        chat_latencies = [m["latency_ms"] for m in session["latency_metrics"]["chat_messages"]]
        if chat_latencies:
            stats["avg_chat_ms"] = round(sum(chat_latencies) / len(chat_latencies), 2)
            stats["max_chat_ms"] = round(max(chat_latencies), 2)
    
    elif metric_type == "network_rtt":
        rtt_values = []
        for sid_data in session["latency_metrics"]["network_rtt"].values():
            rtt_values.extend([m["rtt_ms"] for m in sid_data.get("measurements", [])])
        if rtt_values:
            stats["avg_network_rtt_ms"] = round(sum(rtt_values) / len(rtt_values), 2)
    
    stats["total_measurements"] = (
        len(session["latency_metrics"]["code_sync"]) +
        len(session["latency_metrics"]["chat_messages"]) +
        sum(len(data.get("measurements", [])) for data in session["latency_metrics"]["network_rtt"].values())
    )


@socketio.on("ping_latency")
def handle_ping_latency(data):
    """Handle ping request from client to measure network RTT."""
    session_id = data.get("session_id")
    client_timestamp = data.get("timestamp")
    sid = request.sid
    
    if not session_id or session_id not in sessions:
        return
    
    # Send pong back immediately with both timestamps
    emit("pong_latency", {
        "client_timestamp": client_timestamp,
        "server_timestamp": datetime.utcnow().timestamp() * 1000
    })


@socketio.on("latency_measurement")
def handle_latency_measurement(data):
    """Receive RTT measurement from client after ping-pong."""
    session_id = data.get("session_id")
    rtt_ms = data.get("rtt_ms")
    sid = request.sid
    
    if not session_id or session_id not in sessions or rtt_ms is None:
        return
    
    session = sessions[session_id]
    
    # Initialize latency_metrics if not present (for old sessions)
    if "latency_metrics" not in session:
        session["latency_metrics"] = {
            "code_sync": [],
            "chat_messages": [],
            "network_rtt": {},
            "stats": {
                "avg_code_sync_ms": 0,
                "avg_chat_ms": 0,
                "avg_network_rtt_ms": 0,
                "max_code_sync_ms": 0,
                "max_chat_ms": 0,
                "total_measurements": 0
            }
        }
    
    username = session.get("participants", {}).get(sid, {}).get("name", "Unknown")
    
    # Initialize RTT tracking for this user if needed
    if sid not in session["latency_metrics"]["network_rtt"]:
        session["latency_metrics"]["network_rtt"][sid] = {
            "username": username,
            "measurements": []
        }
    
    # Store RTT measurement
    measurement = {
        "timestamp": datetime.utcnow().isoformat(),
        "rtt_ms": round(rtt_ms, 2)
    }
    session["latency_metrics"]["network_rtt"][sid]["measurements"].append(measurement)
    
    # Write to log file automatically
    _write_latency_to_file(session_id, "network_rtt", {
        "username": username,
        "rtt_ms": round(rtt_ms, 2)
    })
    
    # Keep only last 100 measurements per user to avoid memory issues
    if len(session["latency_metrics"]["network_rtt"][sid]["measurements"]) > 100:
        session["latency_metrics"]["network_rtt"][sid]["measurements"] = \
            session["latency_metrics"]["network_rtt"][sid]["measurements"][-100:]
    
    # Update statistics
    _update_latency_stats(session, rtt_ms, "network_rtt")


def _write_latency_session_summary(session_id, session):
    """
    Write a comprehensive latency summary at the end of session.
    This ensures all latency data is properly recorded for long-running sessions with many users.
    """
    try:
        log_file = os.path.join(LATENCY_LOG_DIR, f"session_{session_id}.txt")
        summary_file = os.path.join(LATENCY_LOG_DIR, f"session_{session_id}_summary.txt")
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Get statistics
        stats = session.get("latency_metrics", {}).get("stats", {})
        participants = session.get("participants", {})
        all_participants = session.get("all_participants", [])
        
        # Build summary
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        summary_text = f"""
================================================================================
SESSION LATENCY SUMMARY REPORT
================================================================================
Generated: {timestamp}
Session ID: {session_id}

PARTICIPANTS: {len(all_participants)}
Users: {', '.join(all_participants)}

================================================================================
LATENCY STATISTICS
================================================================================
Code Sync:
  - Average Latency: {stats.get('avg_code_sync_ms', 'N/A')}ms
  - Maximum Latency: {stats.get('max_code_sync_ms', 'N/A')}ms
  - Total Measurements: {len(session.get('latency_metrics', {}).get('code_sync', []))}

Chat Messages:
  - Average Latency: {stats.get('avg_chat_ms', 'N/A')}ms
  - Maximum Latency: {stats.get('max_chat_ms', 'N/A')}ms
  - Total Measurements: {len(session.get('latency_metrics', {}).get('chat_messages', []))}

Network RTT:
  - Average RTT: {stats.get('avg_network_rtt_ms', 'N/A')}ms
  - Maximum RTT: {stats.get('max_network_rtt_ms', 'N/A')}ms
  - Total Measurements: {sum(len(data.get('measurements', [])) for data in session.get('latency_metrics', {}).get('network_rtt', {}).values())}

Total Latency Events Recorded: {stats.get('total_measurements', 0)}

================================================================================
NOTES
================================================================================
- All latency measurements are stored in: session_{session_id}.txt
- This summary is automatically generated when the session ends
- Data is persistent throughout the entire session duration
- System supports multiple concurrent users without data loss

================================================================================
"""
        
        # Write summary to file
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(summary_text)
            f.flush()
            os.fsync(f.fileno())
        
        # Also append summary to main log file
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(summary_text)
            f.flush()
            os.fsync(f.fileno())
        
        print(f"✅ Latency session summary written to: {summary_file}")
        
    except Exception as e:
        print(f"⚠️ Failed to write latency session summary: {e}")


@app.route("/latency_stats/<session_id>", methods=["GET"])
def get_latency_stats(session_id):
    """Get latency statistics for a session."""
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404
    
    session = sessions[session_id]
    
    # Initialize latency_metrics if not present (for old sessions)
    if "latency_metrics" not in session:
        return jsonify({
            "session_id": session_id,
            "message": "No latency data available for this session",
            "statistics": {},
            "user_network_rtt": {},
            "recent_code_sync": [],
            "recent_chat_messages": []
        })
    
    metrics = session["latency_metrics"]
    
    # Prepare user-wise RTT summary
    user_rtt_summary = {}
    for sid, rtt_data in metrics.get("network_rtt", {}).items():
        measurements = rtt_data.get("measurements", [])
        if measurements:
            rtt_values = [m["rtt_ms"] for m in measurements]
            user_rtt_summary[rtt_data["username"]] = {
                "avg_rtt_ms": round(sum(rtt_values) / len(rtt_values), 2),
                "min_rtt_ms": round(min(rtt_values), 2),
                "max_rtt_ms": round(max(rtt_values), 2),
                "measurements_count": len(measurements),
                "last_measurement": measurements[-1]
            }
    
    # Recent code sync latencies (last 20)
    recent_code_sync = metrics.get("code_sync", [])[-20:]
    
    # Recent chat latencies (last 20)
    recent_chat = metrics.get("chat_messages", [])[-20:]
    
    return jsonify({
        "session_id": session_id,
        "statistics": metrics.get("stats", {}),
        "user_network_rtt": user_rtt_summary,
        "recent_code_sync": recent_code_sync,
        "recent_chat_messages": recent_chat,
        "total_code_sync_measurements": len(metrics.get("code_sync", [])),
        "total_chat_measurements": len(metrics.get("chat_messages", [])),
        "total_network_measurements": sum(
            len(data.get("measurements", [])) 
            for data in metrics.get("network_rtt", {}).values()
        )
    })


@app.route("/upload_dataset", methods=["POST"])
def upload_dataset():
    """
    Upload a dataset file for a session.
    Expects multipart/form-data with fields:
      - session_id
      - file (the file to upload)
    """
    if "file" not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    file = request.files["file"]
    session_id = request.form.get("session_id")
    if not session_id:
        return jsonify({"status": "error", "message": "session_id is required"}), 400
    if session_id not in sessions:
        return jsonify({"status": "error", "message": "Session not found"}), 404
    if file.filename == "":
        return jsonify({"status": "error", "message": "No selected file"}), 400

    filename = secure_filename(file.filename)
    session_dir = os.path.join(UPLOAD_ROOT, session_id)
    os.makedirs(session_dir, exist_ok=True)

    save_path = os.path.join(session_dir, filename)
    try:
        file.save(save_path)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to save file: {e}"}), 500

    return jsonify({"status": "success", "filename": filename, "message": "Uploaded"})


@app.route("/list_datasets", methods=["GET"])
def list_datasets():
    """
    List uploaded dataset files for a session.
    Query: ?session_id=<id>
    """
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"status": "error", "message": "session_id is required"}), 400
    session_dir = os.path.join(UPLOAD_ROOT, session_id)
    files = []
    if os.path.isdir(session_dir):
        for root, _, filenames in os.walk(session_dir):
            for fn in filenames:
                rel_dir = os.path.relpath(root, session_dir)
                rel_path = fn if rel_dir == "." else os.path.join(rel_dir, fn)
                files.append(rel_path.replace("\\", "/"))
    return jsonify({"status": "success", "files": files})


@app.route("/datasets/<session_id>/<path:filename>", methods=["GET"])
def download_dataset(session_id, filename):
    """Download a dataset file for a session (safe send)."""
    session_dir = os.path.join(UPLOAD_ROOT, session_id)
    if not os.path.isdir(session_dir):
        return "Not found", 404
    # send_from_directory will validate and safely serve
    return flask.send_from_directory(session_dir, filename, as_attachment=True)


def _generate_ai_summary_groq(raw_mom_data):
    if not groq_client:
        return None
    prompt = (
        "You are a professional meeting assistant. Provide a concise, chronological summary "
        "of a collaborative coding session from start to end. Include: (1) a short timeline "
        "covering the session start and end, (2) key runs in order with their outcomes "
        "(success or error), (3) notable fixes or changes made after errors, and (4) the final "
        "overall outcome. Keep it under 200 words.\n\n"
        "Please review this session data and produce the chronological summary described above:\n\n"
        f"{raw_mom_data}"
    )
    models = ["mixtral-8x7b-32768", "llama-3-70b-8192", "llama2-70b-4096"]
    for model_name in models:
        try:
            response = groq_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "Be concise and focus on key events."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.7
            )
            if response.choices and response.choices[0].message.content:
                print(f"✅ Groq model '{model_name}' succeeded")
                return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️ Groq model '{model_name}' failed: {e}")
    return None

def _generate_ai_summary_mistral(raw_mom_data):
    if not (MISTRAL_API_KEY and MISTRAL_AVAILABLE):
        return None
    try:
        headers = {
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "mistral-large-latest",
            "messages": [
                {"role": "system", "content": "Be a concise meeting assistant focusing on key events."},
                {"role": "user", "content": (
                    "Provide a concise chronological session summary under 200 words. "
                    "Include start/end, ordered runs with outcomes, fixes after errors, and final outcome.\n\n" + raw_mom_data
                )}
            ],
            "max_tokens": 400,
            "temperature": 0.7
        }
        resp = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=payload, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            # Mistral returns choices[0].message.content
            content = (data.get("choices") or [{}])[0].get("message", {}).get("content")
            if content:
                print("✅ Mistral summary generated")
                return content.strip()
        else:
            print(f"⚠️ Mistral API error {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"⚠️ Mistral API call failed: {e}")
    return None

def _generate_ai_summary(raw_mom_data):
    """Try Mistral first if available, else Groq, else None."""
    summary = _generate_ai_summary_mistral(raw_mom_data)
    if summary:
        return summary
    return _generate_ai_summary_groq(raw_mom_data)


def _build_mom_text(session):
    """Build human-friendly MOM text without Markdown symbols."""
    # Timeline
    try:
        created_at = session.get("created_at")
        start_dt = datetime.fromisoformat(created_at) if created_at else datetime.utcnow()
    except Exception:
        start_dt = datetime.utcnow()
    end_dt = datetime.utcnow()
    duration_seconds = max(1, int((end_dt - start_dt).total_seconds()))
    duration_mins = duration_seconds // 60
    duration_formatted = f"{duration_mins}m {duration_seconds % 60}s"

    participants_live = [p["name"] for p in session.get("participants", {}).values()]
    participants = session.get("all_participants") or participants_live or ["(none)"]

    executions = session.get("executions", [])
    
    # Build plain-text execution blocks
    runs_text = []
    for i, ex in enumerate(executions, start=1):
        st = ex.get("start_time") or ""
        # Parse time to show only HH:MM:SS format
        try:
            if st:
                st_parsed = datetime.fromisoformat(st)
                st = st_parsed.strftime("%H:%M:%S")
        except Exception:
            pass
        
        status = ex.get('status') or 'finished'
        status_emoji = "✅" if status == "completed" else "⚠️" if status == "error" else "⏸️"
        
        code_preview = (ex.get("code") or "").strip()
        # Show only first 5 lines of code
        code_lines = code_preview.split("\n")
        if len(code_lines) > 5:
            code_preview = "\n".join(code_lines[:5]) + "\n..."
        
        stdout_tail = "".join((ex.get("stdout") or [])[-10:]).strip()
        stderr_tail = "".join((ex.get("stderr") or [])[-6:]).strip()
        
        # Limit output length
        if len(stdout_tail) > 500:
            stdout_tail = "...\n" + stdout_tail[-500:]
        if len(stderr_tail) > 300:
            stderr_tail = "...\n" + stderr_tail[-300:]
        
        # Plain text formatting (no **, ##, or code fences)
        lines = []
        lines.append(f"Execution {i} {status_emoji}")
        lines.append(f"Time: {st}")
        lines.append(f"Status: {status.capitalize()}")
        if code_preview:
            lines.append("Code:")
            lines.append(code_preview)
        if stdout_tail:
            lines.append("Output:")
            lines.append(stdout_tail)
        if stderr_tail:
            lines.append("Errors:")
            lines.append(stderr_tail)
        runs_text.append("\n".join(lines))

    runs_block = ("\n\n------\n\n".join(runs_text)) if runs_text else "No code executions in this session."

    # Build formatted MOM data (plain text)
    formatted_mom = (
        "Session Overview:\n"
        f"Duration: {duration_formatted}\n"
        f"Participants: {', '.join(participants)}\n"
        f"Total Executions: {len(executions)}\n\n"
        "Code Executions:\n\n"
        f"{runs_block}"
    )

    # Build raw data for AI summary (technical details only for AI)
    raw_mom_for_ai = (
        f"Session Duration: {duration_formatted}\n"
        f"Participants: {', '.join(participants)}\n"
        f"Total Executions: {len(executions)}\n\n"
        "Execution Details:\n"
    )
    for i, ex in enumerate(executions, start=1):
        status = ex.get('status') or 'finished'
        code = (ex.get("code") or "").strip()[:200]
        stdout = "".join((ex.get("stdout") or [])[:5]).strip()[:200]
        stderr = "".join((ex.get("stderr") or [])[:3]).strip()[:200]
        raw_mom_for_ai += f"\nRun {i}: {status}\nCode: {code}\nOutput: {stdout or '(none)'}\nErrors: {stderr or '(none)'}\n"

    # Try to get AI-powered summary
    ai_summary = _generate_ai_summary(raw_mom_for_ai)
    
    if ai_summary:
        ai_summary_clean = ai_summary.strip()
        mom_text = (
            "✨ AI Summary:\n"
            f"{ai_summary_clean}\n\n"
            f"{formatted_mom}"
        )
    else:
        mom_text = formatted_mom

    return mom_text

@app.route("/mom/<session_id>", methods=["GET"])
def get_mom(session_id):
    """Return Minutes of Meeting for a session without any AI, based purely on session data."""
    if session_id not in sessions:
        return jsonify({"status": "error", "message": "Session not found"}), 404
    session = sessions[session_id]
    mom_text = _build_mom_text(session)
    return jsonify({"status": "success", "session_id": session_id, "mom": mom_text})


def _build_contribution_summary(session):
    participants = session.get("participants", {})
    name_by_sid = session.get("name_by_sid", {})
    edit_counts = session.get("edit_counts", {})
    total_edits = sum(edit_counts.values()) or 0

    # Count chat turns per user (by sid)
    turns_by_sid = {}
    for msg in session.get("chat_messages", []):
        sid = msg.get("sender_sid")
        if not sid:
            continue
        turns_by_sid[sid] = turns_by_sid.get(sid, 0) + 1

    # Use union of all known sids so users who left (including host) are counted
    all_sids = set(edit_counts.keys()) | set(participants.keys()) | set(name_by_sid.keys()) | set(turns_by_sid.keys())

    contrib_summary = {}
    for sid in all_sids:
        name = None
        if sid in participants:
            name = participants[sid].get("name")
        if not name:
            name = name_by_sid.get(sid)
        if not name:
            name = f"user-{str(sid)[:4]}"

        user_edits = edit_counts.get(sid, 0)
        user_turns = turns_by_sid.get(sid, 0)
        activity_percent = round((user_edits / total_edits) * 100, 1) if total_edits else 0
        activity_score = user_edits + user_turns
        contrib_summary[name] = {
            "total_edits": user_edits,
            "write_time": 0,
            "turns_count": user_turns,
            "activity_percent": activity_percent,
            "activity_score": activity_score
        }
    return contrib_summary


def _build_userwise_contributions(session, turns_by_sid):
    participants = session.get("participants", {})
    name_by_sid = session.get("name_by_sid", {})
    user_contributions = session.get("user_contributions", {})
    
    # Include everyone we have ever seen
    all_sids = set(participants.keys()) | set(name_by_sid.keys()) | set(turns_by_sid.keys()) | set(session.get("edit_counts", {}).keys())

    userwise = {}
    for sid in all_sids:
        name = None
        if sid in participants:
            name = participants[sid].get("name")
        if not name:
            name = name_by_sid.get(sid)
        if not name:
            name = f"User-{sid[:6]}"

        # Build this user's contributed code from captured snapshots
        user_code = ""
        edit_count = session.get("edit_counts", {}).get(sid, 0)
        
        # Get all code snapshots for this user (captured when they handed over write permission)
        if sid in user_contributions:
            snapshots = user_contributions[sid].get("code_snapshots", [])
            
            if snapshots:
                # Show the latest/final code snapshot from this user
                latest_snapshot = snapshots[-1]
                snapshot_code = latest_snapshot.get("code", "")
                
                # If code is very long, show a preview
                if len(snapshot_code) > 3000:
                    lines = snapshot_code.splitlines()
                    user_code = "\n".join(lines[:100]) + "\n\n... (Code truncated, showing first 100 lines)"
                else:
                    user_code = snapshot_code
                
                # Add metadata about when this was captured
                timestamp = latest_snapshot.get("timestamp", "")
                reason = latest_snapshot.get("handover_reason", "")
                if timestamp and reason:
                    user_code = f"# Captured at: {timestamp}\n# Reason: {reason}\n\n{user_code}"
        
        # If no snapshots captured, show a message
        if not user_code:
            if edit_count > 0:
                user_code = "(Code contribution exists but snapshot not captured - user may still have write permission)"
            else:
                user_code = "(No code contributions captured)"

        userwise[name] = {
            "turns_count": turns_by_sid.get(sid, 0),
            "combined_code": user_code,
            "new_code_blocks": [],
            "modified_lines": [],
            "edit_count": edit_count
        }
    return userwise


def _safe_parse_dt(value, default=None):
    """Parse ISO or epoch timestamps safely."""
    if value is None:
        return default
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value))
        return datetime.fromisoformat(str(value))
    except Exception:
        return default


def _build_timeline_intel(session):
    """Reconstruct an inferred chronological timeline of the session."""
    now = datetime.utcnow()

    # Resolve session start
    start_dt = _safe_parse_dt(session.get("created_at") or session.get("session_metadata", {}).get("start_time"), now)
    start_dt = start_dt or now

    # Name map
    name_by_sid = dict(session.get("name_by_sid", {}) or {})
    for sid, info in (session.get("participants", {}) or {}).items():
        if info.get("name"):
            name_by_sid[sid] = info.get("name")

    # Collect edits
    edits = []
    for sid, data in (session.get("user_contributions", {}) or {}).items():
        for edit in data.get("edits", []):
            dt = _safe_parse_dt(edit.get("timestamp"))
            if not dt:
                continue
            edits.append({
                "time": dt,
                "sid": sid,
                "file": edit.get("file"),
                "delta": len(edit.get("new_content", "")) - len(edit.get("old_content", ""))
            })

    # Collect chat turns
    chats = []
    for msg in (session.get("chat_messages", []) or []):
        dt = _safe_parse_dt(msg.get("timestamp"))
        if not dt:
            continue
        chats.append({
            "time": dt,
            "sid": msg.get("sender_sid"),
            "message": msg.get("message", "")
        })

    # Collect control handovers
    control_events = []
    for ev in (session.get("control_events", []) or []):
        dt = _safe_parse_dt(ev.get("timestamp"))
        if not dt:
            continue
        control_events.append({
            "time": dt,
            "action": ev.get("action"),
            "from": ev.get("from_name") or name_by_sid.get(ev.get("from_sid")),
            "to": ev.get("to_name") or name_by_sid.get(ev.get("to_sid")),
            "reason": ev.get("reason", "")
        })

    # Collect executions
    runs = []
    for ex in (session.get("executions", []) or []):
        st = _safe_parse_dt(ex.get("start_time"), start_dt)
        et = _safe_parse_dt(ex.get("end_time"), st or start_dt)
        stderr_text = "".join(ex.get("stderr") or [])
        status = (ex.get("status") or "").lower()
        outcome = "success" if (status in {"completed", "success"} and not stderr_text.strip()) else "error"
        runs.append({
            "start": st,
            "end": et or st,
            "raw": ex,
            "stderr": stderr_text,
            "outcome": outcome
        })

    runs = [r for r in runs if r["start"]]
    runs.sort(key=lambda r: r["start"])

    # Determine session end
    all_times = [e["time"] for e in edits] + [c["time"] for c in chats] + [r.get("end") or r.get("start") for r in runs] + [start_dt]
    session_end = max([t for t in all_times if t is not None], default=now)

    def _stats_between(start, end):
        window_edits = [e for e in edits if start <= e["time"] <= end]
        window_chats = [c for c in chats if start <= c["time"] <= end]
        window_runs = [r for r in runs if (r["start"] and start <= r["start"] <= end)]
        window_controls = [ev for ev in control_events if start <= ev["time"] <= end]

        actor_counts = {}
        for e in window_edits:
            actor_counts[e["sid"]] = actor_counts.get(e["sid"], 0) + 1
        for c in window_chats:
            actor_counts[c["sid"]] = actor_counts.get(c["sid"], 0) + 0.5  # chats count slightly less
        top_actors = []
        for sid, score in sorted(actor_counts.items(), key=lambda kv: kv[1], reverse=True)[:3]:
            top_actors.append(name_by_sid.get(sid, f"user-{str(sid)[:4]}") if sid else "unknown")

        files = list({e.get("file") for e in window_edits if e.get("file")})

        return {
            "edits": len(window_edits),
            "runs": len(window_runs),
            "chats": len(window_chats),
            "control_changes": len(window_controls),
            "key_actors": top_actors,
            "files": files
        }

    def _error_hint(run):
        if not run.get("stderr"):
            return None
        for line in run["stderr"].splitlines()[::-1]:
            if line.strip():
                return line.strip()
        return None

    phases = []
    pointer = start_dt

    # Initialization phase (before first major event)
    first_activity_time = None
    if runs:
        first_activity_time = runs[0]["start"]
    non_run_activity_times = [x for x in ([e["time"] for e in edits] + [c["time"] for c in chats]) if x]
    if non_run_activity_times:
        earliest_non_run = min(non_run_activity_times)
        if first_activity_time:
            first_activity_time = min(first_activity_time, earliest_non_run)
        else:
            first_activity_time = earliest_non_run

    init_end = first_activity_time or session_end
    if init_end and init_end > pointer:
        stats = _stats_between(pointer, init_end)
        phases.append({
            "label": "Initialization",
            "start": pointer.isoformat(),
            "end": init_end.isoformat(),
            "summary": (
                f"Session bootstrapped with {stats['edits']} early edits"
                f" and {stats['chats']} chat exchanges."
            ),
            "stats": stats
        })
        pointer = init_end

    prev_outcome = None

    for idx, run in enumerate(runs):
        run_start = run["start"]
        run_end = run["end"] or run_start

        # Gap before this run
        if run_start and run_start > pointer:
            label = "Optimization" if prev_outcome == "success" else "Debugging"
            stats = _stats_between(pointer, run_start)
            if stats["edits"] or stats["chats"] or stats["control_changes"]:
                phases.append({
                    "label": label,
                    "start": pointer.isoformat(),
                    "end": run_start.isoformat(),
                    "summary": (
                        f"Between runs the team made {stats['edits']} edits"
                        f" and {stats['chats']} chats to refine the approach."
                    ),
                    "stats": stats
                })
        # Run phase
        recent_edits = [e for e in edits if e["time"] <= run_start and e["time"] >= (run_start - timedelta(minutes=5))]
        last_author = recent_edits[-1]["sid"] if recent_edits else None
        last_author_name = name_by_sid.get(last_author, "unknown") if last_author else "unknown"
        label = "Validation" if run["outcome"] == "success" else "Error Exploration"
        err_hint = _error_hint(run)
        run_summary = (
            f"Run #{idx + 1} {'succeeded' if run['outcome']=='success' else 'failed'}"
        )
        if err_hint and run["outcome"] == "error":
            run_summary += f" due to {err_hint}."
        else:
            run_summary += "."
        run_summary += f" Triggered after edits by {last_author_name}."
        phases.append({
            "label": label,
            "start": run_start.isoformat(),
            "end": (run_end or run_start).isoformat(),
            "summary": run_summary,
            "stats": _stats_between(run_start, run_end or run_start)
        })

        pointer = run_end or run_start
        prev_outcome = run["outcome"]

    # Tail phase after last run
    if pointer and session_end and session_end > pointer:
        label = "Validation" if prev_outcome == "success" else "Debugging"
        stats = _stats_between(pointer, session_end)
        phases.append({
            "label": label,
            "start": pointer.isoformat(),
            "end": session_end.isoformat(),
            "summary": (
                f"Wrap-up window with {stats['edits']} edits and {stats['chats']} chats"
                f" to {'confirm fixes' if label=='Validation' else 'chase remaining issues'}."
            ),
            "stats": stats
        })

    if not phases:
        phases.append({
            "label": "Initialization",
            "start": start_dt.isoformat(),
            "end": session_end.isoformat(),
            "summary": "Session had no notable events recorded.",
            "stats": {"edits": 0, "runs": 0, "chats": 0, "control_changes": 0, "key_actors": [], "files": []}
        })
    
    # ======= Summarization rules =======
    # 1) Merge consecutive phases with same label to avoid flooding
    merged = []
    for ph in phases:
        if merged and merged[-1]["label"] == ph["label"]:
            # extend time range
            merged[-1]["end"] = ph["end"]
            # merge stats
            mstats = merged[-1].get("stats", {})
            pstats = ph.get("stats", {})
            merged[-1]["stats"] = {
                "edits": (mstats.get("edits", 0) + pstats.get("edits", 0)),
                "runs": (mstats.get("runs", 0) + pstats.get("runs", 0)),
                "chats": (mstats.get("chats", 0) + pstats.get("chats", 0)),
                "control_changes": (mstats.get("control_changes", 0) + pstats.get("control_changes", 0)),
                "key_actors": list({*(mstats.get("key_actors", []) or []), *(pstats.get("key_actors", []) or [])}),
                "files": list({*(mstats.get("files", []) or []), *(pstats.get("files", []) or [])})
            }
            # keep the first summary, append short hint
            merged[-1]["summary"] = merged[-1]["summary"] + " Additional activity continued in this phase."
        else:
            merged.append(ph)

    # 2) Merge all Validation phases into one aggregate (chronologically spanning all)
    val_indices = [i for i, ph in enumerate(merged) if ph.get("label") == "Validation"]
    if len(val_indices) > 1:
        val_start = _safe_parse_dt(merged[val_indices[0]]["start"], start_dt).isoformat()
        val_end = _safe_parse_dt(merged[val_indices[-1]]["end"], session_end).isoformat()
        agg_stats = {"edits": 0, "runs": 0, "chats": 0, "control_changes": 0, "key_actors": [], "files": []}
        for i in val_indices:
            st = merged[i].get("stats", {})
            agg_stats["edits"] += st.get("edits", 0)
            agg_stats["runs"] += st.get("runs", 0)
            agg_stats["chats"] += st.get("chats", 0)
            agg_stats["control_changes"] += st.get("control_changes", 0)
            agg_stats["key_actors"] = list({*agg_stats["key_actors"], *(st.get("key_actors", []) or [])})
            agg_stats["files"] = list({*agg_stats["files"], *(st.get("files", []) or [])})
        # Remove individual validations
        merged = [ph for idx, ph in enumerate(merged) if idx not in val_indices]
        # Insert aggregate validation at position of first validation
        merged.insert(val_indices[0], {
            "label": "Validation",
            "start": val_start,
            "end": val_end,
            "summary": f"Aggregate validation phase covering {len(val_indices)} validation windows.",
            "stats": agg_stats
        })

    # 3) Limit the number of phases to a concise set (max 6)
    if len(merged) > 6:
        # Keep first 5 chronologically, merge the rest into a final 'Summary'
        keep = merged[:5]
        rest = merged[5:]
        if rest:
            # Merge stats of rest
            agg = {"edits": 0, "runs": 0, "chats": 0, "control_changes": 0, "key_actors": [], "files": []}
            for ph in rest:
                st = ph.get("stats", {})
                agg["edits"] += st.get("edits", 0)
                agg["runs"] += st.get("runs", 0)
                agg["chats"] += st.get("chats", 0)
                agg["control_changes"] += st.get("control_changes", 0)
                agg["key_actors"] = list({*agg["key_actors"], *(st.get("key_actors", []) or [])})
                agg["files"] = list({*agg["files"], *(st.get("files", []) or [])})
            keep.append({
                "label": "Summary",
                "start": rest[0]["start"],
                "end": rest[-1]["end"],
                "summary": f"Additional {len(rest)} condensed phases omitted for brevity.",
                "stats": agg
            })
        merged = keep

    return {
        "phases": merged,
        "control_handoffs": [
            {
                "at": ev["time"].isoformat(),
                "action": ev.get("action"),
                "from": ev.get("from"),
                "to": ev.get("to"),
                "reason": ev.get("reason")
            }
            for ev in sorted(control_events, key=lambda e: e["time"])
        ],
        "generated_at": now.isoformat()
    }


@app.route("/session_report", methods=["GET"])
def session_report_api():
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"status": "error", "message": "session_id is required"}), 400
    if session_id not in sessions:
        return jsonify({"status": "error", "message": "Session not found"}), 404

    session = sessions[session_id]
    # Build chat turn counts for downstream userwise summaries
    turns_by_sid = {}
    for msg in session.get("chat_messages", []):
        sid = msg.get("sender_sid")
        if sid:
            turns_by_sid[sid] = turns_by_sid.get(sid, 0) + 1

    contribution_summary = _build_contribution_summary(session)
    userwise_contributions = _build_userwise_contributions(session, turns_by_sid)
    mom_text = _build_mom_text(session)
    timeline_intel = _build_timeline_intel(session)

    # Build graph data for visualization
    users = list(contribution_summary.keys())
    edits = [contribution_summary[u]["total_edits"] for u in users]
    chat_turns = [contribution_summary[u]["turns_count"] for u in users]
    activity_percents = [contribution_summary[u]["activity_percent"] for u in users]

    return jsonify({
        "status": "success",
        "session_id": session_id,
        "contribution_summary": contribution_summary,
        "userwise_contributions": userwise_contributions,
        "mom_text": mom_text,
        "timeline_intel": timeline_intel,
        "graph_data": {
            "users": users,
            "edits": edits,
            "chat_turns": chat_turns,
            "activity_percents": activity_percents
        }
    })


@app.route("/end_session", methods=["POST"])
@login_required
def end_session():
    """End a session and store final report in MySQL"""
    data = request.get_json()
    session_id = data.get("session_id")
    
    if not session_id or session_id not in sessions:
        return jsonify({"status": "error", "message": "Session not found"}), 404
    
    session = sessions[session_id]
    current_user = get_current_user()
    
    # Verify user is the host
    if session.get("host_user_id") != current_user['id']:
        return jsonify({"status": "error", "message": "Only host can end session"}), 403
    
    # IMPORTANT: Capture final code state for current writer before ending session
    current_writer_sid = session.get("writer_id")
    if current_writer_sid:
        active_file = session.get("active_file", "main.py")
        current_code = session.get("files", {}).get(active_file, "")
        
        if "user_contributions" not in session:
            session["user_contributions"] = {}
        
        if current_writer_sid not in session["user_contributions"]:
            session["user_contributions"][current_writer_sid] = {
                "code_snapshots": [],
                "edits": []
            }
        
        # Capture final snapshot
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "file": active_file,
            "code": current_code,
            "handover_reason": "Session ended - final code state"
        }
        session["user_contributions"][current_writer_sid]["code_snapshots"].append(snapshot)
        print(f"📸 Captured final code snapshot for {session['participants'].get(current_writer_sid, {}).get('name', 'unknown')} at session end")
    
    try:
        # Build final report
        start_time = datetime.fromisoformat(session.get("created_at")) if session.get("created_at") else datetime.utcnow()
        end_time = datetime.utcnow()
        duration_seconds = int((end_time - start_time).total_seconds())
        
        # Build comprehensive report
        turns_by_sid = {}
        for msg in session.get("chat_messages", []):
            sid = msg.get("sender_sid")
            if sid:
                turns_by_sid[sid] = turns_by_sid.get(sid, 0) + 1
        
        contribution_summary = _build_contribution_summary(session)
        userwise_contributions = _build_userwise_contributions(session, turns_by_sid)
        mom_text = _build_mom_text(session)
        timeline_intel = _build_timeline_intel(session)
        credit_awards = award_session_credits(session_id, session)
        
        # Build graph data
        users = list(contribution_summary.keys())
        edits = [contribution_summary[u]["total_edits"] for u in users]
        chat_turns = [contribution_summary[u]["turns_count"] for u in users]
        activity_percents = [contribution_summary[u]["activity_percent"] for u in users]
        
        # Create final report JSON
        report_data = {
            "session_metadata": {
                "session_id": session_id,
                "session_name": session.get("session_name", f"Session {session_id}"),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration_seconds,
                "participant_count": len(session.get("all_participants", [])),
                "participants": session.get("all_participants", [])
            },
            "contribution_summary": contribution_summary,
            "userwise_contributions": userwise_contributions,
            "mom_text": mom_text,
            "timeline_intel": timeline_intel,
            "graph_data": {
                "users": users,
                "edits": edits,
                "chat_turns": chat_turns,
                "activity_percents": activity_percents
            },
            "executions": session.get("executions", []),
            "final_code": session.get("files", {}),
            "control_events": session.get("control_events", []),
            "user_contributions": session.get("user_contributions", {}),
            "credit_awards": credit_awards
        }
        
        # Store in database
        if DB_AVAILABLE:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO session_reports 
                       (session_id, host_user_id, session_name, start_time, end_time, 
                        duration_seconds, participant_count, report_json, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (session_id, current_user['id'], session.get("session_name", f"Session {session_id}"),
                     start_time, end_time, duration_seconds,
                     len(session.get("all_participants", [])),
                     json.dumps(report_data), datetime.utcnow())
                )
                conn.commit()
                cursor.close()
                conn.close()
                print(f"✅ Session {session_id} ended and report saved to MySQL")
        
        # Generate latency summary report before deleting session
        _write_latency_session_summary(session_id, session)
        
        # Delete from memory
        del sessions[session_id]
        
        return jsonify({
            "status": "success",
            "message": "Session ended and report saved",
            "session_id": session_id
        })
        
    except Exception as e:
        print(f"❌ Error ending session: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/report/<session_id>", methods=["GET"])
@login_required
def view_report(session_id):
    """View a stored session report from MySQL"""
    if not DB_AVAILABLE:
        return "Database not available", 500
    
    current_user = get_current_user()
    
    # Fetch report from database
    conn = get_db_connection()
    if not conn:
        return "Database connection failed", 500
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM session_reports WHERE session_id = %s", (session_id,))
    report = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not report:
        return "Report not found", 404
    
    # Verify user is the host
    if report['host_user_id'] != current_user['id']:
        return "Unauthorized - Only host can view report", 403
    
    return render_template("session_reportn.html", session_id=session_id, from_database=True)


@app.route("/report_data/<session_id>", methods=["GET"])
@login_required
def get_report_data(session_id):
    """API endpoint to fetch report data from MySQL"""
    if not DB_AVAILABLE:
        return jsonify({"status": "error", "message": "Database not available"}), 500
    
    current_user = get_current_user()
    
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM session_reports WHERE session_id = %s", (session_id,))
    report = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not report:
        return jsonify({"status": "error", "message": "Report not found"}), 404
    
    # Verify user is the host
    if report['host_user_id'] != current_user['id']:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    
    try:
        report_data = json.loads(report['report_json'])
        return jsonify({
            "status": "success",
            "session_id": session_id,
            **report_data
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error loading report: {e}"}), 500


@app.route("/session_report_page/<session_id>", methods=["GET"])
def session_report_page(session_id):
    """Legacy route - check if session is live or stored"""
    # Check if session is live in memory
    if session_id in sessions:
        return render_template("sr.html", session_id=session_id, from_database=False)
    
    # Check if report exists in database
    current_user = get_current_user()
    if DB_AVAILABLE and current_user:
        conn = get_db_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM session_reports WHERE session_id = %s AND host_user_id = %s",
                (session_id, current_user['id'])
            )
            report = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if report:
                return render_template("session_report.html", session_id=session_id, from_database=True)
    
    return "Session not found", 404


@app.route("/latency_monitor/<session_id>", methods=["GET"])
def latency_monitor_page(session_id):
    """Display latency monitoring page for a session"""
    if session_id not in sessions:
        return "Session not found", 404
    return render_template("latency_monitor.html", session_id=session_id)

if __name__ == "__main__":
    print("🚀 Starting SCIAM Collaborative Editor...")
    print("📍 Local URL: http://localhost:5000")
    print("💡 Features: Real-time coding, Python execution, Chat")
    print("🔧 Running with threading async_mode for better compatibility")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
