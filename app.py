import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename

from resume_parser import extract_text_from_file
from job_matcher import JobMatcher
from nlp_preprocessing import extract_skills_from_text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DB_PATH = os.path.join(BASE_DIR, "data.db")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# ---------- DATABASE ----------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            text TEXT,
            uploaded_at TEXT,
            ats_score REAL,
            best_job TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            skills TEXT
        )
    """)

    if conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO jobs (title, description, skills) VALUES (?, ?, ?)",
            [
                ("Python Developer", "Python Flask SQL", "python flask sql"),
                ("Data Analyst", "Python Pandas Data", "python pandas data"),
                ("ML Engineer", "Machine Learning Python", "python machine learning"),
            ]
        )
    conn.commit()
    conn.close()

init_db()

def load_skills():
    with open(os.path.join(BASE_DIR, "skills_list.txt")) as f:
        return [s.strip().lower() for s in f if s.strip()]

# ---------- ROUTES ----------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("resume")
    if not file or file.filename == "":
        return redirect(url_for("index"))

    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    text = extract_text_from_file(path)

    conn = get_db()
    conn.execute(
        "INSERT INTO resumes (filename, text, uploaded_at) VALUES (?, ?, ?)",
        (filename, text, datetime.utcnow().isoformat())
    )
    rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()

    return redirect(url_for("results", rid=rid))

@app.route("/results")
def results():
    rid = request.args.get("rid")
    conn = get_db()
    resume = conn.execute("SELECT * FROM resumes WHERE id=?", (rid,)).fetchone()
    jobs = conn.execute("SELECT * FROM jobs").fetchall()
    conn.close()

    matcher = JobMatcher(load_skills())
    matcher.fit(
        [j["description"] for j in jobs],
        [{"title": j["title"], "skills": j["skills"]} for j in jobs]
    )

    results = matcher.match(resume["text"])
    best = max(results, key=lambda x: x["score"])

    conn = get_db()
    conn.execute(
        "UPDATE resumes SET ats_score=?, best_job=? WHERE id=?",
        (best["ats"], best["job"], rid)
    )
    conn.commit()
    conn.close()

    return render_template(
        "results.html",
        results=results,
        ats_score=best["ats"],
        best_job=best["job"],
        skills=extract_skills_from_text(resume["text"], load_skills())
    )
