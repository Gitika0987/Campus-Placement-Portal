"""
=============================================================
  CUSTOM LOAD BALANCER — load_balancer.py
=============================================================
  WHAT IS THIS FILE?
  This is a custom HTTP load balancer written in Python.
  It replaces Nginx by distributing incoming requests
  across multiple Flask backend instances using Round Robin.

  WHY BUILD OUR OWN?
  Instead of relying on Nginx (an external tool), we built
  our own to demonstrate how load balancing actually works
  at the code level — a core distributed systems concept.

  HOW IT WORKS:
  1. Listens on port 8080 (single entry point)
  2. Maintains a list of backend servers (5001, 5002, 5003)
  3. For each incoming request, picks the next healthy server
  4. Forwards the request and returns the response
  5. Periodically health-checks all backends

  HOW TO RUN:
    python load_balancer.py
=============================================================
"""

import sys
import os
import time
import json
import threading
import itertools
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import urlparse

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

LB_PORT = 8080  # Port the load balancer listens on

# Backend server addresses (same as what Nginx used)
BACKENDS = [
    {"host": "172.31.92.47", "port": 5000, "healthy": True},
    {"host": "172.31.82.187", "port": 5000, "healthy": True},
    {"host": "172.31.82.67", "port": 5000, "healthy": True}
]



HEALTH_CHECK_INTERVAL = 5   # seconds between health checks
HEALTH_CHECK_TIMEOUT  = 3   # seconds to wait for health response
MAX_FAILS             = 3   # consecutive failures before marking down
FAIL_TIMEOUT          = 30  # seconds before retrying a failed server

# Track consecutive failures per backend
fail_counts = {i: 0 for i in range(len(BACKENDS))}
fail_times  = {i: 0 for i in range(len(BACKENDS))}

# ─────────────────────────────────────────────
# ROUND ROBIN ITERATOR
# ─────────────────────────────────────────────

"""
CONCEPT: Round Robin Algorithm
This is the simplest load balancing algorithm.
We cycle through servers in order: 1 → 2 → 3 → 1 → 2 → 3 → ...

itertools.cycle creates an infinite loop over the list.
We skip unhealthy servers automatically.
"""
backend_cycle = itertools.cycle(range(len(BACKENDS)))
cycle_lock = threading.Lock()

# Request counter for logging
request_counter = 0
counter_lock = threading.Lock()

# Path to frontend directory (for serving static files)
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")


def get_next_healthy_backend():
    """
    CONCEPT: Failover
    Pick the next healthy backend using round-robin.
    If a server is marked unhealthy, skip it.
    If ALL servers are down, return None.
    """
    with cycle_lock:
        tried = 0
        while tried < len(BACKENDS):
            idx = next(backend_cycle)
            backend = BACKENDS[idx]

            # If server was marked down, check if enough time passed to retry
            if not backend["healthy"]:
                if time.time() - fail_times.get(idx, 0) > FAIL_TIMEOUT:
                    # Give it another chance
                    backend["healthy"] = True
                    fail_counts[idx] = 0
                    print(f"  ↻ Retrying backend :{backend['port']} after timeout")
                else:
                    tried += 1
                    continue

            return idx, backend

        return None, None


def mark_backend_failed(idx):
    """Mark a backend as failed after a request error."""
    fail_counts[idx] = fail_counts.get(idx, 0) + 1
    if fail_counts[idx] >= MAX_FAILS:
        BACKENDS[idx]["healthy"] = False
        fail_times[idx] = time.time()
        print(f"  ✗ Backend :{BACKENDS[idx]['port']} marked DOWN after {MAX_FAILS} failures")


def mark_backend_success(idx):
    """Reset failure counter on successful request."""
    fail_counts[idx] = 0
    BACKENDS[idx]["healthy"] = True


# ─────────────────────────────────────────────
# HEALTH CHECKER THREAD
# ─────────────────────────────────────────────

