from flask import Flask, render_template, request, redirect, make_response
from config import Config
from models import db, User, Task, License, Company
import uuid
from datetime import datetime, timedelta
import os
import secrets

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key")

db.init_app(app)

# ---------------- SAFE DB INIT ----------------
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print("DB init error:", e)


# ---------------- LICENSE CHECK FUNCTION ----------------
def get_license():
    token = request.cookies.get("auth_token")

    if not token:
        return None

    license = License.query.filter_by(auth_token=token).first()

    if not license:
        return None

    if license.expires_at and license.expires_at < datetime.utcnow():
        return None

    return license


# ---------------- ADMIN LICENSE CREATOR ----------------
@app.route("/admin/create-license")
def create_license():
    code = str(uuid.uuid4()).replace("-", "")[:12].upper()

    company = Company(name=f"Company-{code[:5]}")
    db.session.add(company)
    db.session.commit()

    license = License(
        code=code,
        is_active=True,
        expires_at=datetime.utcnow() + timedelta(days=30),
        company_id=company.id,
        auth_token=None
    )

    db.session.add(license)
    db.session.commit()

    return f"License created: {code}"


# ---------------- LICENSE ACTIVATION ----------------
@app.route("/activate", methods=["GET", "POST"])
def activate():

    # AUTO LOGIN USING COOKIE
    license = get_license()
    if license:
        return redirect("/")

    if request.method == "POST":
        code = request.form.get("code")

        license = License.query.filter_by(code=code, is_active=True).first()

        if not license:
            return "Invalid license code"

        if license.expires_at and license.expires_at < datetime.utcnow():
            return "License expired"

        # GENERATE PERMANENT TOKEN
        license.auth_token = secrets.token_hex(32)
        db.session.commit()

        response = make_response(redirect("/"))

        # STORE TOKEN IN COOKIE (30 DAYS)
        response.set_cookie(
            "auth_token",
            license.auth_token,
            max_age=30 * 24 * 60 * 60,
            httponly=True
        )

        return response

    return render_template("activate.html")


# ---------------- DASHBOARD ----------------
@app.route("/")
def dashboard():
    license = get_license()

    if not license:
        return redirect("/activate")

    company_id = license.company_id

    users = User.query.filter_by(company_id=company_id).all()

    data = []

    for user in users:
        tasks = Task.query.filter_by(user_id=user.id, company_id=company_id).all()
        total_hours = sum(t.estimated_hours or 0 for t in tasks)

        capacity = user.weekly_capacity or 1
        load = (total_hours / capacity) * 100

        if load > 100:
            recommendation = "Overloaded - redistribute tasks"
        elif load > 80:
            recommendation = "Near capacity"
        elif load < 50:
            recommendation = "Can take more work"
        else:
            recommendation = "Balanced"

        data.append({
            "name": user.name,
            "tasks": len(tasks),
            "hours": total_hours,
            "capacity": user.weekly_capacity,
            "load": round(load, 1),
            "recommendation": recommendation
        })

    return render_template("dashboard.html", data=data)


# ---------------- USERS ----------------
@app.route("/users", methods=["GET", "POST"])
def users():
    license = get_license()

    if not license:
        return redirect("/activate")

    company_id = license.company_id

    if request.method == "POST":
        name = request.form.get("name")
        capacity = request.form.get("capacity")

        if not name or not capacity:
            return "Name and capacity are required"

        try:
            capacity = int(capacity)
        except ValueError:
            return "Capacity must be a valid number"

        user = User(
            name=name,
            weekly_capacity=capacity,
            company_id=company_id
        )

        db.session.add(user)
        db.session.commit()

        return redirect("/users")

    users = User.query.filter_by(company_id=company_id).all()
    return render_template("users.html", users=users)


# ---------------- TASKS ----------------
@app.route("/tasks", methods=["GET", "POST"])
def tasks():
    license = get_license()

    if not license:
        return redirect("/activate")

    company_id = license.company_id
    users = User.query.filter_by(company_id=company_id).all()

    if request.method == "POST":
        title = request.form.get("title")
        hours = request.form.get("hours")
        user_id = request.form.get("user_id")

        if not title or not hours or not user_id:
            return "All fields are required"

        try:
            hours = int(hours)
            user_id = int(user_id)
        except ValueError:
            return "Invalid input"

        task = Task(
            title=title,
            estimated_hours=hours,
            user_id=user_id,
            company_id=company_id
        )

        db.session.add(task)
        db.session.commit()

        return redirect("/tasks")

    tasks = Task.query.filter_by(company_id=company_id).all()
    return render_template("tasks.html", tasks=tasks, users=users)


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    response = make_response(redirect("/activate"))
    response.delete_cookie("auth_token")
    return response


# ---------------- RENDER ENTRY ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

    
