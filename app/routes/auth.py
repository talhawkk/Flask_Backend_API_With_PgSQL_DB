from flask import Blueprint, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
from ..models import User
from ..extensions import db
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
import re

auth_bp = Blueprint("auth", __name__)

# Email validation regex
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

def is_valid_email(email):
    """Validate email format"""
    if not email or not isinstance(email, str):
        return False
    return re.match(EMAIL_REGEX, email) is not None

# ------------------- Register -------------------
@auth_bp.route("/register", methods=['POST'])
def register():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "user")

    if not email or not password:
        return jsonify({"msg": "Email and password required"}), 400
    
    # Validate email format
    if not is_valid_email(email):
        return jsonify({"msg": "Invalid email format"}), 400
    
    # Validate password length
    if len(password) < 6:
        return jsonify({"msg": "Password must be at least 6 characters long"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "User already exists"}), 409

    hashed_password = generate_password_hash(password)
    new_user = User(email=email, password=hashed_password, role=role)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"msg": "User registered successfully"}), 201

# ------------------- Login -------------------
@auth_bp.route("/login", methods=['POST'])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        return jsonify({"msg": "Email and password required"}), 400
    
    # Validate email format
    if not is_valid_email(email):
        return jsonify({"msg": "Invalid email format"}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"msg": "Invalid credentials"}), 401

    token = create_access_token(identity=user.email, additional_claims={"role": user.role})
    return jsonify({"access_token": token})

# ------------------- Logout -------------------
@auth_bp.route("/logout", methods=['POST'])
@jwt_required()
def logout():
    current_user = get_jwt_identity()
    claims = get_jwt()
    return jsonify({"msg": f"{current_user} logged out", "role": claims.get("role")})
