# System Architecture

## Campus Placement Portal — Load-Balanced Multi-Instance Architecture

**Team Members:**
- Deeksha – 1602-23-737-139
- Gitika – 1602-23-737-141
- Shiny – 1602-23-737-169

---

## 1. High-Level Architecture

```
                    ┌───────────────────────────────────────────────┐
                    │              CLIENTS (Browsers)               │
                    │                                               │
                    │   Student Portal        Admin Dashboard       │
                    │   (index.html)          (admin.html)          │
                    └───────────────┬───────────────────────────────┘
                                    │
                                    │  HTTP Requests
                                    │  (port 8080)
                                    ▼
                    ┌───────────────────────────────────────────────┐
                    │          NGINX LOAD BALANCER                  │
                    │          (Reverse Proxy)                      │
                    │                                               │
                    │   Algorithm: Round Robin                      │
                    │   Health Checks: max_fails=3, timeout=30s    │
                    │   Keepalive Connections: 32                   │
                    └──────┬──────────────┬──────────────┬──────────┘
                           │              │              │
                           ▼              ▼              ▼
                    ┌────────────┐ ┌────────────┐ ┌────────────┐
                    │  Flask     │ │  Flask     │ │  Flask     │
                    │  Server 1  │ │  Server 2  │ │  Server 3  │
                    │  :5001     │ │  :5002     │ │  :5003     │
                    │            │ │            │ │            │
                    │ REST API   │ │ REST API   │ │ REST API   │
                    │ 7 Endpoints│ │ 7 Endpoints│ │ 7 Endpoints│
                    └──────┬─────┘ └──────┬─────┘ └──────┬─────┘
                           │              │              │
                           ▼              ▼              ▼
                    ┌───────────────────────────────────────────────┐
                    │              SQLite DATABASE                   │
                    │              (placement.db)                    │
                    │                                               │
                    │   Tables: jobs, applications                  │
                    │   Shared by all 3 server instances            │
                    └───────────────────────────────────────────────┘
```

---

## 2. Component Details

### 2.1 Frontend (Client Layer)

| Component | File | Purpose |
|-----------|------|---------|
| Student Portal | `frontend/index.html` | Browse jobs, search/filter, submit applications |
| Admin Dashboard | `frontend/admin.html` | Post new jobs, view all applications, monitor servers |

- **Technology**: Pure HTML + CSS + JavaScript (no framework)
- **API Communication**: `fetch()` calls to `http://localhost:8080` (Nginx)
- **Dark Theme**: Modern UI with CSS variables for easy theming
- **Real-time Updates**: Auto-refresh every 8-10 seconds to show load balancing

### 2.2 Nginx Load Balancer (Distribution Layer)

| Setting | Value | Purpose |
|---------|-------|---------|
| Listen Port | 8080 | Single entry point for all client requests |
| Algorithm | Round Robin | Distributes requests equally across servers |
| max_fails | 3 | Marks server as down after 3 consecutive failures |
| fail_timeout | 30s | Time before retrying a failed server |
| keepalive | 32 | Persistent connections to reduce TCP overhead |
| Gzip | Enabled | Compresses JSON responses for faster transfer |

**Configuration File:** `nginx/nginx.conf`

### 2.3 Flask Backend (Application Layer)

Each Flask instance is an identical copy of `backend/app.py` running on a different port.

| Endpoint | Method | Description | Used By |
|----------|--------|-------------|---------|
| `/health` | GET | Health check (Nginx monitors this) | Nginx, Admin |
| `/api/jobs` | GET | List all job postings | Student Portal |
| `/api/jobs/<id>` | GET | Single job detail | Student Portal |
| `/api/apply` | POST | Submit student application | Student Portal |
| `/api/admin/jobs` | POST | Create new job posting | Admin Dashboard |
| `/api/admin/applications` | GET | View all applications (JOIN query) | Admin Dashboard |
| `/api/stats` | GET | Database statistics | Both Portals |

### 2.4 SQLite Database (Storage Layer)

