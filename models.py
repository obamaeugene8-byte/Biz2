from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


# ==================================================
# 🏢 COMPANY (WORKSPACE / TENANT)
# ==================================================
class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(120), nullable=False)

    # 💳 subscription system (SAAS CORE)
    status = db.Column(db.String(20), default="trial")  
    # trial | active | expired

    expires_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ==================================================
# 👤 USER (LOGIN SYSTEM)
# ==================================================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(20), default="admin")  
    # admin | member

    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ---------------- SECURITY HELPERS ----------------
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# ==================================================
# 📊 TASKS (YOUR CORE PRODUCT FEATURE)
# ==================================================
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)
    estimated_hours = db.Column(db.Integer, default=1)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
