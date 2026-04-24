from flask import Flask, render_template, request, redirect, session
from config import Config
from models import db, User, Task, License, Company
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = "super-secret-key"

db.init_app(app)

with app.app_context():
    db.create_all()

    # Ensure at least one company exists
    if not Company.query.first():
        default_company = Company(name="Default Company")
        db.session.add(default_company)
        db.session.commit()


# ---------------- ADMIN LICENSE CREATOR ----------------
@app.route("/admin/create-license")
def create_license():
    code = str(uuid.uuid4()).replace("-", "")[:12].upper()

    license = License(
        code=code,
        is_active=True,
        expires_at=datetime.utcnow() + timedelta(days=30)
    )

    db.session.add(license)
    db.session.commit()

    return f"License created: {code}"


# ---------------- LICENSE ACTIVATION ----------------
@app.route("/activate", methods=["GET", "POST"])
def activate():
    if request.method == "POST":
        code = request.form.get("code")

        license = License.query.filter_by(code=code, is_active=True).first()

        if not license:
            return "Invalid license code"

        if license.expires_at and license.expires_at < datetime.utcnow():
            return "License expired"

        session["licensed"] = True

        # TEMP: assign all users to first company
        company = Company.query.first()
        session["company_id"] = company.id

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
        tasks = Task.query.filter_by(user_id=user.id).all()
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
        name = request.form.get("name")
        capacity = request.form.get("capacity")

        if not name or not capacity:
            return "Missing data"

        user = User(
            name=name,
            weekly_capacity=int(capacity),
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
        title = request.form.get("title")
        hours = request.form.get("hours")
        user_id = request.form.get("user_id")

        if not title or not hours or not user_id:
            return "Missing data"

        task = Task(
            title=title,
            estimated_hours=int(hours),
            user_id=int(user_id),
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


if __name__ == "__main__":
    app.run(debug=True)




        
