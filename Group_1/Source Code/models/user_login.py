from database.mongo import mongo

def user_login(username, password):
    user = mongo.db.user_signup.find_one({"username": username})

    if not user:
        return None

    if user.get("password") == password:
        return user

    return None
