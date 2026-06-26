"""
=============================================================
  CAMPUS PLACEMENT PORTAL — BACKEND SERVER
=============================================================
  WHAT IS THIS FILE?
  This is the "brain" of our backend. It defines all the
  API endpoints (URLs) that the frontend can call.

  WHAT IS FLASK?
  Flask is a lightweight Python web framework. It lets you
  create web servers with just a few lines of code.

  HOW TO RUN 3 INSTANCES:
  Terminal 1: python app.py 5001
  Terminal 2: python app.py 5002
  Terminal 3: python app.py 5003
=============================================================
"""

import sys
import os
import re
import time
import uuid
import sqlite3
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# ─────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────

# Create the Flask application
app = Flask(__name__)

# CORS = Cross-Origin Resource Sharing
# This allows our frontend (running on a different port)
# to talk to this backend. Without this, browsers block it.
CORS(app)

# Each instance gets its port number from command line
# sys.argv[1] means "first argument after the script name"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5001

# Database file path — all 3 instances share ONE database
DB_PATH = os.path.join(os.path.dirname(__file__), "placement.db")

# Resume upload directory — shared by all 3 server instances
RESUME_DIR = os.path.join(os.path.dirname(__file__), "resumes")
os.makedirs(RESUME_DIR, exist_ok=True)

# Allowed resume file types
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}

def allowed_file(filename):
    """Check if file has an allowed extension."""
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


# ─────────────────────────────────────────────
# DATABASE HELPER
# ─────────────────────────────────────────────

def get_db():
    """
    Opens a connection to our SQLite database.
    Think of this like opening a notebook to write/read data.
    We call this inside each request and close it after.
    """
    conn = sqlite3.connect(DB_PATH)
    # This makes rows return as dictionaries {column: value}
    # instead of plain tuples (value, value, value)
    conn.row_factory = sqlite3.Row
    return conn


# ─────────────────────────────────────────────
# VALIDATION HELPERS
# ─────────────────────────────────────────────

def validate_email(email):
    """
    CONCEPT: Server-Side Validation
    Never trust user input — always validate on the server too!
    This regex checks for a valid email format like name@domain.com
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_phone(phone):
    """
    Validates a 10-digit Indian mobile number.
    Must start with 6, 7, 8, or 9.
    """
    pattern = r'^[6-9]\d{9}$'
    return bool(re.match(pattern, phone))


def validate_name(name):
    """
    Validates a student name: 2-50 characters, letters and spaces only.
    """
    pattern = r'^[A-Za-z\s]{2,50}$'
    return bool(re.match(pattern, name))


def validate_roll_number(roll):
    """
    Validates roll number formats:
    - College format: 1602-23-737-139
    - Short format: 21CS001
    """
    pattern = r'^(\d{4}-\d{2}-\d{3}-\d{3}|[0-9]{2}[A-Z]{2,4}[0-9]{2,4})$'
    return bool(re.match(pattern, roll))


# ─────────────────────────────────────────────
# ROUTE 1 — HEALTH CHECK
# ─────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    """
    CONCEPT: Health Check Endpoint
    The load balancer pings this URL to check if this
    server is alive. If it returns 200 OK, traffic is sent here.
    If it fails, the load balancer skips this server automatically.

    This is how "high availability" works in practice!
    """
    return jsonify({
        "status": "ok",
        "server_port": PORT,
        "timestamp": datetime.now().isoformat()
    }), 200


# ─────────────────────────────────────────────
# ROUTE 2 — GET ALL JOB POSTINGS
# ─────────────────────────────────────────────

@app.route("/api/jobs", methods=["GET"])
def get_jobs():
    """
    CONCEPT: GET Request
    The frontend calls this to fetch all available job listings.
    We query the database and return the results as JSON.

    JSON = JavaScript Object Notation
    It's the universal language between frontend and backend.
    """
    # Simulate some processing time (realistic for a real server)
    # Remove this in production!
    start_time = time.time()

    conn = get_db()
    cursor = conn.cursor()

    # SQL query: fetch all jobs, newest first
    cursor.execute("""
        SELECT j.id, j.title, j.company, j.description,
               j.location, j.package_lpa, j.deadline,
               j.created_at,
               COUNT(a.id) as application_count
        FROM jobs j
        LEFT JOIN applications a ON j.id = a.job_id
        GROUP BY j.id
        ORDER BY j.created_at DESC
    """)

    jobs = cursor.fetchall()
    conn.close()

    # Convert sqlite3.Row objects to plain dictionaries
    jobs_list = [dict(job) for job in jobs]

    response_time = round((time.time() - start_time) * 1000, 2)

    return jsonify({
        "jobs": jobs_list,
        "count": len(jobs_list),
        "served_by_port": PORT,          # So we can see load balancing in action!
        "response_time_ms": response_time
    }), 200


# ─────────────────────────────────────────────
# ROUTE 3 — GET SINGLE JOB
# ─────────────────────────────────────────────

@app.route("/api/jobs/<int:job_id>", methods=["GET"])
def get_job(job_id):
    """
    CONCEPT: URL Parameters
    The <int:job_id> part is a dynamic segment.
    Calling /api/jobs/3 will pass job_id=3 to this function.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    job = cursor.fetchone()
    conn.close()

    if not job:
        # HTTP 404 = Not Found
        return jsonify({"error": "Job not found"}), 404

    return jsonify(dict(job)), 200


