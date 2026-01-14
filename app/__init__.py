

from flask import Flask
from .extensions import db, jwt
from .routes.auth import auth_bp
from .routes.products import product_bp
from .routes.orders import order_bp
from .routes.payments import payment_bp
from .routes.reports import reports_bp
from .routes.audit import audit_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(product_bp, url_prefix="/products")
    app.register_blueprint(order_bp, url_prefix="/orders")
    app.register_blueprint(payment_bp, url_prefix="/payments")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(audit_bp, url_prefix="/audit-logs")

    with app.app_context():
        db.create_all()

    return app