def health_checker():
    """
    CONCEPT: Health Monitoring
    A background thread that periodically pings each backend's
    /health endpoint. If a server doesn't respond, it gets
    marked as unhealthy and traffic is routed away from it.

    This is exactly what Nginx does with its max_fails config!
    """
    while True:
        time.sleep(HEALTH_CHECK_INTERVAL)
        for idx, backend in enumerate(BACKENDS):
            url = f"http://{backend['host']}:{backend['port']}/health"
            try:
                req = Request(url)
                resp = urlopen(req, timeout=HEALTH_CHECK_TIMEOUT)
                if resp.getcode() == 200:
                    if not backend["healthy"]:
                        print(f"  ✓ Backend :{backend['port']} recovered!")
                    mark_backend_success(idx)
            except Exception:
                mark_backend_failed(idx)


# ─────────────────────────────────────────────
# CONTENT TYPE DETECTION
# ─────────────────────────────────────────────

MIME_TYPES = {
    ".html": "text/html",
    ".css":  "text/css",
    ".js":   "application/javascript",
    ".json": "application/json",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".ico":  "image/x-icon",
    ".svg":  "image/svg+xml",
}


# ─────────────────────────────────────────────
# REQUEST HANDLER
# ─────────────────────────────────────────────

class LoadBalancerHandler(BaseHTTPRequestHandler):
    """
    CONCEPT: Reverse Proxy
    This handler receives HTTP requests from the browser
    and forwards them to one of the backend servers.

    It acts as a middleman — the browser thinks it's talking
    to one server, but behind the scenes, multiple servers
    are sharing the work.
    """

    def log_message(self, format, *args):
        """Suppress default logging — we do our own."""
        pass

    def do_OPTIONS(self):
        """
        CONCEPT: CORS Preflight
        Browsers send an OPTIONS request before POST/PUT/DELETE
        to check if the server allows cross-origin requests.
        We respond with the right headers to say "yes, go ahead."
        """
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):
        # Serve static frontend files if path matches
        if self._try_serve_static():
            return
        self._proxy_request("GET")

    def do_POST(self):
        self._proxy_request("POST")

    def do_PUT(self):
        self._proxy_request("PUT")

    def do_DELETE(self):
        self._proxy_request("DELETE")

    def _try_serve_static(self):
        """
        CONCEPT: Static File Server
        If the request is for a frontend file (HTML/CSS/JS),
        serve it directly instead of proxying to a backend.
        This replaces the need for a separate web server.
        """
        path = self.path.split("?")[0]  # Remove query string

        # Map root to index.html
        if path == "/" or path == "":
            path = "/index.html"

        # Only serve known frontend files
        if path in ("/index.html", "/admin.html"):
            filepath = os.path.join(FRONTEND_DIR, path.lstrip("/"))
            if os.path.exists(filepath):
                ext = os.path.splitext(filepath)[1]
                content_type = MIME_TYPES.get(ext, "application/octet-stream")

                with open(filepath, "rb") as f:
                    content = f.read()

                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                self.wfile.write(content)
                return True

        return False

    def _proxy_request(self, method):
        """
        CONCEPT: Request Forwarding (Reverse Proxy)
        1. Pick the next healthy backend (round robin)
        2. Forward the client's request to that backend
        3. Return the backend's response to the client

        This is the core of what a load balancer does!
        """
        global request_counter

        # Get the next healthy backend
        idx, backend = get_next_healthy_backend()

        if backend is None:
            # All servers are down!
            self.send_response(503)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            error_body = json.dumps({
                "error": "All backend servers are unavailable",
                "status": 503
            })
            self.wfile.write(error_body.encode())
            print(f"  ✗ 503 — All backends DOWN for {method} {self.path}")
            return

        # Build the backend URL
        target_url = f"http://{backend['host']}:{backend['port']}{self.path}"

        # Read the request body (for POST/PUT)
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        try:
            # Forward the request to the backend
            req = Request(target_url, data=body, method=method)

            # Copy relevant headers
            if self.headers.get("Content-Type"):
                req.add_header("Content-Type", self.headers["Content-Type"])
            req.add_header("X-Forwarded-For", self.client_address[0])
            req.add_header("X-Real-IP", self.client_address[0])

            # Execute the request
            start_time = time.time()
            response = urlopen(req, timeout=30)
            elapsed = round((time.time() - start_time) * 1000, 1)

            # Read the response
            resp_body = response.read()
            resp_status = response.getcode()
            resp_content_type = response.headers.get("Content-Type", "application/json")

            # Send the response back to the client
            self.send_response(resp_status)
            self.send_header("Content-Type", resp_content_type)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("X-Served-By", str(backend["port"]))
            self.send_header("X-Response-Time", f"{elapsed}ms")
            self.end_headers()
            self.wfile.write(resp_body)

            mark_backend_success(idx)

            # Log the request
            with counter_lock:
                request_counter += 1
                count = request_counter

            print(f"  [{count:>4}] {method:>4} {self.path:<35} → :{backend['port']}  ({elapsed}ms)  ✓ {resp_status}")

        except Exception as e:
            mark_backend_failed(idx)

            # Try next backend on failure (one retry)
            retry_idx, retry_backend = get_next_healthy_backend()
            if retry_backend and retry_idx != idx:
                try:
                    retry_url = f"http://{retry_backend['host']}:{retry_backend['port']}{self.path}"
                    req = Request(retry_url, data=body, method=method)
                    if self.headers.get("Content-Type"):
                        req.add_header("Content-Type", self.headers["Content-Type"])

                    response = urlopen(req, timeout=30)
                    resp_body = response.read()
                    resp_status = response.getcode()
                    resp_content_type = response.headers.get("Content-Type", "application/json")

                    self.send_response(resp_status)
                    self.send_header("Content-Type", resp_content_type)
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
                    self.send_header("Access-Control-Allow-Headers", "Content-Type")
                    self.send_header("X-Served-By", str(retry_backend["port"]))
                    self.end_headers()
                    self.wfile.write(resp_body)

                    mark_backend_success(retry_idx)
                    print(f"  [RETRY] {method} {self.path} → :{retry_backend['port']}  ✓ (failed :{backend['port']})")
                    return
                except Exception:
                    mark_backend_failed(retry_idx)

            # All retries failed
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            error_body = json.dumps({
                "error": f"Backend server :{backend['port']} is not responding",
                "status": 502
            })
            self.wfile.write(error_body.encode())
            print(f"  ✗ 502 — Backend :{backend['port']} failed for {method} {self.path}")


