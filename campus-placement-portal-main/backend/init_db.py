"""
=============================================================
  DATABASE SETUP SCRIPT — init_db.py
=============================================================
  WHAT IS THIS?
  This script creates our SQLite database with two tables:
    1. jobs       — job postings by companies
    2. applications — student applications

  WHAT IS SQLite?
  SQLite is a file-based database. No server needed!
  All data is stored in a single file: placement.db
  Perfect for learning and local development.

  HOW TO RUN:
    python init_db.py

  Run this ONCE before starting the backend servers.
  If you run it again, it will reset all data.
=============================================================
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "placement.db")


def create_tables(conn):
    """
    CONCEPT: Database Schema
    A schema is the structure/blueprint of your database.
    We define what columns each table has and their data types.
    """
    cursor = conn.cursor()

    # ── TABLE 1: jobs ──────────────────────────────────────
    # Stores all job postings created by the placement cell
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT    NOT NULL,
            company      TEXT    NOT NULL,
            description  TEXT    NOT NULL,
            location     TEXT    NOT NULL,
            package_lpa  REAL    NOT NULL,
            deadline     TEXT    NOT NULL,
            created_at   TEXT    NOT NULL
        )
    """)
    # AUTOINCREMENT → each new job gets a unique id (1, 2, 3...)
    # NOT NULL      → these fields are mandatory
    # REAL          → decimal number (e.g. 12.5 LPA)

    # ── TABLE 2: applications ──────────────────────────────
    # Stores every student's application for a job
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name    TEXT    NOT NULL,
            email           TEXT    NOT NULL,
            phone_number    TEXT    NOT NULL,
            roll_number     TEXT    NOT NULL,
            job_id          INTEGER NOT NULL,
            cgpa            REAL    NOT NULL,
            resume_filename TEXT,
            applied_at      TEXT    NOT NULL,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)
    # FOREIGN KEY → job_id links to the jobs table
    # This is a relationship: one job can have many applications
    # phone_number → 10-digit Indian mobile number

    conn.commit()
    print("✓ Tables created successfully")


