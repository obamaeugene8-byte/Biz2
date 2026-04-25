from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


# ---------------- COMPANY ----------------
class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------- USER ----------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)
    weekly_capacity = db.Column(db.Integer, default=40)

    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    tasks = db.relationship('Task', backref='user', lazy=True)


# ---------------- TASK ----------------
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    title = db.Column(db.String(200), nullable=False)
    estimated_hours = db.Column(db.Integer, default=1)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ---------------- LICENSE ----------------
class License(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    code = db.Column(db.String(50), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    expires_at = db.Column(db.DateTime, nullable=True)

    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))

    # ✅ NEW: persistent auth token
    auth_token = db.Column(db.String(100), unique=True, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
