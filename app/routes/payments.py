from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from ..models import Payment, Order, AuditLog, User
from ..extensions import db
import uuid, json

payment_bp = Blueprint("payments", __name__)

# ------------------- Create Payment -------------------
@payment_bp.route("/", methods=["POST"])
@jwt_required()
def create_payment():
    current_email = get_jwt_identity()
    user = User.query.filter_by(email=current_email).first()
    claims = get_jwt()

    data = request.get_json()
    order_id = data.get("order_id")
    method = data.get("payment_method")

    if not order_id or not method:
        return jsonify({"msg": "order_id and payment_method required"}), 400
    if method not in ["card", "cash", "bank_transfer"]:
        return jsonify({"msg": "Invalid payment method, only Card, Cash, and Bank Transfer are allowed"}), 400

    order = Order.query.get_or_404(order_id)

    if claims.get("role") != "admin" and order.user_id != user.id:
        return jsonify({"msg": "Access denied"}), 403
    if order.payment:
        return jsonify({"msg": "Payment already exists"}), 400
    if order.status == "cancelled":
        return jsonify({"msg": "Cannot pay for cancelled order"}), 400

    payment = Payment(
        order_id=order.id,
        amount=order.total_amount,
        payment_method=method,
        status="completed",
        transaction_id=str(uuid.uuid4())
    )
    order.status = "completed"
    db.session.add(payment)

    # Audit log
    log = AuditLog(
        user_id=user.id,
        action="CREATE",
        table_name="payment",
        record_id=payment.id,
        new_values=json.dumps({"order_id": order.id, "amount": order.total_amount}),
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({
        "msg": "Payment successful",
        "transaction_id": payment.transaction_id,
        "amount": payment.amount
    })

# ------------------- List Payments -------------------
@payment_bp.route("/", methods=["GET"])
@jwt_required()
def list_payments():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admins only!"}), 403

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    payments = Payment.query.order_by(Payment.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    data = [
        {
            "id": p.id,
            "order_id": p.order_id,
            "amount": p.amount,
            "method": p.payment_method,
            "status": p.status,
            "transaction_id": p.transaction_id
        } for p in payments.items
    ]
    return jsonify({
        "page": page,
        "per_page": per_page,
        "total": payments.total,
        "payments": data
    })
