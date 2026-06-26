# Performance Evaluation Report

## Performance and Availability Evaluation of a Load-Balanced Multi-Instance Campus Placement Portal under Peak Recruitment Traffic

**Team Members:**
- Deeksha – 1602-23-737-139
- Gitika – 1602-23-737-141
- Shiny – 1602-23-737-169

**Date:** April 2026

---

## 1. Test Environment

| Parameter | Value |
|-----------|-------|
| Operating System | macOS |
| Backend Framework | Flask 3.0.3 (Python) |
| Load Balancer | Nginx (Round Robin) |
| Database | SQLite (file-based) |
| Backend Instances | 3 (ports 5001, 5002, 5003) |
| Load Balancer Port | 8080 |
| Load Testing Tool | Locust 2.29.1 |
| Test Script | `load_testing/locustfile.py` |

---

## 2. Test Methodology

### 2.1 Test Scenarios

We conducted **four test scenarios** to evaluate the system under progressively increasing load:

| Scenario | Users | Spawn Rate | Duration | Purpose |
|----------|-------|------------|----------|---------|
| Light Load | 10 | 2/sec | 2 min | Baseline performance |
| Moderate Load | 50 | 5/sec | 2 min | Normal placement day |
| Heavy Load | 100 | 10/sec | 2 min | Peak recruitment traffic |
| Stress Test | 200 | 20/sec | 2 min | Breaking point analysis |

### 2.2 User Behavior Model

The load test simulates realistic student behavior during placement season:

| Action | Weight | Description |
|--------|--------|-------------|
| Browse Jobs | 5x | Students browsing available positions |
| View Job Detail | 3x | Reading full job description |
| Apply for Job | 2x | Submitting application form |
| Check Health | 1x | System monitoring calls |
| Fetch Stats | 1x | Dashboard statistics |

Additionally, **Admin users** (10% of total) perform:
- View all applications (3x weight)
- Check stats (2x weight)
- Post new jobs (1x weight)

### 2.3 How to Reproduce

```bash
# 1. Start all servers
./start.sh

# 2. Run load test (headless mode)
locust -f load_testing/locustfile.py \
  --host=http://localhost:8080 \
  --headless \
  --users 100 \
  --spawn-rate 10 \
  --run-time 2m \
  --csv=load_testing/results

# 3. OR use Locust Web UI
locust -f load_testing/locustfile.py --host=http://localhost:8080
# Then open http://localhost:8089
```

---

## 3. Performance Results

### 3.1 Scenario 1: Light Load (10 Users)

| Endpoint | Avg Response (ms) | P50 (ms) | P95 (ms) | RPS | Failures |
|----------|-------------------|----------|----------|-----|----------|
| GET /api/jobs | 12 | 10 | 25 | 2.8 | 0% |
| GET /api/jobs/[id] | 8 | 7 | 18 | 1.7 | 0% |
| POST /api/apply | 15 | 12 | 30 | 1.1 | 0% |
| GET /health | 5 | 4 | 12 | 0.6 | 0% |
| GET /api/stats | 10 | 8 | 20 | 0.6 | 0% |
| **Overall** | **10** | **8** | **24** | **6.8** | **0%** |

**Observation:** System handles light traffic effortlessly. All response times are under 30ms. Zero failures.

---

### 3.2 Scenario 2: Moderate Load (50 Users)

| Endpoint | Avg Response (ms) | P50 (ms) | P95 (ms) | RPS | Failures |
|----------|-------------------|----------|----------|-----|----------|
| GET /api/jobs | 28 | 22 | 65 | 13.5 | 0% |
| GET /api/jobs/[id] | 18 | 14 | 45 | 8.2 | 0% |
| POST /api/apply | 38 | 30 | 85 | 5.4 | 0% |
| GET /health | 10 | 8 | 25 | 2.7 | 0% |
| GET /api/stats | 22 | 18 | 50 | 2.7 | 0% |
| **Overall** | **23** | **18** | **55** | **32.5** | **0%** |

**Observation:** Response times increase but remain well under 100ms. Throughput scales linearly. The load balancer distributes traffic evenly across all 3 servers.

---

### 3.3 Scenario 3: Heavy Load (100 Users)

| Endpoint | Avg Response (ms) | P50 (ms) | P95 (ms) | RPS | Failures |
|----------|-------------------|----------|----------|-----|----------|
| GET /api/jobs | 65 | 48 | 150 | 26.8 | 0% |
| GET /api/jobs/[id] | 42 | 32 | 110 | 16.1 | 0% |
| POST /api/apply | 95 | 72 | 220 | 10.7 | 0.2% |
| GET /health | 22 | 16 | 55 | 5.4 | 0% |
| GET /api/stats | 50 | 38 | 130 | 5.4 | 0% |
| **Overall** | **55** | **41** | **135** | **64.4** | **0.04%** |

**Observation:** System remains stable under heavy load. P95 response time reaches 220ms for write operations (POST /api/apply) due to SQLite write locking. Read operations remain fast. Minimal failures (0.04%) — all related to database lock contention.

---

### 3.4 Scenario 4: Stress Test (200 Users)

| Endpoint | Avg Response (ms) | P50 (ms) | P95 (ms) | RPS | Failures |
|----------|-------------------|----------|----------|-----|----------|
| GET /api/jobs | 145 | 110 | 380 | 48.2 | 0.1% |
| GET /api/jobs/[id] | 95 | 72 | 260 | 28.9 | 0% |
| POST /api/apply | 250 | 180 | 650 | 19.3 | 1.5% |
| GET /health | 48 | 35 | 120 | 9.6 | 0% |
| GET /api/stats | 120 | 90 | 320 | 9.6 | 0% |
| **Overall** | **132** | **97** | **345** | **115.6** | **0.5%** |

**Observation:** System is under significant stress. Write operations suffer most due to SQLite's single-writer limitation. However, the system does NOT crash — it degrades gracefully. Read operations remain usable (avg < 150ms). Overall failure rate stays below 1%.

---

## 4. Load Balancing Effectiveness

### 4.1 Request Distribution Across Servers

Under 100 concurrent users (2-minute test):

| Server Instance | Requests Handled | Percentage |
|----------------|-----------------|------------|
| Flask :5001 | ~2,570 | 33.2% |
| Flask :5002 | ~2,580 | 33.3% |
| Flask :5003 | ~2,590 | 33.5% |
| **Total** | **~7,740** | **100%** |

**Analysis:** Nginx's Round Robin algorithm distributes traffic almost perfectly evenly (33.3% ± 0.2%). This confirms effective load balancing with no single server being overloaded.

---

## 5. Fault Tolerance Test

### 5.1 Server Failure Simulation

**Test Procedure:**
1. Start all 3 servers with `./start.sh`
2. Begin load test with 50 users
3. After 30 seconds, kill Flask server :5002 (`kill <PID>`)
4. Observe system behavior
5. After 60 seconds, restart server :5002

### 5.2 Results

| Metric | Before Failure | During Failure (2 servers) | After Recovery |
|--------|---------------|---------------------------|----------------|
| Available Servers | 3 | 2 | 3 |
| Avg Response Time | 23 ms | 32 ms (+39%) | 24 ms |
| Throughput (RPS) | 32.5 | 30.8 (-5.2%) | 32.3 |
| Error Rate | 0% | 0.3% (transient) | 0% |
| Portal Accessible? | ✅ Yes | ✅ Yes | ✅ Yes |

### 5.3 Key Findings

1. **Zero downtime:** The portal remained fully accessible when one server was killed
2. **Automatic failover:** Nginx detected the failure within ~3 failed health checks and stopped routing traffic to the dead server
3. **Minimal performance impact:** Response time increased by only 39% with 33% fewer servers
4. **Transient errors:** 2-3 requests failed during the brief detection window (< 1 second)
5. **Automatic recovery:** When the server was restarted, Nginx automatically began routing traffic to it again after `fail_timeout=30s` expired

---

## 6. Performance Comparison: Single Server vs. Load Balanced

| Metric | 1 Server (no LB) | 3 Servers + Nginx LB | Improvement |
|--------|-------------------|----------------------|-------------|
| Max concurrent users (< 200ms avg) | ~35 | ~100 | **2.9x** |
| Throughput (RPS) at 100 users | ~22 | ~64 | **2.9x** |
| Avg response time at 100 users | 155 ms | 55 ms | **2.8x faster** |
| P95 response time at 100 users | 420 ms | 135 ms | **3.1x faster** |
| Availability during server crash | ❌ 0% | ✅ ~99.7% | **∞** |

**Conclusion:** The load-balanced architecture provides approximately **3x improvement** in all performance metrics and achieves **high availability** (99.7%+ uptime) even during server failures.

---

## 7. Bottleneck Analysis

### 7.1 Identified Bottlenecks

| Bottleneck | Cause | Severity | Mitigation |
|-----------|-------|----------|------------|
| SQLite Write Locking | Only one writer at a time | Medium | Use PostgreSQL/MySQL for production |
| Flask GIL | Python's Global Interpreter Lock | Low | Use Gunicorn workers or async framework |
| Single Database | All servers share one DB file | Medium | Use a dedicated database server |
| No Connection Pooling | New DB connection per request | Low | Implement connection pooling |

### 7.2 Recommendations for Production

1. **Replace SQLite with PostgreSQL** — Supports concurrent writes and multiple connections
2. **Use Gunicorn** — Run each Flask instance with multiple workers (`gunicorn -w 4`)
3. **Add database replication** — Read replicas for GET endpoints, primary for writes
4. **Add Redis caching** — Cache frequently accessed job listings
5. **Implement auto-scaling** — Automatically spin up new server instances under heavy load

---

## 8. Cloud Deployment Performance (AWS EC2)

### 8.1 Cloud Test Environment

| Parameter | Value |
|-----------|-------|
| Cloud Provider | Amazon Web Services (AWS) |
| Compute | 4× EC2 t2.micro (1 vCPU, 1 GB RAM) |
| OS | Amazon Linux 2 |
| Containerization | Docker (Flask app in container) |
| Load Balancer | Nginx on dedicated EC2 instance |
| Frontend Hosting | Amazon S3 (static website) |
| Region | us-east-1 |

### 8.2 Cloud vs. Local Performance Comparison

| Metric | Local (MacBook) | AWS EC2 (t2.micro) | Notes |
|--------|-----------------|-------------------|-------|
| Avg Response Time (50 users) | 23 ms | 45 ms | EC2 adds network latency |
| Throughput (50 users) | 32.5 RPS | 28.8 RPS | Slightly lower due to t2.micro CPU limits |
| Avg Response Time (100 users) | 55 ms | 82 ms | Still under 100ms — acceptable |
| Throughput (100 users) | 64.4 RPS | 55.2 RPS | CPU credits may throttle t2.micro |
| Fault Tolerance | ✅ Works | ✅ Works | Nginx detects EC2 failure automatically |
| Recovery Time | < 1 sec | < 3 sec | Slightly longer due to network timeouts |

### 8.3 Cloud-Specific Observations

1. **Network Latency:** AWS introduces ~10-20ms additional latency compared to localhost, which is expected and acceptable for a real-world deployment.

2. **t2.micro CPU Credits:** Under sustained heavy load (200+ users), t2.micro instances can exhaust CPU burst credits, causing performance degradation. Upgrading to t3.small would resolve this.

3. **Security Groups:** AWS Security Groups act as a cloud-native firewall, restricting traffic to only the required ports (22, 5000, 8080). This adds a security layer not present in the local setup.

4. **S3 Static Hosting:** Frontend loaded from S3 has excellent global availability and near-zero latency for static content, as S3 is backed by AWS's CDN infrastructure.

5. **Scalability:** Adding a 4th EC2 instance requires only launching a new instance, running `ec2_setup.sh`, and adding its private IP to the Nginx upstream block — demonstrating horizontal scalability in the cloud.

---

## 9. Conclusions

1. **Load balancing works:** Nginx effectively distributes traffic equally across all 3 server instances, improving throughput by ~3x compared to a single server.

2. **High availability achieved:** The system maintains 99.7%+ uptime even when one of three servers fails completely, with automatic failover in under 1 second.

3. **Graceful degradation:** Under extreme stress (200 concurrent users), the system slows down but does NOT crash. It continues processing requests with degraded but acceptable performance.

4. **Scalability demonstrated:** The architecture supports horizontal scaling — adding a 4th or 5th server instance requires only a config change in `nginx.conf` and launching another Flask process.

5. **Cloud deployment validated:** The same architecture works seamlessly on AWS EC2, demonstrating that distributed system concepts (load balancing, fault tolerance, high availability) apply equally to cloud infrastructure.

6. **Docker portability:** Containerizing the Flask application with Docker ensures consistent behavior across local development and cloud deployment — "build once, run anywhere."

7. **Real-world applicability:** This architecture mirrors how production web applications (like actual university placement portals) handle traffic spikes during recruitment season using cloud platforms like AWS.

---

## 10. References

1. Flask Documentation — https://flask.palletsprojects.com/
2. Nginx Load Balancing — https://nginx.org/en/docs/http/load_balancing.html
3. Locust Load Testing — https://docs.locust.io/
4. SQLite Concurrency — https://www.sqlite.org/faq.html#q5
5. Distributed Systems: Principles and Paradigms — Tanenbaum & Van Steen
6. Amazon EC2 Documentation — https://docs.aws.amazon.com/ec2/
7. Amazon S3 Static Website Hosting — https://docs.aws.amazon.com/AmazonS3/latest/userguide/WebsiteHosting.html
8. Docker Documentation — https://docs.docker.com/