# ─────────────────────────────────────────────
# ROUTE 4 — STUDENT APPLIES FOR A JOB
# ─────────────────────────────────────────────

@app.route("/api/apply", methods=["POST"])
def apply_for_job():
    """
    CONCEPT: POST Request + File Upload + Server-Side Validation
    When a student clicks "Apply", the frontend sends
    their data as multipart/form-data (because of the resume file).
    We validate all fields, save the resume, and store in database.

    POST is used when you're CREATING new data.
    multipart/form-data is used when uploading files.
    """
    # Parse form fields (multipart/form-data, not JSON)
    student_name = request.form.get("student_name", "").strip()
    email = request.form.get("email", "").strip()
    phone_number = request.form.get("phone_number", "").strip()
    roll_number = request.form.get("roll_number", "").strip()
    job_id = request.form.get("job_id", "")
    cgpa_str = request.form.get("cgpa", "")
    resume_file = request.files.get("resume")

    # Basic field presence check — never trust user input!
    if not all([student_name, email, phone_number, roll_number, job_id, cgpa_str]):
        return jsonify({"error": "All fields are required"}), 400

    # ── SERVER-SIDE VALIDATION ──────────────────────────────
    if not validate_name(student_name):
        return jsonify({"error": "Invalid name. Use 2-50 characters, letters and spaces only."}), 400
    if not validate_email(email):
        return jsonify({"error": "Invalid email format. Use format: name@domain.com"}), 400
    if not validate_phone(phone_number):
        return jsonify({"error": "Invalid phone number. Must be a 10-digit Indian mobile number."}), 400
    if not validate_roll_number(roll_number):
        return jsonify({"error": "Invalid roll number. Use format: 1602-23-737-139 or 21CS001"}), 400

    try:
        cgpa = float(cgpa_str)
        if cgpa < 0 or cgpa > 10:
            return jsonify({"error": "CGPA must be between 0 and 10"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "CGPA must be a valid number"}), 400

    try:
        job_id = int(job_id)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid job ID"}), 400

    # ── RESUME FILE VALIDATION ──────────────────────────────
    resume_filename = None
    if resume_file and resume_file.filename:
        if not allowed_file(resume_file.filename):
            return jsonify({"error": "Resume must be PDF, DOC, or DOCX"}), 400
        # Generate unique filename to avoid collisions
        ext = os.path.splitext(resume_file.filename)[1].lower()
        resume_filename = f"{roll_number}_{uuid.uuid4().hex[:8]}{ext}"
        resume_file.save(os.path.join(RESUME_DIR, resume_filename))
    else:
        return jsonify({"error": "Resume file is required (PDF, DOC, or DOCX)"}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Check if job exists
    cursor.execute("SELECT id FROM jobs WHERE id = ?", (job_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({"error": "Job not found"}), 404

    # Check if student already applied for this job
    cursor.execute(
        "SELECT id FROM applications WHERE email = ? AND job_id = ?",
        (email, job_id)
    )
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "You have already applied for this job"}), 409

    # Insert the application into the database
    cursor.execute("""
        INSERT INTO applications (student_name, email, phone_number, roll_number, job_id, cgpa, resume_filename, applied_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        student_name, email, phone_number, roll_number,
        job_id, cgpa, resume_filename,
        datetime.now().isoformat()
    ))

    conn.commit()
    application_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "message": "Application submitted successfully!",
        "application_id": application_id,
        "served_by_port": PORT
    }), 201


# ─────────────────────────────────────────────
# ROUTE 4B — DOWNLOAD RESUME
# ─────────────────────────────────────────────

@app.route("/api/resumes/<filename>", methods=["GET"])
def download_resume(filename):
    """
    CONCEPT: Static File Serving
    Admin can download any student's resume via this endpoint.
    send_from_directory safely serves files from the resumes folder.
    """
    return send_from_directory(RESUME_DIR, filename, as_attachment=True)


# ─────────────────────────────────────────────
# ROUTE 5 — ADMIN: POST A NEW JOB
# ─────────────────────────────────────────────

@app.route("/api/admin/jobs", methods=["POST"])
def post_job():
    """
    CONCEPT: Admin-only endpoint
    In a real system this would require authentication/login.
    For now, we keep it simple and open.
    """
    data = request.get_json()

    required_fields = ["title", "company", "description", "location", "package_lpa", "deadline"]
    for field in required_fields:
        if not data or field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO jobs (title, company, description, location, package_lpa, deadline, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["title"],
        data["company"],
        data["description"],
        data["location"],
        data["package_lpa"],
        data["deadline"],
        datetime.now().isoformat()
    ))
    conn.commit()
    job_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "message": "Job posted successfully!",
        "job_id": job_id,
        "served_by_port": PORT
    }), 201


# ─────────────────────────────────────────────
# ROUTE 6 — ADMIN: VIEW ALL APPLICATIONS
# ─────────────────────────────────────────────

@app.route("/api/admin/applications", methods=["GET"])
def get_all_applications():
    """
    CONCEPT: JOIN Query
    We fetch data from two tables at once (jobs + applications)
    using a JOIN — linking them by the job_id foreign key.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.id, a.student_name, a.email, a.phone_number,
               a.roll_number, a.cgpa, a.resume_filename, a.applied_at,
               j.title as job_title, j.company
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        ORDER BY a.applied_at DESC
    """)
    applications = cursor.fetchall()
    conn.close()

    return jsonify({
        "applications": [dict(app) for app in applications],
        "count": len(applications),
        "served_by_port": PORT
    }), 200


# ─────────────────────────────────────────────
# ROUTE 7 — LOAD TESTING ENDPOINT
# ─────────────────────────────────────────────

@app.route("/api/stats", methods=["GET"])
def get_stats():
    """
    CONCEPT: Performance Metrics
    Locust will hammer this endpoint during load testing.
    We return basic server stats so we can measure
    response time and throughput under heavy traffic.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM jobs")
    total_jobs = cursor.fetchone()["total"]
    cursor.execute("SELECT COUNT(*) as total FROM applications")
    total_applications = cursor.fetchone()["total"]
    conn.close()

    return jsonify({
        "total_jobs": total_jobs,
        "total_applications": total_applications,
        "server_port": PORT,
        "uptime": "running",
        "timestamp": datetime.now().isoformat()
    }), 200


# ─────────────────────────────────────────────
# START THE SERVER
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════╗
║   Placement Portal Backend Starting...   ║
║   Port: {PORT}                              ║
║   Database: {DB_PATH}  ║
╚══════════════════════════════════════════╝
    """)
    # debug=True → auto-restarts when you save the file
    # host="0.0.0.0" → accepts connections from all network interfaces
    app.run(host="0.0.0.0", port=PORT, debug=True)
