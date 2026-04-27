from database.mongo import mongo
from datetime import datetime

def log_admin_login(username):
    mongo.db.admin_login_log.insert_one({
        "username": username,
        "login_time": datetime.utcnow()
    })
