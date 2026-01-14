from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from ..models import AuditLog
from ..extensions import db
import json

audit_bp = Blueprint("audit", __name__)

@audit_bp.route("/", methods=["GET"])
@jwt_required()
def get_audit_logs():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admins only!"}), 403

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    table = request.args.get("table")
    action = request.args.get("action")

    query = AuditLog.query
    if table:
        query = query.filter_by(table_name=table)
    if action:
        query = query.filter_by(action=action.upper())

    logs = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    data = [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "table_name": log.table_name,
            "record_id": log.record_id,
            "old_values": json.loads(log.old_values) if log.old_values else None,
            "new_values": json.loads(log.new_values) if log.new_values else None,
            "ip": log.ip_address,
            "created_at": log.created_at.isoformat()
        } for log in logs.items
    ]
    return jsonify({
        "page": page,
        "per_page": per_page,
        "total": logs.total,
        "logs": data
    })