# ─────────────────────────────────────────────
# THREADED HTTP SERVER
# ─────────────────────────────────────────────

class ThreadedHTTPServer(HTTPServer):
    """
    CONCEPT: Multi-threaded Server
    Handle each request in a separate thread so one slow
    request doesn't block all the others.
    """
    allow_reuse_address = True

    def process_request(self, request, client_address):
        thread = threading.Thread(target=self._handle, args=(request, client_address))
        thread.daemon = True
        thread.start()

    def _handle(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)


# ─────────────────────────────────────────────
# MAIN — START THE LOAD BALANCER
# ─────────────────────────────────────────────

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else LB_PORT

    print(f"""
╔# Change this:
# ║  Backends  : :5001, :5002, :5003             ║

# To this:
║  Backends  : 3 EC2 Backend Instances         ║

    """)

    # Start the health checker in a background thread
    health_thread = threading.Thread(target=health_checker, daemon=True)
    health_thread.start()
    print("  ✓ Health checker started (background thread)")

    # Start the load balancer server
    server = ThreadedHTTPServer(("0.0.0.0", port), LoadBalancerHandler)
    print(f"  ✓ Load balancer listening on http://localhost:{port}")
    print(f"  ✓ Frontend served at http://localhost:{port}/")
    print()
    print("  Live request log:")
    print("  " + "─" * 70)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  ⚙ Shutting down load balancer...")
        server.shutdown()
        print("  ✓ Load balancer stopped.")
