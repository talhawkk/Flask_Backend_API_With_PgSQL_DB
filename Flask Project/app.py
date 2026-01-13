from flask import Config, Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from flask_jwt_extended import (
    JWTManager, create_access_token, get_jwt,
    jwt_required, get_jwt_identity)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from config import Config
import uuid
import json

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
jwt = JWTManager(app)


@app.route('/', methods=['GET'])
@jwt_required(optional=True)
def home():
    current_user = get_jwt_identity()
    if current_user:
        return jsonify({"msg": f"Welcome back, {current_user}!"})
    return jsonify({"msg": "Welcome to the Home Page, please login or register."})

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
@jwt_required()
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

@app.route('/create_bulk', methods=['POST'])
@jwt_required()
def create_bulk():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admins only!"}), 403

    data = request.get_json()  # expects a list of products
    if not isinstance(data, list):
        return jsonify({"msg": "Expected a list of products"}), 400

    created = []
    for item in data:
        name = item.get("name")
        price = item.get("price")
        description = item.get("description", "")
        if not name or price is None:
            continue
        p = Product(name=name, description=description, price=price)
        db.session.add(p)
        created.append({"name": name, "price": price})
    
    db.session.commit()
    return jsonify({"msg": f"{len(created)} products created", "products": created})


@app.route("/show", methods=['GET'])
def show():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 5, type=int)
    sort_by = request.args.get('sort_by', 'created_at', type=str)
    order = request.args.get('order', 'desc', type=str)

    # Advanced filters
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    name = request.args.get('name', type=str)

    # Base query: only non-deleted products
    query = Product.query.filter_by(deleted=False)

    # Apply filters
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if name:
        query = query.filter(Product.name.ilike(f"%{name}%"))

    # Apply sorting
    if sort_by == "price":
        query = query.order_by(Product.price.asc() if order=="asc" else Product.price.desc())
    else:  # default sorting by created_at
        query = query.order_by(Product.created_at.asc() if order=="asc" else Product.created_at.desc())

    # Pagination
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


@app.route("/update/<int:id>", methods=['PUT'])
@jwt_required()
def update(id):
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
    q_name = request.args.get("name", "")
    q_desc = request.args.get("description", "")
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)

    query = Product.query.filter_by(deleted=False)

    if q_name:
        query = query.filter(Product.name.ilike(f"%{q_name}%"))
    if q_desc:
        query = query.filter(Product.description.ilike(f"%{q_desc}%"))
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    # Optional: sorting by price or created_at
    sort_by = request.args.get("sort_by", "created_at")
    order = request.args.get("order", "desc")
    if sort_by == "price":
        query = query.order_by(Product.price.asc() if order=="asc" else Product.price.desc())
    else:
        query = query.order_by(Product.created_at.asc() if order=="asc" else Product.created_at.desc())

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    products = query.paginate(page=page, per_page=per_page, error_out=False)

    data = [
        {"id": p.id, "name": p.name, "description": p.description, "price": p.price}
        for p in products.items
    ]
    return jsonify({
        "page": page,
        "per_page": per_page,
        "total": products.total,
        "results": data
    })

# --------------------------------Orders API--------------------------------

@app.route('/orders', methods=['POST'])
@jwt_required()
def create_order():
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()
    
    data = request.get_json()
    items = data.get('items', [])  # [{"product_id": 1, "quantity": 2}, ...]
    
    if not items:
        return jsonify({"msg": "Order items required"}), 400
    
    total = 0
    order_items = []
    
    for item in items:
        product = Product.query.get(item['product_id'])
        if not product or product.deleted:
            return jsonify({"msg": f"Product {item['product_id']} not found"}), 404
        
        quantity = item.get('quantity', 1)
        total += product.price * quantity
        order_items.append({
            'product': product,
            'quantity': quantity,
            'price': product.price
        })
    
    # Create order
    order = Order(user_id=user.id, total_amount=total, status='pending')
    db.session.add(order)
    db.session.flush()  
    
    for item in order_items:
        oi = OrderItem(
            order_id=order.id,
            product_id=item['product'].id,
            quantity=item['quantity'],
            price=item['price']
        )
        db.session.add(oi)
    
    # Log the action
    log = AuditLog(
        user_id=user.id,
        action='CREATE',
        table_name='order',
        record_id=order.id,
        new_values=json.dumps({"total_amount": total, "status": "pending"}),
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        "msg": "Order created",
        "order_id": order.id,
        "total": total
    }), 201


