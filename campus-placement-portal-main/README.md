# Campus Placement Portal
### Performance & Availability Evaluation under Peak Traffic

**DSCC Project — Distributed Systems & Cloud Computing**

**Team Members:**
- Shiny –
- Gitika – 
- Deeksha – 



---

## Project Overview

A load-balanced multi-instance campus placement portal deployed on **AWS Cloud** using **Docker**, **EC2**, **S3**, and **Nginx**. The system is tested under simulated peak recruitment traffic to evaluate performance, availability, and fault tolerance.

### Distributed Systems Concepts

| Concept | Implementation |
|---------|---------------|
| Load Balancing | Nginx Round Robin across 3 backend instances |
| High Availability | Kill one server → others take over automatically |
| Fault Tolerance | Health checks + automatic failover |
| Scalability | Add more EC2 instances to scale horizontally |
| Containerization | Docker containers on EC2 |
| Cloud Computing | AWS EC2, S3, Security Groups |

---

## Quick Start (Local)

```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Install Nginx
brew install nginx        # Mac
sudo apt install nginx    # Ubuntu

# 3. Init database
cd backend && python3 init_db.py && cd ..

# 4. Start everything
chmod +x start.sh
./start.sh
```

Then open `frontend/index.html` in your browser.

---

## AWS Cloud Deployment

See [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md) for full step-by-step instructions.

```bash
# Summary:
# 1. Launch 4 EC2 instances (3 Flask + 1 Nginx)
# 2. Run ec2_setup.sh on each Flask EC2 (installs Docker, starts container)
# 3. Configure Nginx on the LB EC2 (nginx_aws.conf)
# 4. Deploy frontend to S3 (deploy_frontend.sh)
# 5. Run load tests against cloud endpoint
```

---

## Load Testing

```bash
# With Web UI (recommended for demo):
locust -f load_testing/locustfile.py --host=http://localhost:8080
# Open http://localhost:8089

# Against AWS:
locust -f load_testing/locustfile.py --host=http://<NGINX-EC2-IP>:8080

# Headless mode:
locust -f load_testing/locustfile.py \
  --host=http://localhost:8080 \
  --headless --users 100 --spawn-rate 10 --run-time 2m
```

---

## Project Structure

```
placement-portal/
├── start.sh                      ← Start locally (all servers + Nginx)
├── Dockerfile                    ← Containerize Flask for EC2
├── ec2_setup.sh                  ← Setup script for each EC2 instance
├── deploy_frontend.sh            ← Upload frontend to S3
│
├── backend/
│   ├── app.py                    ← Flask REST API (7 endpoints)
│   ├── init_db.py                ← Database initializer + seed data
│   ├── placement.db              ← SQLite database
│   └── requirements.txt          ← Python dependencies
│
├── frontend/
│   ├── index.html                ← Student portal (dark theme)
│   └── admin.html                ← Admin dashboard
│
├── nginx/
│   ├── nginx.conf                ← Local load balancer config
│   └── nginx_aws.conf            ← AWS load balancer config
│
├── load_testing/
│   └── locustfile.py             ← Locust load test (students + admins)
│
├── ARCHITECTURE.md               ← System architecture + diagrams
├── AWS_DEPLOYMENT.md             ← Step-by-step AWS deployment guide
├── PERFORMANCE_REPORT.md         ← Performance evaluation report
└── README.md                     ← This file
```

---

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/health` | Server health check |
| GET | `/api/jobs` | List all job postings |
| GET | `/api/jobs/<id>` | Single job detail |
| POST | `/api/apply` | Student submits application |
| GET | `/api/admin/applications` | All applications (admin) |
| POST | `/api/admin/jobs` | Post new job (admin) |
| GET | `/api/stats` | Database statistics |

---

## Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, components, AWS cloud diagram |
| [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md) | Step-by-step EC2 + Docker + S3 deployment |
| [PERFORMANCE_REPORT.md](PERFORMANCE_REPORT.md) | Load test results, fault tolerance, analysis |
