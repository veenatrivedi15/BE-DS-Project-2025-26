from database.mongo import mongo

def create_user(name, username, password):
    mongo.db.user_signup.insert_one({
        "name": name,
        "username": username,
        "password": password
    })