@app.route('/orders', methods=['GET'])
@jwt_required()
def get_orders():
    current_user_email = get_jwt_identity()
    claims = get_jwt()
    user = User.query.filter_by(email=current_user_email).first()
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Admin sees all orders, user sees only their own
    if claims.get("role") == "admin":
        query = Order.query
    else:
        query = Order.query.filter_by(user_id=user.id)
    
    orders = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    data = []
    for o in orders.items:
        items_data = [{"product_id": oi.product_id, "quantity": oi.quantity, "price": oi.price} for oi in o.items]
        data.append({
            "id": o.id,
            "user_email": o.user.email,
            "total_amount": o.total_amount,
            "status": o.status,
            "items": items_data,
            "created_at": o.created_at.isoformat()
        })
    
    return jsonify({
        "page": page,
        "per_page": per_page,
        "total": orders.total,
        "orders": data
    })


@app.route('/orders/<int:id>', methods=['GET'])
@jwt_required()
def get_order(id):
    current_user_email = get_jwt_identity()
    claims = get_jwt()
    user = User.query.filter_by(email=current_user_email).first()
    
    order = Order.query.get_or_404(id)
    
    # Check if user has access to this order
    if claims.get("role") != "admin" and order.user_id != user.id:
        return jsonify({"msg": "Access denied"}), 403
    
    items_data = [{"product_id": oi.product_id, "product_name": oi.product.name, "quantity": oi.quantity, "price": oi.price} for oi in order.items]
    
    return jsonify({
        "id": order.id,
        "user_email": order.user.email,
        "total_amount": order.total_amount,
        "status": order.status,
        "items": items_data,
        "created_at": order.created_at.isoformat(),
        "payment": {
            "status": order.payment.status,
            "method": order.payment.payment_method,
            "transaction_id": order.payment.transaction_id
        } if order.payment else None
    })


@app.route('/orders/<int:id>/cancel', methods=['PUT'])
@jwt_required()
def cancel_order(id):
    current_user_email = get_jwt_identity()
    claims = get_jwt()
    user = User.query.filter_by(email=current_user_email).first()
    
    order = Order.query.get_or_404(id)
    
    # Check access
    if claims.get("role") != "admin" and order.user_id != user.id:
        return jsonify({"msg": "Access denied"}), 403
    
    if order.status == 'completed':
        return jsonify({"msg": "Cannot cancel completed order"}), 400
    
    if order.status == 'cancelled':
        return jsonify({"msg": "Order already cancelled"}), 400
    
    old_status = order.status
    order.status = 'cancelled'
    
    # Audit log
    log = AuditLog(
        user_id=user.id,
        action='UPDATE',
        table_name='order',
        record_id=order.id,
        old_values=json.dumps({"status": old_status}),
        new_values=json.dumps({"status": "cancelled"}),
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({"msg": "Order cancelled", "order_id": order.id})


# --------------------------------Payments API--------------------------------

@app.route('/payments', methods=['POST'])
@jwt_required()
def create_payment():
    current_user_email = get_jwt_identity()
    user = User.query.filter_by(email=current_user_email).first()
    
    data = request.get_json()
    order_id = data.get('order_id')
    payment_method = data.get('payment_method')  # card, cash, bank_transfer
    
    if not order_id or not payment_method:
        return jsonify({"msg": "order_id and payment_method required"}), 400
    
    if payment_method not in ['card', 'cash', 'bank_transfer']:
        return jsonify({"msg": "Invalid payment method. Use: card, cash, or bank_transfer"}), 400
    
    order = Order.query.get_or_404(order_id)
    
    # Check if user owns this order or is admin
    claims = get_jwt()
    if claims.get("role") != "admin" and order.user_id != user.id:
        return jsonify({"msg": "Access denied"}), 403
    
    if order.payment:
        return jsonify({"msg": "Payment already exists for this order"}), 400
    
    if order.status == 'cancelled':
        return jsonify({"msg": "Cannot pay for cancelled order"}), 400
    
    # Create payment
    payment = Payment(
        order_id=order.id,
        amount=order.total_amount,
        payment_method=payment_method,
        status='completed',
        transaction_id=str(uuid.uuid4())
    )
    
    order.status = 'completed'
    db.session.add(payment)
    
    # Audit log
    log = AuditLog(
        user_id=user.id,
        action='CREATE',
        table_name='payment',
        record_id=None,
        new_values=json.dumps({"order_id": order.id, "amount": order.total_amount, "method": payment_method}),
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        "msg": "Payment successful",
        "transaction_id": payment.transaction_id,
        "amount": payment.amount,
        "order_status": order.status
    }), 201


