import os
import psycopg2
from contextlib import contextmanager


def get_db_connection():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL לא מוגדר")
    return psycopg2.connect(database_url)


@contextmanager
def get_cursor():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()


def init_db():
    with get_cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS testapp_appointments (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                date_text TEXT NOT NULL,
                time_text TEXT NOT NULL,
                location TEXT,
                notes TEXT,
                status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'done', 'canceled')),
                updated_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        cur.execute(
            """
            ALTER TABLE testapp_appointments
            ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'planned';
            """
        )
        cur.execute(
            """
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
            """
        )

        cur.execute(
            """
            ALTER TABLE testapp_appointments
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP;
            """
        )
        cur.execute(
            """
            ALTER TABLE testapp_appointments
            ADD COLUMN IF NOT EXISTS owner_user_id INTEGER;
            """
        )
        cur.execute(
            """
            ALTER TABLE testapp_appointments
            ADD COLUMN IF NOT EXISTS status_updated_at TIMESTAMP;
            """
        )
        cur.execute(
            """
            ALTER TABLE testapp_appointments
            ADD COLUMN IF NOT EXISTS status_updated_by_user_id INTEGER;
            """
        )
