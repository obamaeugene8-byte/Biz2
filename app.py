from flask import Flask, render_template, request, redirect
from config import Config
from models import db, User, Task, License, Company
import uuid
from datetime import datetime, timedelta
import os
import secrets

app = Flask(__name__)
app.config.from_object(Config)

# Render-safe secret
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key")

db.init_app(app)

# ==================================================
# SAFE DATABASE INIT
# ==================================================
with app.app_context():
    try:
        db.create_all()
    except Exception as e:
        print("DB INIT ERROR:", e)


# ==================================================
# HELPER: GET LICENSE
# ==================================================
def get_license_from_token(token):
    if not token:
        return None

    license = License.query.filter_by(auth_token=token).first()

    if not license:
        return None

    if license.expires_at and license.expires_at < datetime.utcnow():
        return None

    return license


# ==================================================
# ADMIN: CREATE 30-DAY LICENSE
# ==================================================
@app.route("/admin/create-license")
def create_license():
    try:
        code = uuid.uuid4().hex[:12].upper()

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

        return f"30-DAY LICENSE CREATED: {code}"

    except Exception as e:
        db.session.rollback()
        return f"ERROR (create-license): {str(e)}"


# ==================================================
# ADMIN: 24-HOUR TRIAL
# ==================================================
@app.route("/admin/create-trial")
def create_trial():
    try:
        code = uuid.uuid4().hex[:12].upper()

        company = Company(name=f"Trial-{code[:5]}")
        db.session.add(company)
        db.session.commit()

        license = License(
            code=code,
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            company_id=company.id,
            auth_token=None
        )

        db.session.add(license)
        db.session.commit()

        return f"24-HOUR TRIAL CREATED: {code}"

    except Exception as e:
        db.session.rollback()
        return f"ERROR (create-trial): {str(e)}"


# ==================================================
# ACTIVATION (GENERATES LOGIN LINK)
# ==================================================
@app.route("/activate", methods=["GET", "POST"])
def activate():

    if request.method == "POST":
        code = request.form.get("code")

        license = License.query.filter_by(code=code, is_active=True).first()

        if not license:
            return "Invalid license code"

        if license.expires_at and license.expires_at < datetime.utcnow():
            return "License expired"

        # generate token once
        if not license.auth_token:
            license.auth_token = secrets.token_hex(16)
            db.session.commit()

        return f"""
        <h2>✅ Activated Successfully</h2>

        <p><b>Your login link:</b></p>

        <a href="/portal/{license.auth_token}">
            /portal/{license.auth_token}
        </a>

        <br><br>
        <p>Save this link. It is your login system.</p>
        """

    return render_template("activate.html")


# ==================================================
# PORTAL (LOGIN SYSTEM)
# ==================================================
@app.route("/portal/<token>")
def portal(token):

    license = get_license_from_token(token)

    if not license:
        return redirect("/activate")

    users = User.query.filter_by(company_id=license.company_id).all()

    data = []

    for user in users:
        tasks = Task.query.filter_by(
            user_id=user.id,
            company_id=license.company_id
        ).all()

        total_hours = sum(t.estimated_hours or 0 for t in tasks)

        capacity = user.weekly_capacity or 1
        load = (total_hours / capacity) * 100

        recommendation = (
            "Overloaded" if load > 100 else
            "Near capacity" if load > 80 else
            "Can take more work" if load < 50 else
            "Balanced"
        )

        data.append({
            "name": user.name,
            "tasks": len(tasks),
            "hours": total_hours,
            "capacity": capacity,
            "load": round(load, 1),
            "recommendation": recommendation
        })

    return render_template("dashboard.html", data=data)


# ==================================================
# USERS
# ==================================================
@app.route("/users/<token>", methods=["GET", "POST"])
def users(token):

    license = get_license_from_token(token)
    if not license:
        return redirect("/activate")

    company_id = license.company_id

    if request.method == "POST":
        name = request.form.get("name")
        capacity = request.form.get("capacity")

        if not name or not capacity:
            return "Missing fields"

        try:
            capacity = int(capacity)
        except:
            return "Invalid capacity"

        user = User(
            name=name,
            weekly_capacity=capacity,
            company_id=company_id
        )

        db.session.add(user)
        db.session.commit()

        return redirect(f"/users/{token}")

    users_list = User.query.filter_by(company_id=company_id).all()
    return render_template("users.html", users=users_list)


# ==================================================
# TASKS
# ==================================================
@app.route("/tasks/<token>", methods=["GET", "POST"])
def tasks(token):

    license = get_license_from_token(token)
    if not license:
        return redirect("/activate")

    company_id = license.company_id
    users_list = User.query.filter_by(company_id=company_id).all()

    if request.method == "POST":
        try:
            task = Task(
                title=request.form.get("title"),
                estimated_hours=int(request.form.get("hours")),
                user_id=int(request.form.get("user_id")),
                company_id=company_id
            )

            db.session.add(task)
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            return f"Error: {str(e)}"
 + m to toggle the tab key moving focus. Alternatively
        return redirect(f"/tasks/{token}")

    tasks_list = Task.query.filter_by(company_id=company_id).all()
    return render_template("tasks.html", tasks=tasks_list, users=users_list)


# ==================================================
# RUN APP (RENDER SAFE)
# ==================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

    
