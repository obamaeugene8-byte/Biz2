from flask import Flask, render_template, request, redirect, session
from config import Config
from models import db, User, Task, License
from datetime import datetime

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = "super-secret-key"
db.init_app(app)

with app.app_context():
    db.create_all()

# ---------------- LICENSE ACTIVATION ----------------
@app.route("/activate", methods=["GET", "POST"])
def activate():
    if request.method == "POST":
        code = request.form["code"]

        license = License.query.filter_by(code=code, is_active=True).first()

        if license:
            if license.expires_at and license.expires_at < datetime.utcnow():
                return "License expired"

            session["licensed"] = True
            return redirect("/")

        return "Invalid license code"

    return render_template("activate.html")


# ---------------- DASHBOARD ----------------
@app.route("/")
def dashboard():
    if not session.get("licensed"):
        return redirect("/activate")

    users = User.query.all()

    data = []

    for user in users:
        tasks = Task.query.filter_by(user_id=user.id).all()
        total_hours = sum(t.estimated_hours for t in tasks)

        load = (total_hours / user.weekly_capacity) * 100 if user.weekly_capacity else 0

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

    if request.method == "POST":
        name = request.form["name"]
        capacity = request.form["capacity"]

        user = User(name=name, weekly_capacity=capacity)
        db.session.add(user)
        db.session.commit()
        return redirect("/users")

    users = User.query.all()
    return render_template("users.html", users=users)


# ---------------- TASKS ----------------
@app.route("/tasks", methods=["GET", "POST"])
def tasks():
    if not session.get("licensed"):
        return redirect("/activate")

    users = User.query.all()

    if request.method == "POST":
        title = request.form["title"]
        hours = request.form["hours"]
        user_id = request.form["user_id"]

        task = Task(title=title, estimated_hours=hours, user_id=user_id)
        db.session.add(task)
        db.session.commit()
        return redirect("/tasks")

    tasks = Task.query.all()
    return render_template("tasks.html", tasks=tasks, users=users)


if __name__ == "__main__":
    app.run(debug=True)
