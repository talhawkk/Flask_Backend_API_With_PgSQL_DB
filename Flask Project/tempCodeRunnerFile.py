from flask import Config, Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
# from sqlalchemy import SQLAlchemy
from flask_jwt_extended import (
    JWTManager, create_access_token, get_jwt,
    jwt_required, get_jwt_identity)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
jwt = JWTManager(app)


@app.route('/', methods=['GET'])
def home():
    return "Welcome to the Home Page, please login or register."

# --------------------------------Authentication----------------------------------------------


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'user')
    
    if not email or not password:
        return jsonify({"msg": "Email and password are required"}), 400
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"msg": "User already exists"}), 409
    
    hashed_password = generate_password_hash(password)
    new_user = User(email=email, password=hashed_password, role=role)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"msg": "User registered successfully"}), 201



@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user=User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"msg": "Invalid credentials"}), 401
    
    access_token=create_access_token(
        identity=user.email,
        additional_claims={"role": user.role}
    )
    return jsonify(access_token=access_token), 200


@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    current_user = get_jwt_identity()  # Returns email
    claims = get_jwt()  # Returns full token including role
    print("Current User:", current_user)
    print("Role:", claims.get("role"))
    return jsonify({"msg": "Logout successful"}), 200

# ---------------------------------------CRUD----------------------------------

@app.route('/create', methods=['POST'])
def create():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admins only!"}), 403
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    price = data.get('price')

    if not name or not price:
        return jsonify({"msg": "Name and price are required"}), 400
    new_product = Product(name=name, description=description, price=price)
    db.session.add(new_product)
    db.session.commit()
    return jsonify({"msg": "Product created successfully", "product": {
        "id": new_product.id,
        "name": new_product.name,
        "description": new_product.description,
        "price": new_product.price
    }}), 201

@app.route("/show", methods=['GET'])
def show():
    page=request.args.get('page', 1, type=int)
    per_page=request.args.get('per_page', 5, type=int)
    sort_by=request.args.get('sort_by', 'created_at', type=str)
    order=request.args.get('order', 'desc', type=str)


    query = Product.query.filter_by(deleted=False)
    if sort_by == "price":
        query = query.order_by(Product.price.asc() if order=="asc" else Product.price.desc())
    else:
        query = query.order_by(Product.created_at.asc() if order=="asc" else Product.created_at.desc())

    products = query.paginate(page=page, per_page=per_page, error_out=False)

    data = []
    for p in products.items:
        data.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "price": p.price
        })
    return jsonify({
        "page": page,
        "per_page": per_page,
        "total": products.total,
        "products": data
    })

@app.route("/update", methods=['PUT'])
def update():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admins only!"}), 403
    
    product = Product.query.get_or_404(id)
    if product.deleted:
        return jsonify({"msg": "Product not found"}), 404

    data = request.get_json()
    product.name = data.get("name", product.name)
    product.description = data.get("description", product.description)
    product.price = data.get("price", product.price)
    db.session.commit()
    return jsonify({"msg": "Product updated", "product": {"id": product.id, "name": product.name}})

@app.route("/delete/<int:id>", methods=['DELETE'])
@jwt_required()
def delete(id):
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admin only"}), 403

    product = Product.query.get_or_404(id)
    if product.deleted:
        return jsonify({"msg": "Already deleted"}), 400

    product.deleted = True
    db.session.commit()
    return jsonify({"msg": "Product soft deleted"})

# --------------------------------------------Searching--------------------------------

@app.route("/search", methods=['GET'])
def search():
    q = request.args.get("q", "")
    if not q:
        return jsonify({"msg": "Query parameter required"}), 400

    results = Product.query.filter(
        Product.deleted==False,
        db.or_(
            Product.name.ilike(f"%{q}%"),
            Product.description.ilike(f"%{q}%")
        )
    ).all()

    data = [{"id": p.id, "name": p.name, "description": p.description, "price": p.price} for p in results]
    return jsonify({"results": data, "count": len(data)})


# --------------------------------Database Initialization--------------------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.email}>"

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255))
    price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted = db.Column(db.Boolean, default=False)  # Soft delete



with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)