# ─────────────────────────────────────────────
# Dockerfile — Campus Placement Portal Backend
# ─────────────────────────────────────────────
# WHAT IS THIS?
#   This file tells Docker how to package our Flask
#   backend into a portable container image.
#
# WHY DOCKER?
#   Docker containers are like lightweight virtual machines.
#   Once built, the same image runs identically on:
#   - Your laptop
#   - An EC2 instance in AWS
#   - Any cloud provider
#
# HOW TO BUILD:
#   docker build -t placement-portal .
#
# HOW TO RUN:
#   docker run -p 5001:5000 placement-portal
# ─────────────────────────────────────────────

# Step 1: Start from a lightweight Python image
FROM python:3.11-slim

# Step 2: Set the working directory inside the container
WORKDIR /app

# Step 3: Copy and install Python dependencies FIRST
# (Docker caches this layer — faster rebuilds!)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Step 4: Copy the application code
COPY backend/app.py .
COPY backend/init_db.py .

# Step 5: Initialize the database inside the container
RUN python init_db.py

# Step 6: Expose port 5000 (Flask's default inside container)
EXPOSE 5000

# Step 7: Run the Flask server
# PORT is passed as an environment variable (default 5000)
ENV PORT=5000
CMD python app.py $PORT
