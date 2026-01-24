"""
Gunicorn configuration file for production deployment.

Run with:
    gunicorn config.wsgi:application -c gunicorn.conf.py

Or with uvicorn workers (async, faster):
    gunicorn config.wsgi:application -k uvicorn.workers.UvicornWorker -c gunicorn.conf.py
"""

import multiprocessing
import os

# ==============================================
# SERVER SOCKET
# ==============================================
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
backlog = 2048

# ==============================================
# WORKERS
# ==============================================
# Recommended: (2 x CPU cores) + 1
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))

# Worker class: Use uvicorn for async support
# Options: 'sync', 'eventlet', 'gevent', 'uvicorn.workers.UvicornWorker'
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "sync")

# Maximum requests before worker restart (prevents memory leaks)
max_requests = 1000
max_requests_jitter = 50

# Timeout for worker responses (seconds)
timeout = 30

# Graceful timeout
graceful_timeout = 30

# Keep-alive connections
keepalive = 5

# ==============================================
# THREADS (only for sync workers)
# ==============================================
threads = int(os.getenv("GUNICORN_THREADS", 2))

# ==============================================
# SECURITY
# ==============================================
# Limit request line size (bytes)
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# ==============================================
# LOGGING
# ==============================================
# Access log - set to '-' for stdout, or a file path
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

# Access log format
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sμs'

# ==============================================
# PROCESS NAMING
# ==============================================
proc_name = "crm_gunicorn"

# ==============================================
# SERVER HOOKS
# ==============================================
def on_starting(server):
    """Called before master process is initialized."""
    pass

def on_reload(server):
    """Called to reload the app."""
    pass

def worker_int(worker):
    """Called when a worker receives INT or QUIT signal."""
    pass

def worker_exit(server, worker):
    """Called when a worker has exited."""
    pass

# ==============================================
# PERFORMANCE TUNING (Production)
# ==============================================
# Preload app code before worker processes are forked
# This saves memory but requires careful handling of connections
preload_app = os.getenv("GUNICORN_PRELOAD", "False") == "True"

# Recycle workers after N requests to prevent memory leaks
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", 1000))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", 100))
