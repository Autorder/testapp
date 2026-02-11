from flask import Flask, render_template, request, redirect, url_for, flash
from db import init_db, get_cursor
import os


app = Flask(__name__)
app.secret_key = "dev-secret"
ALLOWED_STATUSES = {"planned", "done", "canceled"}


def format_timestamp(value):
    if not value:
        return ""
    return value.strftime("%Y-%m-%d %H:%M:%S")


@app.get("/")
def home():
    return redirect(url_for("new_appointment"))


@app.get("/input")
def new_appointment():
    return render_template("input.html")


@app.post("/input")
def create_appointment():
    title = (request.form.get("title") or "").strip()
    date_text = (request.form.get("date") or "").strip()
    time_text = (request.form.get("time") or "").strip()
    location = (request.form.get("location") or "").strip()
    notes = (request.form.get("notes") or "").strip()
    status = (request.form.get("status") or "planned").strip().lower()

    if not title or not date_text or not time_text:
        flash("חובה למלא נושא, תאריך ושעה")
        return redirect(url_for("new_appointment"))
    if status not in ALLOWED_STATUSES:
        flash("סטטוס לא תקין")
        return redirect(url_for("new_appointment"))

    with get_cursor() as cur:
        cur.execute(
            """
            INSERT INTO testapp_appointments (title, date_text, time_text, location, notes, status)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (title, date_text, time_text, location, notes, status),
        )

    return redirect(url_for("list_appointments"))


@app.get("/output")
def list_appointments():
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, title, date_text, time_text, location, notes, status, updated_at, created_at
            FROM testapp_appointments
            ORDER BY id DESC
            """
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
                "created_at": r[8],
            }
        )

    return render_template("output.html", appointments=appointments)


@app.post("/delete/<int:appt_id>")
def delete_appointment(appt_id: int):
    with get_cursor() as cur:
        cur.execute("DELETE FROM testapp_appointments WHERE id = %s", (appt_id,))
    return redirect(url_for("list_appointments"))


@app.post("/complete/<int:appt_id>")
def complete_appointment(appt_id: int):
    with get_cursor() as cur:
        cur.execute(
            "UPDATE testapp_appointments SET status = 'done' WHERE id = %s",
            (appt_id,),
        )
    return redirect(url_for("list_appointments"))


@app.get("/edit/<int:appt_id>")
def edit_appointment(appt_id: int):
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT id, title, date_text, time_text, location, notes, status, created_at
            FROM testapp_appointments
            WHERE id = %s
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
        "created_at": row[7],
    }
    return render_template("edit.html", appointment=appointment)


@app.post("/edit/<int:appt_id>")
def update_appointment(appt_id: int):
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
            WHERE id = %s
            """,
            (title, time_text, location, notes, appt_id),
        )

    return redirect(url_for("list_appointments"))


if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", "5056"))
    app.run(host="127.0.0.1", port=port, debug=True)