def seed_sample_data(conn):
    """
    CONCEPT: Seed Data
    Real apps need test data during development.
    We insert 15 sample jobs so the frontend has plenty of
    job listings for demonstration and testing purposes.
    """
    cursor = conn.cursor()

    sample_jobs = [
        (
            "Software Engineer",
            "Infosys",
            "Join our digital transformation team. Work on enterprise Java applications, "
            "REST APIs, and cloud migrations. Ideal for students with strong DSA skills.",
            "Bangalore",
            9.5,
            "2025-06-30",
            "2025-05-01T10:00:00"
        ),
        (
            "Data Analyst",
            "TCS",
            "Analyze large datasets to derive business insights. Use Python, SQL, and "
            "Tableau. Work with Fortune 500 clients across finance and retail domains.",
            "Chennai",
            7.0,
            "2025-07-15",
            "2025-05-02T11:00:00"
        ),
        (
            "Frontend Developer",
            "Wipro",
            "Build responsive web interfaces using React.js and TypeScript. "
            "Collaborate with UX designers and backend teams in an agile environment.",
            "Hyderabad",
            8.0,
            "2025-07-01",
            "2025-05-03T09:00:00"
        ),
        (
            "Cloud Engineer",
            "Accenture",
            "Design and deploy cloud infrastructure on AWS and Azure. "
            "Experience with Docker, Kubernetes, and CI/CD pipelines preferred.",
            "Pune",
            11.0,
            "2025-06-20",
            "2025-05-04T14:00:00"
        ),
        (
            "ML Engineer",
            "HCL Technologies",
            "Develop and deploy machine learning models for NLP and computer vision. "
            "Strong Python, TensorFlow/PyTorch skills required. Research-oriented role.",
            "Noida",
            13.0,
            "2025-08-01",
            "2025-05-05T10:30:00"
        ),
        (
            "DevOps Engineer",
            "Amazon",
            "Automate CI/CD pipelines and manage scalable infrastructure on AWS. "
            "Work with EC2, Lambda, S3, and CloudFormation. On-call rotation required.",
            "Hyderabad",
            18.0,
            "2025-07-20",
            "2025-05-06T09:00:00"
        ),
        (
            "Full Stack Developer",
            "Flipkart",
            "Build end-to-end features for India's largest e-commerce platform. "
            "Tech stack includes React, Node.js, Java microservices, and MySQL.",
            "Bangalore",
            16.5,
            "2025-07-25",
            "2025-05-07T10:00:00"
        ),
        (
            "Cybersecurity Analyst",
            "Deloitte",
            "Monitor and defend enterprise networks against cyber threats. "
            "Perform vulnerability assessments, penetration testing, and incident response.",
            "Mumbai",
            12.0,
            "2025-08-10",
            "2025-05-08T11:00:00"
        ),
        (
            "Backend Developer",
            "Google",
            "Design and build high-performance backend systems using Go and Python. "
            "Work on distributed systems serving billions of requests daily.",
            "Bangalore",
            25.0,
            "2025-07-30",
            "2025-05-09T09:30:00"
        ),
        (
            "Mobile App Developer",
            "Swiggy",
            "Develop and maintain the Swiggy mobile app using Flutter and Kotlin. "
            "Focus on performance, offline-first architecture, and real-time tracking.",
            "Hyderabad",
            14.0,
            "2025-08-05",
            "2025-05-10T10:00:00"
        ),
        (
            "Business Analyst",
            "Capgemini",
            "Bridge the gap between business stakeholders and engineering teams. "
            "Create requirement docs, user stories, and data-driven recommendations.",
            "Pune",
            8.5,
            "2025-07-10",
            "2025-05-11T09:00:00"
        ),
        (
            "Database Administrator",
            "Oracle",
            "Manage and optimize Oracle and PostgreSQL databases for enterprise clients. "
            "Handle backup strategies, query tuning, and high-availability setups.",
            "Chennai",
            10.0,
            "2025-08-15",
            "2025-05-12T10:30:00"
        ),
        (
            "UI/UX Designer",
            "Adobe",
            "Design intuitive user interfaces for Adobe Creative Cloud products. "
            "Conduct user research, create wireframes, prototypes, and design systems.",
            "Noida",
            15.0,
            "2025-07-28",
            "2025-05-13T09:00:00"
        ),
        (
            "QA Engineer",
            "Microsoft",
            "Ensure quality of Microsoft Azure services through automated testing. "
            "Write test frameworks using Selenium, Playwright, and JUnit. CI/CD integration.",
            "Hyderabad",
            17.0,
            "2025-08-20",
            "2025-05-14T10:00:00"
        ),
        (
            "Systems Engineer",
            "Cognizant",
            "Support and maintain enterprise IT infrastructure and applications. "
            "Handle system monitoring, troubleshooting, and performance optimization.",
            "Chennai",
            6.5,
            "2025-06-25",
            "2025-05-15T11:00:00"
        ),
    ]

    cursor.executemany("""
        INSERT INTO jobs (title, company, description, location, package_lpa, deadline, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, sample_jobs)

    # Only a few sample applications (so you have plenty of jobs to apply to during demo)
    sample_applications = [
        ("Priya Sharma",    "priya@college.edu",  "9876543210", "21CS001", 1, 8.7, None, "2025-05-06T10:00:00"),
        ("Rahul Kumar",     "rahul@college.edu",  "9123456789", "21CS002", 1, 7.9, None, "2025-05-06T11:00:00"),
        ("Sneha Reddy",     "sneha@college.edu",  "8765432109", "21CS003", 2, 8.1, None, "2025-05-07T09:00:00"),
    ]

    cursor.executemany("""
        INSERT INTO applications (student_name, email, phone_number, roll_number, job_id, cgpa, resume_filename, applied_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, sample_applications)

    conn.commit()
    print(f"✓ Inserted {len(sample_jobs)} sample jobs")
    print(f"✓ Inserted {len(sample_applications)} sample applications")


def main():
    print("=" * 50)
    print("  Placement Portal — Database Initializer")
    print("=" * 50)

    # Remove existing database (fresh start)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"✓ Removed old database: {DB_PATH}")

    # Create new database and connect
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    create_tables(conn)
    seed_sample_data(conn)

    conn.close()

    print("=" * 50)
    print(f"✓ Database ready at: {DB_PATH}")
    print("  You can now start the backend servers!")
    print("=" * 50)


if __name__ == "__main__":
    main()