@app.route('/payments', methods=['GET'])
@jwt_required()
def get_payments():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admins only!"}), 403
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    payments = Payment.query.order_by(Payment.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    data = []
    for p in payments.items:
        data.append({
            "id": p.id,
            "order_id": p.order_id,
            "amount": p.amount,
            "payment_method": p.payment_method,
            "status": p.status,
            "transaction_id": p.transaction_id,
            "created_at": p.created_at.isoformat()
        })
    
    return jsonify({
        "page": page,
        "per_page": per_page,
        "total": payments.total,
        "payments": data
    })


# --------------------------------Reports API--------------------------------

@app.route('/reports/monthly-sales', methods=['GET'])
@jwt_required()
def monthly_sales_report():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admins only!"}), 403
    
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    
    if not year or not month:
        return jsonify({"msg": "year and month are required"}), 400
    
    if month < 1 or month > 12:
        return jsonify({"msg": "month must be between 1 and 12"}), 400
    
    try:
        result = db.session.execute(
            text("SELECT * FROM get_monthly_sales_report(:year, :month)"),
            {"year": year, "month": month}
        ).fetchone()
        
        if result:
            return jsonify({
                "year": year,
                "month": month,
                "report": {
                    "total_orders": result[0] or 0,
                    "total_revenue": float(result[1]) if result[1] else 0,
                    "completed_orders": result[2] or 0,
                    "pending_orders": result[3] or 0,
                    "cancelled_orders": result[4] or 0,
                    "avg_order_value": round(float(result[5]), 2) if result[5] else 0,
                    "top_product": {
                        "id": result[6],
                        "name": result[7],
                        "total_sold": result[8]
                    } if result[6] else None
                }
            })
        
        return jsonify({"msg": "No data found"}), 404
    
    except Exception as e:
        # If stored procedure doesn't exist, return basic report
        return jsonify({
            "msg": "Stored procedure not found. Run the SQL file first.",
            "error": str(e)
        }), 500

# ---------------------optional: Basic sales summary without stored procedure-----------------------
@app.route('/reports/sales-summary', methods=['GET'])
@jwt_required()
def sales_summary():
    """Basic sales summary without stored procedure"""
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admins only!"}), 403
    
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    
    if not year or not month:
        return jsonify({"msg": "year and month are required"}), 400
    
    # Query orders for the specified month
    from sqlalchemy import extract
    
    orders = Order.query.filter(
        extract('year', Order.created_at) == year,
        extract('month', Order.created_at) == month
    ).all()
    
    total_orders = len(orders)
    total_revenue = sum(o.total_amount for o in orders if o.status == 'completed')
    completed = sum(1 for o in orders if o.status == 'completed')
    pending = sum(1 for o in orders if o.status == 'pending')
    cancelled = sum(1 for o in orders if o.status == 'cancelled')
    avg_value = total_revenue / completed if completed > 0 else 0
    
    return jsonify({
        "year": year,
        "month": month,
        "report": {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "completed_orders": completed,
            "pending_orders": pending,
            "cancelled_orders": cancelled,
            "avg_order_value": round(avg_value, 2)
        }
    })


# --------------------------------Audit Logs API--------------------------------

@app.route('/audit-logs', methods=['GET'])
@jwt_required()
def get_audit_logs():
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"msg": "Admins only!"}), 403
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    table_name = request.args.get('table', type=str)
    action = request.args.get('action', type=str)
    
    query = AuditLog.query
    
    if table_name:
        query = query.filter_by(table_name=table_name)
    if action:
        query = query.filter_by(action=action.upper())
    
    logs = query.order_by(AuditLog.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    
    data = []
    for log in logs.items:
        data.append({
            "id": log.id,
            "user_email": log.user.email if log.user else None,
            "action": log.action,
            "table_name": log.table_name,
            "record_id": log.record_id,
            "old_values": json.loads(log.old_values) if log.old_values else None,
            "new_values": json.loads(log.new_values) if log.new_values else None,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat()
        })
    
    return jsonify({
        "page": page,
        "per_page": per_page,
        "total": logs.total,
        "logs": data
    })



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
    name = db.Column(db.String(120), nullable=False, index=True)
    description = db.Column(db.String(255))
    price = db.Column(db.Float, nullable=False, index=True)  # Index for price filtering
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # Index for sorting
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted = db.Column(db.Boolean, default=False, index=True)  # Index for soft delete filter


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending', index=True)  # pending, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('orders', lazy=True))
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)  # Price at time of order
    
    product = db.relationship('Product', backref='order_items')

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)  # card, cash, bank_transfer
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    transaction_id = db.Column(db.String(100), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    order = db.relationship('Order', backref=db.backref('payment', uselist=False))

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    action = db.Column(db.String(50), nullable=False)  # CREATE, UPDATE, DELETE, LOGIN, LOGOUT
    table_name = db.Column(db.String(50), nullable=False)
    record_id = db.Column(db.Integer)
    old_values = db.Column(db.Text)  # JSON string
    new_values = db.Column(db.Text)  # JSON string
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='audit_logs')


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)