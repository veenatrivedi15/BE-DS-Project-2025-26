from database.mongo import mongo
from datetime import datetime

def log_user_login(username):
    mongo.db.user_login.insert_one({
        "username": username,
        "login_time": datetime.utcnow()
    })
