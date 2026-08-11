"""
Creates the public-facing plots table on the live Postgres database and
seeds it from the local staff app's SQLite database. Only public-safe
fields are copied over -- explicitly NOT date_of_burial, notes, or the
headstone photo path.

Run this once after the Postgres database exists and DATABASE_URL is
set (Render provides this automatically for the web service once a
database is attached in the same project -- for a one-off local run,
copy the "External Database URL" from Render's Postgres dashboard).
"""
import os
import sqlite3
import psycopg2

DATABASE_URL = os.environ["DATABASE_URL"]
LOCAL_DB = os.path.join(os.path.dirname(__file__), "..", "app", "cemetery.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS plots (
    plot_number     INTEGER PRIMARY KEY,
    surname         TEXT,
    given_name      TEXT,
    date_of_birth   TEXT,
    date_of_death   TEXT,
    veteran_branch  TEXT
);
"""

def main():
    sconn = sqlite3.connect(LOCAL_DB)
    rows = sconn.execute(
        "SELECT plot_number, surname, given_name, date_of_birth, date_of_death, veteran_branch FROM plots"
    ).fetchall()
    sconn.close()

    pconn = psycopg2.connect(DATABASE_URL)
    cur = pconn.cursor()
    cur.execute(SCHEMA)
    cur.executemany(
        """INSERT INTO plots (plot_number, surname, given_name, date_of_birth, date_of_death, veteran_branch)
           VALUES (%s, %s, %s, %s, %s, %s)
           ON CONFLICT (plot_number) DO UPDATE SET
               surname=EXCLUDED.surname, given_name=EXCLUDED.given_name,
               date_of_birth=EXCLUDED.date_of_birth, date_of_death=EXCLUDED.date_of_death,
               veteran_branch=EXCLUDED.veteran_branch""",
        rows,
    )
    pconn.commit()
    cur.close()
    pconn.close()
    print(f"seeded/updated {len(rows)} plots on the live database")

if __name__ == "__main__":
    main()
