import os
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, jsonify

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "")

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


if __name__ == "__main__":
    app.run(debug=True, port=5051)