**File:** `backend/placement.db`

```
┌──────────────────────────┐       ┌──────────────────────────────┐
│         jobs              │       │       applications            │
├──────────────────────────┤       ├──────────────────────────────┤
│ id          INTEGER PK   │◄──────│ id             INTEGER PK    │
│ title       TEXT          │       │ student_name   TEXT           │
│ company     TEXT          │       │ email          TEXT           │
│ description TEXT          │       │ roll_number    TEXT           │
│ location    TEXT          │       │ job_id         INTEGER FK ───┤
│ package_lpa REAL          │       │ cgpa           REAL           │
│ deadline    TEXT          │       │ applied_at     TEXT           │
│ created_at  TEXT          │       └──────────────────────────────┘
└──────────────────────────┘
         ONE                              MANY
              (One job → Many applications)
```

---

## 3. Distributed Systems Concepts Demonstrated

### 3.1 Load Balancing

**What:** Distributing incoming requests across multiple servers so no single server is overloaded.

**How:** Nginx uses the **Round Robin** algorithm — each new request goes to the next server in sequence:
```
Request 1 → Server :5001
Request 2 → Server :5002
Request 3 → Server :5003
Request 4 → Server :5001  (cycles back)
...
```

**Why:** Without load balancing, a single server handling 500+ concurrent students during placement season would become extremely slow or crash entirely.

### 3.2 High Availability

**What:** The system remains accessible even if individual components fail.

**How:** With 3 backend instances, if one server crashes:
- Nginx detects the failure via health checks (`max_fails=3`)
- Traffic is automatically redirected to the remaining 2 healthy servers
- Students experience no downtime — they may not even notice

**Demonstration:**
```bash
# 1. Start all 3 servers
./start.sh

# 2. Kill one server
kill <PID of server 5002>

# 3. Portal still works — Nginx routes to :5001 and :5003 only
```

### 3.3 Fault Tolerance

**What:** The system handles failures gracefully without data loss or service interruption.

**How:**
- Health check endpoint (`/health`) returns status of each server
- Nginx `max_fails=3` and `fail_timeout=30s` configuration
- After 30 seconds, Nginx retries the failed server (in case it recovers)
- Shared database means no data is lost when a server goes down

### 3.4 Scalability

**What:** The ability to handle more users by adding more resources.

**How (Horizontal Scaling):**
```nginx
# To add a 4th server, simply add to nginx.conf:
upstream placement_backends {
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
    server 127.0.0.1:5003;
    server 127.0.0.1:5004;  ← new server
}
```
Then start another Flask instance: `python app.py 5004`

---

## 4. Request Flow Walkthrough

### Example: Student applies for a job

```
1. Student fills form and clicks "Apply" in index.html

2. Browser sends POST request:
   POST http://localhost:8080/api/apply
   Body: { student_name, email, roll_number, job_id, cgpa }

3. Nginx (port 8080) receives the request
   → Checks upstream server list
   → Selects next server via Round Robin (e.g., :5002)
   → Forwards request to http://127.0.0.1:5002/api/apply

4. Flask Server :5002 processes the request:
   → Parses JSON body
   → Validates all required fields
   → Checks if job exists in database
   → Checks for duplicate application
   → Inserts new row into 'applications' table
   → Returns 201 Created with application ID

5. Nginx forwards the response back to the browser

6. Browser shows success toast:
   "Application submitted! (served by :5002)"
```

---

## 5. Load Testing Architecture

```
┌───────────────────────────────────────┐
│          LOCUST LOAD TESTER           │
│                                       │
│   Simulates 50-500 virtual users      │
│   Mix: 90% Students + 10% Admins     │
│                                       │
│   Actions:                            │
│   - Browse jobs (most frequent)       │
│   - View job detail                   │
│   - Submit application                │
│   - Check health                      │
│   - Admin: view all, post jobs        │
│                                       │
│   Metrics Collected:                  │
│   - Response time (avg, p50, p95)     │
│   - Requests per second (throughput)  │
│   - Failure rate                      │
│   - Response time distribution        │
└──────────────────┬────────────────────┘
                   │
                   │ HTTP Traffic
                   ▼
            ┌──────────────┐
            │    Nginx     │
            │   (:8080)    │
            └──────────────┘
```

