import os
import psycopg2


DDL = """
-- =========================
-- users
-- =========================
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  is_admin BOOLEAN NOT NULL DEFAULT FALSE,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =========================
-- testapp_appointments
-- =========================
CREATE TABLE IF NOT EXISTS testapp_appointments (
  id SERIAL PRIMARY KEY,
  owner_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,

  title TEXT NOT NULL,
  date_text TEXT NOT NULL,
  time_text TEXT NOT NULL,
  location TEXT,
  notes TEXT,

  status TEXT NOT NULL DEFAULT 'planned',
  updated_at TIMESTAMP,
  status_updated_at TIMESTAMP,
  status_updated_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,

  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- סטטוס מותר
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conname = 'testapp_appointments_status_check'
  ) THEN
    ALTER TABLE testapp_appointments
    ADD CONSTRAINT testapp_appointments_status_check
    CHECK (status IN ('planned', 'done', 'canceled'));
  END IF;
END $$;

-- אינדקסים שימושיים
CREATE INDEX IF NOT EXISTS idx_testapp_appointments_owner_user_id
  ON testapp_appointments(owner_user_id);

CREATE INDEX IF NOT EXISTS idx_testapp_appointments_created_at
  ON testapp_appointments(created_at);
"""


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL לא מוגדר")

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)

    print("DB init done")


if __name__ == "__main__":
    main()
