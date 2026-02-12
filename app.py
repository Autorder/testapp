import os
from functools import wraps

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_cursor, init_db

app = Flask(__name__)
app.secret_key = "dev-secret"
ALLOWED_STATUSES = {"planned", "done", "canceled"}


def format_timestamp(value):
    if not value:
        return ""
    return value.strftime("%Y-%m-%d %H:%M:%S")


def get_current_user():
    if hasattr(g, "current_user"):
        return g.current_user

    user_id = session.get("user_id")
    if not user_id:
        g.current_user = None
        return None

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, email, is_admin
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()

    if not row:
        session.pop("user_id", None)
        g.current_user = None
        return None

    g.current_user = {"id": row[0], "email": row[1], "is_admin": row[2]}
    return g.current_user


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not get_current_user():
            flash("יש להתחבר כדי להמשיך")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash("יש להתחבר כדי להמשיך")
            return redirect(url_for("login"))
        if not user["is_admin"]:
            abort(403)
        return view_func(*args, **kwargs)

    return wrapper


def sanitize_next_url(next_url):
    if not next_url or not next_url.startswith("/"):
        return url_for("list_appointments")
    return next_url


def fetch_appointments_for_owner(owner_user_id):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
                a.id,
                a.title,
                a.date_text,
                a.time_text,
                a.location,
                a.notes,
                a.status,
                a.updated_at,
                a.status_updated_at,
                a.created_at,
                owner_u.email AS owner_email,
                status_u.email AS status_updated_by_email
            FROM testapp_appointments a
            LEFT JOIN users owner_u ON owner_u.id = a.owner_user_id
            LEFT JOIN users status_u ON status_u.id = a.status_updated_by_user_id
            WHERE a.owner_user_id = %s
            ORDER BY a.id DESC
            """,
            (owner_user_id,),
        )
        rows = cur.fetchall()

    appointments = []
    for r in rows:
        appointments.append(
            {
                "id": r[0],
                "title": r[1],
                "date": r[2],
                "time": r[3],
                "location": r[4] or "",
                "notes": r[5] or "",
                "status": r[6],
                "updated_at": r[7],
                "updated_at_text": format_timestamp(r[7]),
                "status_updated_at": r[8],
                "status_updated_at_text": format_timestamp(r[8]),
                "created_at": r[9],
                "owner_email": r[10] or "",
                "status_updated_by_email": r[11] or "",
            }
        )
    return appointments


def load_user(user_id):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, email, is_admin
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        )
        row = cur.fetchone()

    if not row:
        return None
    return {"id": row[0], "email": row[1], "is_admin": row[2]}


@app.context_processor
def inject_current_user():
    return {"current_user": get_current_user()}


@app.get("/")
def home():
    if not get_current_user():
        return redirect(url_for("login"))
    return redirect(url_for("new_appointment"))


@app.get("/register")
def register():
    return render_template("register.html")


@app.post("/register")
def register_post():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    is_admin = bool(request.form.get("is_admin"))

    if not email or not password:
        flash("יש למלא אימייל וסיסמה")
        return redirect(url_for("register"))

    password_hash = generate_password_hash(password)

    with get_cursor() as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        existing = cur.fetchone()
        if existing:
            flash("האימייל כבר קיים")
            return redirect(url_for("register"))

        cur.execute(
            """
            INSERT INTO users (email, password_hash, is_admin)
            VALUES (%s, %s, %s)
            """,
            (email, password_hash, is_admin),
        )

    flash("ההרשמה בוצעה בהצלחה, אפשר להתחבר")
    return redirect(url_for("login"))


@app.get("/login")
def login():
    return render_template("login.html")


@app.post("/login")
def login_post():
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""

    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, password_hash
            FROM users
            WHERE email = %s
            """,
            (email,),
        )
        row = cur.fetchone()

    if not row or not check_password_hash(row[1], password):
        flash("אימייל או סיסמה שגויים")
        return redirect(url_for("login"))

    session["user_id"] = row[0]
    return redirect(url_for("list_appointments"))


@app.post("/logout")
@login_required
def logout():
    session.pop("user_id", None)
    flash("התנתקת מהמערכת")
    return redirect(url_for("login"))


@app.get("/input")
@login_required
def new_appointment():
    return render_template("input.html")


