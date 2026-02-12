def register_user(client, email, password="secret", is_admin=False):
    data = {
        "email": email,
        "password": password,
    }
    if is_admin:
        data["is_admin"] = "on"
    return client.post("/register", data=data, follow_redirects=True)


def login_user(client, email, password="secret"):
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def logout_user(client):
    return client.post("/logout", follow_redirects=True)


def create_appointment(client, title="פגישה", date_text="2026-01-01", time_text="09:00"):
    response = client.post(
        "/input",
        data={
            "title": title,
            "date": date_text,
            "time": time_text,
            "location": "תל אביב",
            "notes": "בדיקה",
            "status": "planned",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200


def fetch_one_appointment(db_module, appt_id):
    with db_module.get_cursor() as cur:
        cur.execute(
            """
            SELECT
                id,
                title,
                date_text,
                time_text,
                location,
                notes,
                status,
                owner_user_id,
                updated_at,
                status_updated_at,
                status_updated_by_user_id
            FROM testapp_appointments
            WHERE id = %s
            """,
            (appt_id,),
        )
        row = cur.fetchone()
    return row


def fetch_user_id_by_email(db_module, email):
    with db_module.get_cursor() as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
    return row[0]


def fetch_latest_appt_id(db_module):
    with db_module.get_cursor() as cur:
        cur.execute("SELECT id FROM testapp_appointments ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
    return row[0]


def test_regular_register_login_and_output_access(client):
    register_user(client, "user1@example.com")
    res = login_user(client, "user1@example.com")
    assert res.status_code == 200

    output = client.get("/output")
    assert output.status_code == 200
    text = output.get_data(as_text=True)
    assert "רשימת פגישות" in text


def test_admin_can_access_status_screen(client, db_module):
    register_user(client, "admin1@example.com", is_admin=True)
    login_user(client, "admin1@example.com")

    create_appointment(client, title="admin appt")
    appt_id = fetch_latest_appt_id(db_module)

    res = client.get(f"/status/{appt_id}")
    assert res.status_code == 200
    assert "שינוי סטטוס" in res.get_data(as_text=True)


def test_regular_user_cannot_access_status_and_no_button(client, db_module):
    register_user(client, "user2@example.com")
    login_user(client, "user2@example.com")
    create_appointment(client, title="regular appt")
    appt_id = fetch_latest_appt_id(db_module)

    output = client.get("/output")
    text = output.get_data(as_text=True)
    assert "שנה סטטוס" not in text

    res = client.post(
        f"/status/{appt_id}",
        data={"status": "canceled", "next": "/output"},
        follow_redirects=False,
    )
    assert res.status_code in (302, 403)


def test_admin_status_change_stores_audit_and_shown_on_status_page(client, db_module):
    register_user(client, "owner@example.com")
    login_user(client, "owner@example.com")
    create_appointment(client, title="owner appt")
    appt_id = fetch_latest_appt_id(db_module)
    logout_user(client)

    register_user(client, "admin2@example.com", is_admin=True)
    login_user(client, "admin2@example.com")
    admin_id = fetch_user_id_by_email(db_module, "admin2@example.com")

    res = client.post(
        f"/status/{appt_id}",
        data={"status": "canceled", "next": "/output"},
        follow_redirects=False,
    )
    assert res.status_code == 302

    row = fetch_one_appointment(db_module, appt_id)
    assert row is not None
    assert row[6] == "canceled"
    assert row[9] is not None
    assert row[10] == admin_id

    status_page = client.get(f"/status/{appt_id}")
    page_text = status_page.get_data(as_text=True)
    assert "admin2@example.com" in page_text
    assert "עדכון סטטוס אחרון" in page_text


def test_edit_cannot_change_date_or_status_and_updates_updated_at(client, db_module):
    register_user(client, "user3@example.com")
    login_user(client, "user3@example.com")
    create_appointment(client, title="before edit", date_text="2026-02-01", time_text="10:00")
    appt_id = fetch_latest_appt_id(db_module)

    before = fetch_one_appointment(db_module, appt_id)
    assert before[2] == "2026-02-01"
    assert before[6] == "planned"
    assert before[8] is None

    edit_res = client.post(
        f"/edit/{appt_id}",
        data={
            "title": "after edit",
            "time_text": "11:30",
            "location": "חיפה",
            "notes": "עודכן",
            "date_text": "2030-01-01",
            "status": "done",
        },
        follow_redirects=True,
    )
    assert edit_res.status_code == 200

    after_edit = fetch_one_appointment(db_module, appt_id)
    assert after_edit[1] == "after edit"
    assert after_edit[2] == "2026-02-01"
    assert after_edit[6] == "planned"
    assert after_edit[8] is not None

    updated_at_after_edit = after_edit[8]

    complete_res = client.post(f"/complete/{appt_id}", follow_redirects=True)
    assert complete_res.status_code == 200

    after_complete = fetch_one_appointment(db_module, appt_id)
    assert after_complete[6] == "done"
    assert after_complete[8] == updated_at_after_edit

    delete_res = client.post(f"/delete/{appt_id}", follow_redirects=True)
    assert delete_res.status_code == 200

    with db_module.get_cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM testapp_appointments WHERE id = %s", (appt_id,))
        count = cur.fetchone()[0]
    assert count == 0
