import hmac
import os
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")
SYNC_SECRET = os.environ.get("SYNC_SECRET", "")

MIGRATIONS = """
ALTER TABLE plots ADD COLUMN IF NOT EXISTS date_of_burial TEXT;
ALTER TABLE plots ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE plots ADD COLUMN IF NOT EXISTS headstone_photo BYTEA;
ALTER TABLE plots ADD COLUMN IF NOT EXISTS headstone_photo_filename TEXT;
"""

VETERAN_BADGES = {
    "Unknown": ("US Veteran", "#7a2f2f"),
    "Army": ("US Army Veteran", "#4b5320"),
    "Navy": ("US Navy Veteran", "#000080"),
    "Air Force": ("US Air Force Veteran", "#00308F"),
    "Marines": ("US Marine Veteran", "#8B0000"),
    "Coast Guard": ("US Coast Guard Veteran", "#003366"),
    "Space Force": ("US Space Force Veteran", "#1C2951"),
}


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def run_migrations():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(MIGRATIONS)
    conn.commit()
    cur.close()
    conn.close()


run_migrations()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/plots")
def api_plots():
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT plot_number, surname, given_name, date_of_birth, date_of_death, veteran_branch FROM plots"
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    data = {}
    for r in rows:
        badge = VETERAN_BADGES.get(r["veteran_branch"]) if r["veteran_branch"] else None
        data[str(r["plot_number"])] = {
            "surname": r["surname"] or "",
            "given_name": r["given_name"] or "",
            "dob": str(r["date_of_birth"] or ""),
            "dod": str(r["date_of_death"] or ""),
            "badge": {"label": badge[0], "color": badge[1]} if badge else None,
        }
    return jsonify(data)


@app.route("/api/sync", methods=["POST"])
def api_sync():
    """
    Receives a full record push from the staff records app -- every field,
    including the ones never shown on the public page (notes, burial date,
    headstone photo). This is the actual backup mechanism: if a client's
    local computer is ever lost, everything needed to rebuild it lives here.
    """
    provided_secret = request.headers.get("X-Sync-Secret", "")
    if not SYNC_SECRET or not hmac.compare_digest(provided_secret, SYNC_SECRET):
        return jsonify({"error": "unauthorized"}), 401

    plot_number = request.form.get("plot_number", "").strip()
    if not plot_number.isdigit():
        return jsonify({"error": "plot_number required"}), 400

    fields = {
        "surname": request.form.get("surname", "").strip(),
        "given_name": request.form.get("given_name", "").strip(),
        "date_of_birth": request.form.get("date_of_birth", "").strip(),
        "date_of_death": request.form.get("date_of_death", "").strip(),
        "date_of_burial": request.form.get("date_of_burial", "").strip(),
        "veteran_branch": request.form.get("veteran_branch", "").strip(),
        "notes": request.form.get("notes", "").strip(),
    }

    photo = request.files.get("headstone_photo")
    photo_bytes = photo.read() if photo and photo.filename else None
    photo_filename = photo.filename if photo and photo.filename else None

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM plots WHERE plot_number=%s", (plot_number,))
    exists = cur.fetchone()

    if photo_bytes:
        if exists:
            cur.execute(
                """UPDATE plots SET surname=%s, given_name=%s, date_of_birth=%s, date_of_death=%s,
                   date_of_burial=%s, veteran_branch=%s, notes=%s, headstone_photo=%s,
                   headstone_photo_filename=%s WHERE plot_number=%s""",
                (*fields.values(), photo_bytes, photo_filename, plot_number),
            )
        else:
            cur.execute(
                """INSERT INTO plots (plot_number, surname, given_name, date_of_birth, date_of_death,
                   date_of_burial, veteran_branch, notes, headstone_photo, headstone_photo_filename)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (plot_number, *fields.values(), photo_bytes, photo_filename),
            )
    else:
        if exists:
            cur.execute(
                """UPDATE plots SET surname=%s, given_name=%s, date_of_birth=%s, date_of_death=%s,
                   date_of_burial=%s, veteran_branch=%s, notes=%s WHERE plot_number=%s""",
                (*fields.values(), plot_number),
            )
        else:
            cur.execute(
                """INSERT INTO plots (plot_number, surname, given_name, date_of_birth, date_of_death,
                   date_of_burial, veteran_branch, notes)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (plot_number, *fields.values()),
            )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "ok", "plot_number": plot_number})


if __name__ == "__main__":
    app.run(debug=True, port=5051)
