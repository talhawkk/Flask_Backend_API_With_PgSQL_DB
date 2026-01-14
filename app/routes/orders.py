from flask import Blueprint, request, jsonify
from ..models import Order, OrderItem, Product, AuditLog, User
from ..extensions import db
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
import json

order_bp = Blueprint("orders", __name__)

@order_bp.route("/", methods=['POST'])
@jwt_required()
def create_order():
    current_email = get_jwt_identity()
    user = User.query.filter_by(email=current_email).first()
    data = request.get_json()
    items = data.get("items", [])
    if not items:
        return jsonify({"msg": "Order items required"}), 400

    total = 0
    order_items = []
    for item in items:
        product = Product.query.get(item["product_id"])
        if not product or product.deleted:
            return jsonify({"msg": f"Product {item['product_id']} not found"}), 404
        quantity = item.get("quantity", 1)
        total += product.price * quantity
        order_items.append({"product": product, "quantity": quantity, "price": product.price})

    order = Order(user_id=user.id, total_amount=total, status="pending")
    db.session.add(order)
    db.session.flush()

    for item in order_items:
        oi = OrderItem(order_id=order.id, product_id=item["product"].id, quantity=item["quantity"], price=item["price"])
        db.session.add(oi)

    # Audit log
    log = AuditLog(user_id=user.id, action="CREATE", table_name="order", record_id=order.id, new_values=json.dumps({"total": total}), ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()

    return jsonify({"msg": "Order created", "order_id": order.id, "total": total})
