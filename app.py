from flask import Flask, render_template, request, redirect, session
from config import Config
from models import db, User, Task, License, Company
import uuid
from datetime import datetime, timedelta
import os

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
        company_id=company.id
    )

    db.session.add(license)
    db.session.commit()

    return f"License created: {code}"


# ---------------- LICENSE ACTIVATION (UPDATED) ----------------
@app.route("/activate", methods=["GET", "POST"])
def activate():

    # ---------------- AUTO-LOGIN IF ALREADY ACTIVATED ----------------
    license_code = session.get("license_code")
    company_id = session.get("company_id")

    if license_code and company_id:
        license = License.query.filter_by(code=license_code).first()

        if license and license.expires_at and license.expires_at > datetime.utcnow():
            return redirect("/")  # SKIP ACTIVATION

        # if expired → clear session
        session.clear()

    # ---------------- MANUAL ACTIVATION ----------------
    if request.method == "POST":
        code = request.form.get("code")

        license = License.query.filter_by(code=code, is_active=True).first()

        if not license:
            return "Invalid license code"

        if license.expires_at and license.expires_at < datetime.utcnow():
            return "License expired"

        # store activation state
        session["licensed"] = True
        session["company_id"] = license.company_id
        session["license_code"] = license.code

        return redirect("/")

    return render_template("activate.html")


# ---------------- DASHBOARD ----------------
@app.route("/")
def dashboard():
    if not session.get("licensed"):
        return redirect("/activate")

    company_id = session.get("company_id")

    users = User.query.filter_by(company_id=company_id).all()

    data = []

    for user in users:
        tasks = Task.query.filter_by(user_id=user.id, company_id=company_id).all()
        total_hours = sum(t.estimated_hours or 0 for t in tasks)

        capacity = user.weekly_capacity or 1
        load = (total_hours / capacity) * 100

        data.append({
            "name": user.name,
            "tasks": len(tasks),
            "hours": total_hours,
            "capacity": user.weekly_capacity,
            "load": round(load, 1)
        })

    return render_template("dashboard.html", data=data)


# ---------------- USERS ----------------
@app.route("/users", methods=["GET", "POST"])
def users():
    if not session.get("licensed"):
        return redirect("/activate")

    company_id = session.get("company_id")

    if request.method == "POST":
        user = User(
            name=request.form.get("name"),
            weekly_capacity=int(request.form.get("capacity")),
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
    if not session.get("licensed"):
        return redirect("/activate")

    company_id = session.get("company_id")
    users = User.query.filter_by(company_id=company_id).all()

    if request.method == "POST":
        task = Task(
            title=request.form.get("title"),
            estimated_hours=int(request.form.get("hours")),
            user_id=int(request.form.get("user_id")),
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
    session.clear()
    return redirect("/activate")


# ---------------- RENDER ENTRY POINT ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

        
    
