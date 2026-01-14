from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from ..models import Order
from sqlalchemy import extract

reports_bp = Blueprint("reports", __name__)

# ------------------- Monthly Sales Report -------------------
@reports_bp.route("/monthly-sales", methods=["GET"])
@jwt_required()
def monthly_sales():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admins only!"}), 403

    year = request.args.get("year", type=int)
    month = request.args.get("month", type=int)

    if not year or not month:
        return jsonify({"msg": "year and month required"}), 400
    if month < 1 or month > 12:
        return jsonify({"msg": "month must be 1-12"}), 400

    orders = Order.query.filter(
        extract("year", Order.created_at)==year,
        extract("month", Order.created_at)==month
    ).all()

    total_orders = len(orders)
    completed = sum(1 for o in orders if o.status=="completed")
    pending = sum(1 for o in orders if o.status=="pending")
    cancelled = sum(1 for o in orders if o.status=="cancelled")
    total_revenue = sum(o.total_amount for o in orders if o.status=="completed")
    avg_order = total_revenue / completed if completed else 0

    return jsonify({
        "year": year,
        "month": month,
        "report": {
            "total_orders": total_orders,
            "completed_orders": completed,
            "pending_orders": pending,
            "cancelled_orders": cancelled,
            "total_revenue": total_revenue,
            "avg_order_value": round(avg_order, 2)
        }
    })
