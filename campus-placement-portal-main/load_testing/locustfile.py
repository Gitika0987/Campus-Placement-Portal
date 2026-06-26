"""
=============================================================
  LOAD TESTING SCRIPT — locustfile.py
=============================================================
  WHAT IS THIS?
  This script simulates hundreds of students using the
  placement portal simultaneously during peak recruitment.

  WHAT IS LOCUST?
  Locust is a Python load testing tool. It spawns virtual
  "users" that make HTTP requests to your server, measuring
  response time, throughput, and error rates.

  HOW TO RUN:

  Option 1 — With Locust Web UI:
    cd placement-portal
    locust -f load_testing/locustfile.py --host=http://localhost:8080
    Then open http://localhost:8089 in your browser.

  Option 2 — Headless (no browser needed):
    locust -f load_testing/locustfile.py \
      --host=http://localhost:8080 \
      --headless \
      --users 100 \
      --spawn-rate 10 \
      --run-time 2m \
      --csv=load_testing/results

  WHAT THE RESULTS MEAN:
    - Response Time: How fast the server replies (ms)
    - RPS (Requests Per Second): Throughput
    - Failure %: Error rate under load
=============================================================
"""

import random
import string
from locust import HttpUser, task, between, tag


class StudentUser(HttpUser):
    """
    CONCEPT: Virtual User
    Each StudentUser simulates one real student browsing the
    placement portal. Locust spawns many of these simultaneously
    to create peak traffic.

    wait_time = between(1, 3)
    → After each action, the student waits 1-3 seconds before
      doing something else (simulates real human behavior).
    """
    wait_time = between(1, 3)

    def on_start(self):
        """
        CONCEPT: Setup per user
        Called once when a virtual user starts.
        We generate a unique student identity for this user.
        """
        self.student_id = ''.join(random.choices(string.digits, k=6))
        self.student_name = f"LoadTest_Student_{self.student_id}"
        self.student_email = f"student{self.student_id}@college.edu"
        self.student_roll = f"21CS{self.student_id}"
        self.student_cgpa = round(random.uniform(6.0, 9.5), 1)
        self.applied_jobs = set()

    # ─────────────────────────────────────────
    # TASK 1: Browse All Jobs (Most common action)
    # ─────────────────────────────────────────
    @tag('browse')
    @task(5)
    def browse_jobs(self):
        """
        CONCEPT: Task Weight
        @task(5) means this action is 5x more likely than @task(1).
        Most students spend time BROWSING rather than applying,
        so we make this the most frequent action.
        """
        with self.client.get("/api/jobs", name="GET /api/jobs",
                             catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "jobs" in data and len(data["jobs"]) > 0:
                    response.success()
                else:
                    response.failure("No jobs returned")
            else:
                response.failure(f"Status {response.status_code}")

    # ─────────────────────────────────────────
    # TASK 2: View a Single Job Detail
    # ─────────────────────────────────────────
    @tag('browse')
    @task(3)
    def view_single_job(self):
        """
        Students click on a specific job to read its full
        description before deciding to apply.
        """
        job_id = random.randint(1, 5)  # We have 5 sample jobs
        with self.client.get(f"/api/jobs/{job_id}",
                             name="GET /api/jobs/[id]",
                             catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.success()  # Job might not exist, that's OK
            else:
                response.failure(f"Status {response.status_code}")

    # ─────────────────────────────────────────
    # TASK 3: Apply for a Job
    # ─────────────────────────────────────────
    @tag('apply')
    @task(2)
    def apply_for_job(self):
        """
        CONCEPT: POST Request Under Load
        This tests the server's ability to handle write operations
        (database inserts) under heavy concurrent traffic.
        SQLite may struggle with many concurrent writes — this is
        a known limitation we can discuss in the report.
        """
        job_id = random.randint(1, 5)

        # Skip if already applied (like a real student would)
        if job_id in self.applied_jobs:
            return

        payload = {
            "student_name": self.student_name,
            "email": self.student_email,
            "roll_number": self.student_roll,
            "job_id": job_id,
            "cgpa": self.student_cgpa
        }

        with self.client.post("/api/apply",
                              json=payload,
                              name="POST /api/apply",
                              catch_response=True) as response:
            if response.status_code == 201:
                self.applied_jobs.add(job_id)
                response.success()
            elif response.status_code == 409:
                # Already applied — not an error
                self.applied_jobs.add(job_id)
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

    # ─────────────────────────────────────────
    # TASK 4: Check System Health
    # ─────────────────────────────────────────
    @tag('health')
    @task(1)
    def check_health(self):
        """
        CONCEPT: Health Check
        Simulates monitoring systems that periodically
        verify the server is alive.
        """
        self.client.get("/health", name="GET /health")

    # ─────────────────────────────────────────
    # TASK 5: Fetch Dashboard Stats
    # ─────────────────────────────────────────
    @tag('stats')
    @task(1)
    def fetch_stats(self):
        """
        Simulates the admin dashboard refreshing its statistics.
        """
        self.client.get("/api/stats", name="GET /api/stats")


class AdminUser(HttpUser):
    """
    CONCEPT: Multiple User Types
    Real systems have different types of users with different
    behaviors. AdminUsers are less frequent but perform
    heavier operations like viewing all applications.

    We set a higher wait_time because admins don't click
    as rapidly as students.
    """
    wait_time = between(3, 6)
    weight = 1  # 1 admin for every 10 students (see StudentUser default weight=10)

    # ─────────────────────────────────────────
    # TASK: View All Applications
    # ─────────────────────────────────────────
    @tag('admin')
    @task(3)
    def view_applications(self):
        """
        Admin reviews all student applications.
        This is a JOIN query — heavier on the database.
        """
        with self.client.get("/api/admin/applications",
                             name="GET /api/admin/applications",
                             catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")

    # ─────────────────────────────────────────
    # TASK: View Stats
    # ─────────────────────────────────────────
    @tag('admin')
    @task(2)
    def view_stats(self):
        """Admin checking dashboard stats."""
        self.client.get("/api/stats", name="GET /api/stats")

    # ─────────────────────────────────────────
    # TASK: Post a New Job
    # ─────────────────────────────────────────
    @tag('admin')
    @task(1)
    def post_new_job(self):
        """
        Admin posting a new job listing.
        Less frequent but tests write performance.
        """
        job_id = random.randint(1000, 9999)
        payload = {
            "title": f"LoadTest Engineer #{job_id}",
            "company": random.choice(["Infosys", "TCS", "Wipro", "HCL", "Accenture"]),
            "description": "This is a load test job posting to evaluate system performance.",
            "location": random.choice(["Bangalore", "Hyderabad", "Chennai", "Pune", "Mumbai"]),
            "package_lpa": round(random.uniform(6.0, 20.0), 1),
            "deadline": "2025-12-31"
        }

        with self.client.post("/api/admin/jobs",
                              json=payload,
                              name="POST /api/admin/jobs",
                              catch_response=True) as response:
            if response.status_code == 201:
                response.success()
            else:
                response.failure(f"Status {response.status_code}")
