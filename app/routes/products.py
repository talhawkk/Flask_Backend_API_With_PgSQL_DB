from flask import Blueprint, request, jsonify
from ..models import Product
from ..extensions import db
from flask_jwt_extended import jwt_required, get_jwt

product_bp = Blueprint("products", __name__)

# ------------------- Create Product -------------------
@product_bp.route("/", methods=['POST'])
@jwt_required()
def create_product():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admins only!"}), 403

    data = request.get_json()
    name = data.get("name")
    price = data.get("price")
    description = data.get("description", "")

    if not name or price is None:
        return jsonify({"msg": "Name and price required"}), 400

    product = Product(name=name, price=price, description=description)
    db.session.add(product)
    db.session.commit()
    return jsonify({"msg": "Product created", "product_id": product.id}), 201

# ------------------- List / Search Products -------------------
@product_bp.route("/", methods=['GET'])
def list_products():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    name_filter = request.args.get("name", "")

    query = Product.query.filter_by(deleted=False)
    if name_filter:
        query = query.filter(Product.name.ilike(f"%{name_filter}%"))

    products = query.paginate(page=page, per_page=per_page, error_out=False)
    data = [{"id": p.id, "name": p.name, "price": p.price, "description": p.description} for p in products.items]

    return jsonify({
        "page": page,
        "per_page": per_page,
        "total": products.total,
        "products": data
    })

# ------------------- Update Product -------------------
@product_bp.route("/<int:id>", methods=['PUT'])
@jwt_required()
def update_product(id):
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admins only!"}), 403

    product = Product.query.get_or_404(id)
    data = request.get_json()
    product.name = data.get("name", product.name)
    product.price = data.get("price", product.price)
    product.description = data.get("description", product.description)
    db.session.commit()
    return jsonify({"msg": "Product updated", "product_id": product.id})

# ------------------- Soft Delete Product -------------------
@product_bp.route("/<int:id>", methods=['DELETE'])
@jwt_required()
def delete_product(id):
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admins only!"}), 403

    product = Product.query.get_or_404(id)
    product.deleted = True
    db.session.commit()
    return jsonify({"msg": "Product soft deleted", "product_id": product.id})