@app.post("/input")
@login_required
def create_appointment():
    user = get_current_user()
    title = (request.form.get("title") or "").strip()
    date_text = (request.form.get("date") or "").strip()
    time_text = (request.form.get("time") or "").strip()
    location = (request.form.get("location") or "").strip()
    notes = (request.form.get("notes") or "").strip()

    if not title or not date_text or not time_text:
        flash("חובה למלא נושא, תאריך ושעה")
        return redirect(url_for("new_appointment"))

    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO testapp_appointments (title, date_text, time_text, location, notes, status, owner_user_id)
            VALUES (%s, %s, %s, %s, %s, 'planned', %s)
            """,
            (title, date_text, time_text, location, notes, user["id"]),
        )

    return redirect(url_for("list_appointments"))


@app.get("/output")
@login_required
def list_appointments():
    user = get_current_user()
    appointments = fetch_appointments_for_owner(user["id"])
    return render_template(
        "output.html",
        appointments=appointments,
        view_user=user,
        show_owner_column=False,
        can_change_status=user["is_admin"],
        can_manage_fields=True,
        title_text="רשימת פגישות",
        current_path=request.path,
    )


@app.post("/delete/<int:appt_id>")
@login_required
def delete_appointment(appt_id: int):
    user = get_current_user()
    with get_cursor() as cur:
        cur.execute(
            """
            DELETE FROM testapp_appointments
            WHERE id = %s AND owner_user_id = %s
            """,
            (appt_id, user["id"]),
        )
        deleted = cur.rowcount

    if deleted == 0:
        flash("לא ניתן למחוק את הפגישה")
    return redirect(url_for("list_appointments"))


@app.post("/complete/<int:appt_id>")
@login_required
def complete_appointment(appt_id: int):
    user = get_current_user()
    with get_cursor() as cur:
        cur.execute(
            """
            UPDATE testapp_appointments
            SET status = 'done'
            WHERE id = %s AND owner_user_id = %s
            """,
            (appt_id, user["id"]),
        )
        updated = cur.rowcount

    if updated == 0:
        flash("לא ניתן לסמן את הפגישה כהושלמה")
    return redirect(url_for("list_appointments"))


@app.get("/edit/<int:appt_id>")
@login_required
def edit_appointment(appt_id: int):
    user = get_current_user()
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, title, date_text, time_text, location, notes, status, created_at
            FROM testapp_appointments
            WHERE id = %s AND owner_user_id = %s
            """,
            (appt_id, user["id"]),
        )
        row = cur.fetchone()

    if not row:
        flash("הפגישה לא נמצאה")
        return redirect(url_for("list_appointments"))

    appointment = {
        "id": row[0],
        "title": row[1],
        "date": row[2],
        "time": row[3],
        "location": row[4] or "",
        "notes": row[5] or "",
        "status": row[6],
        "created_at": row[7],
    }
    return render_template("edit.html", appointment=appointment)


@app.post("/edit/<int:appt_id>")
@login_required
def update_appointment(appt_id: int):
    user = get_current_user()
    title = (request.form.get("title") or "").strip()
    time_text = (request.form.get("time_text") or "").strip()
    location = (request.form.get("location") or "").strip()
    notes = (request.form.get("notes") or "").strip()

    if not title or not time_text:
        flash("חובה למלא נושא ושעה")
        return redirect(url_for("edit_appointment", appt_id=appt_id))

    with get_cursor() as cur:
        cur.execute(
            """
            UPDATE testapp_appointments
            SET title = %s,
                time_text = %s,
                location = %s,
                notes = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND owner_user_id = %s
            """,
            (title, time_text, location, notes, appt_id, user["id"]),
        )
        updated = cur.rowcount

    if updated == 0:
        flash("לא ניתן לעדכן את הפגישה")
    return redirect(url_for("list_appointments"))


@app.get("/status/<int:appt_id>")
@admin_required
def status_page(appt_id: int):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT
                a.id,
                a.title,
                a.date_text,
                a.time_text,
                a.location,
                a.notes,
                a.status,
                owner_u.email,
                a.status_updated_at,
                status_u.email
            FROM testapp_appointments a
            LEFT JOIN users owner_u ON owner_u.id = a.owner_user_id
            LEFT JOIN users status_u ON status_u.id = a.status_updated_by_user_id
            WHERE a.id = %s
            """,
            (appt_id,),
        )
        row = cur.fetchone()

    if not row:
        flash("הפגישה לא נמצאה")
        return redirect(url_for("list_appointments"))

    appointment = {
        "id": row[0],
        "title": row[1],
        "date": row[2],
        "time": row[3],
        "location": row[4] or "",
        "notes": row[5] or "",
        "status": row[6],
        "owner_email": row[7] or "",
        "status_updated_at_text": format_timestamp(row[8]),
        "status_updated_by_email": row[9] or "",
    }
    back_url = sanitize_next_url(request.args.get("next"))
    return render_template("status.html", appointment=appointment, back_url=back_url)


@app.post("/status/<int:appt_id>")
@admin_required
def status_update(appt_id: int):
    user = get_current_user()
    status = (request.form.get("status") or "").strip().lower()
    back_url = sanitize_next_url(request.form.get("next"))

    if status not in ALLOWED_STATUSES:
        flash("סטטוס לא תקין")
        return redirect(url_for("status_page", appt_id=appt_id, next=back_url))

    with get_cursor() as cur:
        cur.execute(
            """
            UPDATE testapp_appointments
            SET status = %s,
                status_updated_at = CURRENT_TIMESTAMP,
                status_updated_by_user_id = %s
            WHERE id = %s
            """,
            (status, user["id"], appt_id),
        )
        updated = cur.rowcount

    if updated == 0:
        flash("לא ניתן לעדכן סטטוס")
    else:
        flash("הסטטוס עודכן")
    return redirect(back_url)


@app.get("/admin/users")
@admin_required
def admin_users():
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, email, is_admin, created_at
            FROM users
            ORDER BY id ASC
            """
        )
        rows = cur.fetchall()

    users = [
        {
            "id": r[0],
            "email": r[1],
            "is_admin": r[2],
            "created_at": r[3],
            "created_at_text": format_timestamp(r[3]),
        }
        for r in rows
    ]
    return render_template("admin_users.html", users=users)


@app.get("/admin/users/<int:user_id>/appointments")
@admin_required
def admin_user_appointments(user_id: int):
    user = load_user(user_id)
    if not user:
        flash("המשתמש לא נמצא")
        return redirect(url_for("admin_users"))

    current = get_current_user()
    appointments = fetch_appointments_for_owner(user_id)
    return render_template(
        "output.html",
        appointments=appointments,
        view_user=user,
        show_owner_column=current["id"] != user_id,
        can_change_status=True,
        can_manage_fields=current["id"] == user_id,
        title_text=f"רשימת פגישות עבור {user['email']}",
        current_path=request.path,
    )


if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", "5056"))
    app.run(host="127.0.0.1", port=port, debug=True)
