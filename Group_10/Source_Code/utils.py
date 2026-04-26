from flask import session, redirect, url_for
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "currentUser" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get("userType") != role:
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper