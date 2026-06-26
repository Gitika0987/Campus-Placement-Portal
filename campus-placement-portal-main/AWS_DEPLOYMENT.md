# AWS Cloud Deployment Guide

## Campus Placement Portal — Deploying on Amazon Web Services

**Team Members:**
- Deeksha – 1602-23-737-139
- Gitika – 1602-23-737-141
- Shiny – 1602-23-737-169

---

## Cloud Architecture

```
                    ┌────────────────────────────────────────────────┐
                    │                 INTERNET                       │
                    │                                                │
                    │   Students access the portal via S3 URL        │
                    └───────────────────┬────────────────────────────┘
                                        │
                    ┌───────────────────▼────────────────────────────┐
                    │          AMAZON S3 (Static Website)             │
                    │                                                │
                    │   index.html  →  Student Portal                │
                    │   admin.html  →  Admin Dashboard               │
                    │                                                │
                    │   URL: http://<bucket>.s3-website-<region>.    │
                    │        amazonaws.com                           │
                    └───────────────────┬────────────────────────────┘
                                        │
                                        │  API calls (fetch)
                                        │  http://<nginx-ec2>:8080
                                        ▼
          ┌─────────────────────────────────────────────────────────┐
          │              EC2 INSTANCE — NGINX LOAD BALANCER          │
          │              (t2.micro, Amazon Linux 2)                   │
          │                                                         │
          │   Security Group: allow 8080 from anywhere               │
          │   Nginx Round Robin → distributes to 3 backends          │
          └────────┬──────────────────┬──────────────────┬──────────┘
                   │                  │                  │
                   ▼                  ▼                  ▼
          ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
          │   EC2 #1     │  │   EC2 #2     │  │   EC2 #3     │
          │  (t2.micro)  │  │  (t2.micro)  │  │  (t2.micro)  │
          │              │  │              │  │              │
          │  ┌────────┐  │  │  ┌────────┐  │  │  ┌────────┐  │
          │  │ Docker │  │  │  │ Docker │  │  │  │ Docker │  │
          │  │ Flask  │  │  │  │ Flask  │  │  │  │ Flask  │  │
          │  │ :5000  │  │  │  │ :5000  │  │  │  │ :5000  │  │
          │  │ SQLite │  │  │  │ SQLite │  │  │  │ SQLite │  │
          │  └────────┘  │  │  └────────┘  │  │  └────────┘  │
          │              │  │              │  │              │
          │  SG: 5000    │  │  SG: 5000    │  │  SG: 5000    │
          └──────────────┘  └──────────────┘  └──────────────┘
```

---

## Prerequisites

- AWS Academy Sandbox or AWS account with free tier
- AWS CLI installed on your laptop
- SSH key pair (`.pem` file) for EC2 access
- Basic terminal/SSH knowledge

---

## Step 0: Configure AWS CLI

If not already done, configure your AWS credentials:

```bash
aws configure
```

Enter:
- **Access Key ID**: (from your AWS Academy credentials)
- **Secret Access Key**: (from your AWS Academy credentials)
- **Region**: `us-east-1` (or your preferred region)
- **Output format**: `json`

Verify:
```bash
aws sts get-caller-identity
```

---

## Step 1: Create a Security Group

We need a security group that allows:
- SSH (port 22) — for us to connect
- HTTP (port 5000) — Flask backend
- HTTP (port 8080) — Nginx load balancer

```bash
# Create security group
aws ec2 create-security-group \
    --group-name placement-portal-sg \
    --description "Security group for Placement Portal"

# Note the GroupId returned (e.g., sg-0abc1234def56789)
# Save it — you'll use it in the next steps

# Allow SSH (port 22) from anywhere
aws ec2 authorize-security-group-ingress \
    --group-name placement-portal-sg \
    --protocol tcp --port 22 --cidr 0.0.0.0/0

# Allow Flask (port 5000) from anywhere
aws ec2 authorize-security-group-ingress \
    --group-name placement-portal-sg \
    --protocol tcp --port 5000 --cidr 0.0.0.0/0

# Allow Nginx (port 8080) from anywhere
aws ec2 authorize-security-group-ingress \
    --group-name placement-portal-sg \
    --protocol tcp --port 8080 --cidr 0.0.0.0/0

# Allow all internal traffic within the security group
# (so Nginx can talk to Flask instances via private IPs)
aws ec2 authorize-security-group-ingress \
    --group-name placement-portal-sg \
    --protocol -1 --source-group placement-portal-sg
```

---

## Step 2: Create a Key Pair

```bash
# Create key pair and save the .pem file
aws ec2 create-key-pair \
    --key-name placement-key \
    --query 'KeyMaterial' \
    --output text > placement-key.pem

# Set correct permissions (required by SSH)
chmod 400 placement-key.pem
```

> **Note:** If you already have a key pair from your lab, you can use that instead.

---

## Step 3: Launch 4 EC2 Instances

We need **4 instances**: 3 for Flask backends + 1 for Nginx.

### Option A: Launch via AWS CLI

```bash
# Launch 4 t2.micro instances with Amazon Linux 2
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --instance-type t2.micro \
    --count 4 \
    --key-name placement-key \
    --security-groups placement-portal-sg \
    --tag-specifications \
        'ResourceType=instance,Tags=[{Key=Name,Value=placement-portal}]'
```

> **Note:** The AMI ID `ami-0c02fb55956c7d316` is Amazon Linux 2 in `us-east-1`.
> For other regions, find the correct AMI ID in the AWS Console.

### Option B: Launch via AWS Console (Easier)

1. Go to **EC2 Dashboard** → **Launch Instance**
2. **Name**: `placement-flask-1` (repeat for 2, 3, and `placement-nginx`)
3. **AMI**: Amazon Linux 2 (free tier eligible)
4. **Instance type**: `t2.micro` (free tier)
5. **Key pair**: Select `placement-key` (or your existing key)
6. **Security group**: Select `placement-portal-sg`
7. Click **Launch Instance**
8. Repeat for all 4 instances

### After launching, note down the IPs:

```bash
# List your instances and their IPs
aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=placement-portal" \
    --query 'Reservations[*].Instances[*].[Tags[?Key==`Name`].Value|[0],PublicIpAddress,PrivateIpAddress,State.Name]' \
    --output table
```

Write these down:
```
┌─────────────────┬────────────────┬────────────────┐
│ Instance        │ Public IP      │ Private IP     │
├─────────────────┼────────────────┼────────────────┤
│ Flask EC2 #1    │ ___.___.___._  │ ___.___.___._  │
│ Flask EC2 #2    │ ___.___.___._  │ ___.___.___._  │
│ Flask EC2 #3    │ ___.___.___._  │ ___.___.___._  │
│ Nginx EC2       │ ___.___.___._  │ ___.___.___._  │
└─────────────────┴────────────────┴────────────────┘
```

---

## Step 4: Set Up Flask Backend EC2 Instances (×3)

Repeat this for **each of the 3 Flask EC2 instances**.

### 4.1: SSH into the instance

```bash
ssh -i placement-key.pem ec2-user@<FLASK-EC2-PUBLIC-IP>
```

### 4.2: Install Git and clone project

```bash
sudo yum install -y git
git clone <YOUR-REPO-URL> placement-portal
cd placement-portal
```

**OR** upload files directly using `scp`:

```bash
# Run this from your LAPTOP (not EC2):
scp -i placement-key.pem -r \
    backend/ Dockerfile .dockerignore ec2_setup.sh \
    ec2-user@<FLASK-EC2-PUBLIC-IP>:~/placement-portal/
```

### 4.3: Run the setup script

```bash
cd ~/placement-portal
chmod +x ec2_setup.sh
./ec2_setup.sh
```

This will:
- Install Docker
- Build the Flask container image
- Start the Flask server on port 5000
- Run a health check

### 4.4: Verify

```bash
curl http://localhost:5000/health
# Should return: {"server_port": 5000, "status": "ok", ...}
```

Also test from your laptop:
```bash
curl http://<FLASK-EC2-PUBLIC-IP>:5000/health
```

### Repeat Step 4 for all 3 Flask EC2 instances.

---

## Step 5: Set Up Nginx Load Balancer EC2

### 5.1: SSH into the Nginx EC2

```bash
ssh -i placement-key.pem ec2-user@<NGINX-EC2-PUBLIC-IP>
```

### 5.2: Install Nginx

```bash
sudo yum install -y nginx
```

### 5.3: Configure Nginx

```bash
sudo nano /etc/nginx/nginx.conf
```

Paste the following (replace the 3 private IPs!):

```nginx
worker_processes auto;

events {
    worker_connections 256;
}

http {
    upstream placement_backends {
        server <EC2-1-PRIVATE-IP>:5000 max_fails=3 fail_timeout=30s;
        server <EC2-2-PRIVATE-IP>:5000 max_fails=3 fail_timeout=30s;
        server <EC2-3-PRIVATE-IP>:5000 max_fails=3 fail_timeout=30s;
        keepalive 32;
    }

    log_format main '$remote_addr - [$time_local] '
                    '"$request" $status '
                    'upstream=$upstream_addr '
                    'req_time=${request_time}s';

    access_log /var/log/nginx/access.log main;
    error_log  /var/log/nginx/error.log warn;

    sendfile        on;
    keepalive_timeout 65;

    gzip on;
    gzip_types application/json text/plain;

    server {
        listen 8080;
        server_name _;

        location /nginx-status {
            return 200 '{"nginx":"ok"}';
            add_header Content-Type application/json;
        }

        location / {
            proxy_pass http://placement_backends;

            proxy_set_header Host            $host;
            proxy_set_header X-Real-IP       $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

            proxy_connect_timeout 10s;
            proxy_send_timeout    30s;
            proxy_read_timeout    30s;

            add_header 'Access-Control-Allow-Origin'  '*' always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
            add_header 'Access-Control-Allow-Headers' 'Content-Type' always;

            if ($request_method = OPTIONS) {
                return 204;
            }
        }
    }
}
```

> **IMPORTANT:** Replace `<EC2-1-PRIVATE-IP>`, `<EC2-2-PRIVATE-IP>`, `<EC2-3-PRIVATE-IP>` with the actual private IPs of your 3 Flask EC2 instances.

### 5.4: Start Nginx

```bash
sudo nginx -t              # Test config
sudo systemctl start nginx  # Start Nginx
sudo systemctl enable nginx  # Auto-start on reboot
```

### 5.5: Verify Load Balancer

From your laptop:
```bash
# Test 6 requests — watch the port rotate!
for i in 1 2 3 4 5 6; do
    echo -n "Request $i → "
    curl -s http://<NGINX-EC2-PUBLIC-IP>:8080/api/stats | python3 -c "import sys,json; print('served by :' + str(json.load(sys.stdin)['server_port']))"
done
```

Expected output:
```
Request 1 → served by :5000
Request 2 → served by :5000
Request 3 → served by :5000
Request 4 → served by :5000  (same port since all backends use 5000)
```

> The port will show `5000` for all since each Docker container uses port 5000 internally. The load balancing is visible in Nginx access logs:
> ```bash
> # SSH into Nginx EC2, then:
> sudo tail -f /var/log/nginx/access.log
> # Watch upstream= rotate between the 3 private IPs!
> ```

---

## Step 6: Deploy Frontend to Amazon S3

### Option A: Using the script (from your laptop)

```bash
chmod +x deploy_frontend.sh
./deploy_frontend.sh <NGINX-EC2-PUBLIC-IP> campus-placement-portal-2026
```

### Option B: Manual steps via AWS Console

1. Go to **S3** → **Create Bucket**
   - Name: `campus-placement-portal-2026` (must be globally unique)
   - Region: same as your EC2 instances
   - **Uncheck** "Block all public access"
   - Click **Create**

2. Go to **Bucket** → **Properties** → **Static website hosting**
   - Enable
   - Index document: `index.html`
   - Save

3. Go to **Permissions** → **Bucket policy**, paste:
   ```json
   {
       "Version": "2012-10-17",
       "Statement": [
           {
               "Sid": "PublicReadGetObject",
               "Effect": "Allow",
               "Principal": "*",
               "Action": "s3:GetObject",
               "Resource": "arn:aws:s3:::campus-placement-portal-2026/*"
           }
       ]
   }
   ```

4. **Before uploading**, edit `frontend/index.html` and `frontend/admin.html`:
   ```javascript
   // Change this:
   const API = "http://localhost:8080";
   // To this:
   const API = "http://<NGINX-EC2-PUBLIC-IP>:8080";
   ```

5. Go to **Objects** → **Upload** → Upload both HTML files

6. Your portal URL will be:
   ```
   http://campus-placement-portal-2026.s3-website-us-east-1.amazonaws.com
   ```

---

## Step 7: Verify Everything Works

### Test the full flow:

1. **Open the S3 URL** in your browser
   - Jobs should load from the EC2 backends
   - Server badge should show the backend port

2. **Apply for a job** — should work through the load balancer

3. **Check Admin Dashboard** (add `/admin.html` to the S3 URL)

4. **Run load test** from your laptop:
   ```bash
   locust -f load_testing/locustfile.py \
       --host=http://<NGINX-EC2-PUBLIC-IP>:8080 \
       --headless --users 50 --spawn-rate 5 --run-time 1m
   ```

5. **Test fault tolerance** — stop one Flask container:
   ```bash
   # SSH into Flask EC2 #1
   docker stop placement-backend
   
   # Portal should still work (2 backends remaining!)
   
   # Restart it
   docker start placement-backend
   ```

---

## Step 8: Cleanup (After Demo)

**Important:** Always clean up to avoid charges!

```bash
# Terminate all EC2 instances
aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=placement-portal" \
    --query 'Reservations[*].Instances[*].InstanceId' \
    --output text | xargs -I {} aws ec2 terminate-instances --instance-ids {}

# Delete S3 bucket
aws s3 rm s3://campus-placement-portal-2026 --recursive
aws s3 rb s3://campus-placement-portal-2026

# Delete security group (wait for instances to terminate first)
aws ec2 delete-security-group --group-name placement-portal-sg

# Delete key pair
aws ec2 delete-key-pair --key-name placement-key
rm placement-key.pem
```

---

## Summary of AWS Services Used

| AWS Service | Purpose | Free Tier? |
|------------|---------|-----------|
| EC2 (t2.micro × 4) | Flask backends + Nginx | ✅ Yes (750 hrs/month) |
| S3 | Static frontend hosting | ✅ Yes (5 GB) |
| VPC + Security Groups | Network security | ✅ Yes (free) |
| Docker on EC2 | Containerized Flask | ✅ Yes (runs on EC2) |

---

## Concepts Demonstrated

| Concept | Implementation |
|---------|---------------|
| **Cloud Computing** | All servers run on AWS EC2 |
| **Virtualization** | Docker containers on EC2 |
| **Load Balancing** | Nginx distributes across 3 EC2 instances |
| **High Availability** | Kill one EC2 → system keeps running |
| **Fault Tolerance** | Nginx health checks auto-detect failures |
| **Scalability** | Add more EC2 instances to nginx.conf |
| **Static Website Hosting** | S3 serves frontend globally |
| **Infrastructure as Code** | Scripts automate entire deployment |
| **Distributed Systems** | Multiple servers, shared-nothing, round-robin |

---

## Troubleshooting

### "Connection refused" when accessing EC2

- Check security group allows the port (5000 or 8080)
- Check the container is running: `docker ps`
- Check container logs: `docker logs placement-backend`

### "CORS error" in browser

- Make sure Nginx config has the CORS headers
- Frontend API URL must point to Nginx EC2's **public IP**, not `localhost`

### "502 Bad Gateway" from Nginx

- Check Flask EC2s are reachable: `curl http://<PRIVATE-IP>:5000/health`
- Check all 3 Flask containers are running
- Check Nginx error log: `sudo tail /var/log/nginx/error.log`

### SSH "Permission denied"

- Make sure `.pem` file has correct permissions: `chmod 400 placement-key.pem`
- Use `ec2-user` as username: `ssh -i key.pem ec2-user@<IP>`
