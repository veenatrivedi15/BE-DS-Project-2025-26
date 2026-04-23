from database.mongo import mongo
from datetime import datetime

# ===============================
# USER AUTH
# ===============================

def create_user(username, contact_number, password):
    # Check if username already exists
    if mongo.db.user_signup.find_one({"username": username}):
        return False
        
    mongo.db.user_signup.insert_one({
        "username": username,
        "contact_number": contact_number,
        "password": password,
        "created_at": datetime.utcnow()
    })
    return True

def user_login(username, password):
    user = mongo.db.user_signup.find_one({
        "username": username
    })

    if user and user["password"] == password:
        return user
    return None

# ===============================
# ORGANIZATION / ADMIN AUTH
# ===============================

def create_organization(org_name, contact_number, email, address, password):
    # Check if username already exists in organizations or users
    if mongo.db.organizations.find_one({"username": org_name}) or mongo.db.user_signup.find_one({"username": org_name}):
        return False
        
    mongo.db.organizations.insert_one({
        "name": org_name,
        "username": org_name,
        "email": email,
        "password": password,
        "contact_number": contact_number,
        "address": address,
        "role": "admin", # Explicitly set role
        "created_at": datetime.utcnow()
    })
    return True

def organization_login(username, password):
    org = mongo.db.organizations.find_one({
        "username": username
    })

    if not org:
        return None

    # Plain-text password comparison
    if org["password"] == password:
        return org

    return None

def list_all_organizations():
    orgs = list(mongo.db.organizations.find({}, {"_id": 0, "password": 0}))
    for org in orgs:
        if 'created_at' in org:
            org['created_at'] = org['created_at'].isoformat()
    return orgs