**Tool:** Locust (Python-based load testing framework)
**Script:** `load_testing/locustfile.py`

---

## 6. Technology Stack Summary

| Layer | Technology | Why Chosen |
|-------|-----------|------------|
| Frontend | HTML/CSS/JS | Simple, no build tools needed |
| Frontend Hosting | Amazon S3 | Serverless static site hosting |
| Backend | Flask (Python) | Lightweight, easy to run multiple instances |
| Containerization | Docker | Portable, consistent deployment across EC2 instances |
| Load Balancer | Nginx on EC2 | Industry standard, built-in upstream support |
| Compute | Amazon EC2 (t2.micro) | Free tier, scalable virtual machines |
| Database | SQLite | File-based, no server setup, embedded in container |
| Load Testing | Locust | Python-based, web UI, realistic user simulation |
| Scripting | Bash | Automates server startup and health checks |

---

## 7. AWS Cloud Architecture

The project is deployed on AWS to demonstrate cloud computing concepts:

```
                    ┌────────────────────────────────────────────────┐
                    │                 INTERNET                       │
                    └───────────────────┬────────────────────────────┘
                                        │
               ┌────────────────────────┼───────────────────────────┐
               │                  AWS CLOUD                         │
               │                                                    │
               │    ┌───────────────────▼──────────────────────┐    │
               │    │         AMAZON S3 (Static Website)        │    │
               │    │   index.html / admin.html                 │    │
               │    └───────────────────┬──────────────────────┘    │
               │                        │ API calls                 │
               │    ┌───────────────────▼──────────────────────┐    │
               │    │        EC2 — NGINX LOAD BALANCER          │    │
               │    │        (t2.micro, port 8080)              │    │
               │    └──────┬────────────┬────────────┬─────────┘    │
               │           │            │            │              │
               │    ┌──────▼─────┐┌─────▼──────┐┌───▼────────┐     │
               │    │ EC2 #1     ││ EC2 #2     ││ EC2 #3     │     │
               │    │ t2.micro   ││ t2.micro   ││ t2.micro   │     │
               │    │ ┌────────┐ ││ ┌────────┐ ││ ┌────────┐ │     │
               │    │ │ Docker │ ││ │ Docker │ ││ │ Docker │ │     │
               │    │ │ Flask  │ ││ │ Flask  │ ││ │ Flask  │ │     │
               │    │ │ :5000  │ ││ │ :5000  │ ││ │ :5000  │ │     │
               │    │ └────────┘ ││ └────────┘ ││ └────────┘ │     │
               │    └────────────┘└────────────┘└────────────┘     │
               │                                                    │
               │    Security Group: placement-portal-sg             │
               │    Ports: 22 (SSH), 5000 (Flask), 8080 (Nginx)    │
               └────────────────────────────────────────────────────┘
```

### AWS Services Used

| Service | Purpose | Lab Mapping |
|---------|---------|-------------|
| **EC2** (×4 instances) | Run Flask backends + Nginx LB | Lab 7i |
| **S3** (static website) | Host frontend HTML files | Lab 7ii |
| **Docker** (on EC2) | Containerize Flask application | Lab 8 |
| **VPC + Security Groups** | Network isolation & firewall rules | — |

### Deployment Flow

```
Developer Laptop                        AWS Cloud
─────────────────                       ──────────────────────
1. docker build                    →    (build image on each EC2)
2. deploy_frontend.sh              →    S3 bucket (static site)
3. ec2_setup.sh (×3 instances)     →    Docker containers running
4. nginx_aws.conf                  →    Load balancer distributing
5. locustfile.py                   →    Load test against cloud
```

For full deployment instructions, see [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md).

