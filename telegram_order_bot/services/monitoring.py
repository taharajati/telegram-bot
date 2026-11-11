"""
services/monitoring.py — Sentry + Prometheus + Health checks.

Usage:
    from services.monitoring import metrics, init_sentry, start_metrics_server

    # In main.py:
    init_sentry()                          # Call BEFORE anything else
    start_metrics_server()                 # Starts /metrics endpoint
    metrics.bot_messages.inc()             # Use anywhere
    metrics.track_order("created")         # Convenience wrapper
"""
from __future__ import annotations

import logging
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# Prometheus Metrics
# ════════════════════════════════════════════════════════════════

try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        Info,
        generate_latest,
        CONTENT_TYPE_LATEST,
        REGISTRY,
        CollectorRegistry,
        multiprocess,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.info("prometheus_client not installed — metrics disabled")


class _Metrics:
    """All application metrics in one place."""

    def __init__(self):
        if not PROMETHEUS_AVAILABLE:
            return

        # ── Core counters ──
        self.bot_messages = Counter(
            "foroshgram_bot_messages_total",
            "Total bot messages sent",
            ["direction", "status"],
        )
        self.bot_updates = Counter(
            "foroshgram_bot_updates_total",
            "Total incoming Telegram updates processed",
            ["update_type", "handler"],
        )
        self.bot_errors = Counter(
            "foroshgram_bot_errors_total",
            "Total errors caught by global error handler",
            ["error_type"],
        )

        # ── Business metrics ──
        self.orders = Counter(
            "foroshgram_orders_total",
            "Total orders",
            ["status"],
        )
        self.payments = Counter(
            "foroshgram_payments_total",
            "Total payment attempts",
            ["method", "status"],
        )
        self.products = Counter(
            "foroshgram_products_total",
            "Product operations",
            ["operation"],
        )
        self.users = Counter(
            "foroshgram_users_total",
            "User actions",
            ["action"],
        )
        self.support_tickets = Counter(
            "foroshgram_support_tickets_total",
            "Support tickets opened",
        )
        self.conversations = Counter(
            "foroshgram_conversations_total",
            "Buyer-seller conversations",
            ["direction"],
        )
        self.events_emitted = Counter(
            "foroshgram_events_emitted_total",
            "Events emitted on the event bus",
            ["event"],
        )

        # ── Gauges ──
        self.active_shops = Gauge(
            "foroshgram_active_shops",
            "Number of active shops",
        )
        self.active_sellers = Gauge(
            "foroshgram_active_sellers",
            "Number of active sellers",
        )
        self.pending_orders = Gauge(
            "foroshgram_pending_orders",
            "Number of pending orders",
        )
        self.bot_uptime = Gauge(
            "foroshgram_bot_uptime_seconds",
            "Bot uptime in seconds",
        )

        # ── Info ──
        self.app_info = Info("foroshgram", "Application info")

    # ── Convenience methods ──

    def track_order(self, status: str):
        if PROMETHEUS_AVAILABLE:
            self.orders.labels(status=status).inc()

    def track_payment(self, method: str, status: str):
        if PROMETHEUS_AVAILABLE:
            self.payments.labels(method=method, status=status).inc()

    def track_event(self, event_name: str):
        if PROMETHEUS_AVAILABLE:
            self.events_emitted.labels(event=event_name).inc()

    def track_error(self, error_type: str):
        if PROMETHEUS_AVAILABLE:
            self.bot_errors.labels(error_type=error_type).inc()

    def track_user(self, action: str):
        if PROMETHEUS_AVAILABLE:
            self.users.labels(action=action).inc()

    def set_app_info(self, **kwargs):
        if PROMETHEUS_AVAILABLE:
            self.app_info.info(kwargs)


# Singleton
metrics = _Metrics()


# ════════════════════════════════════════════════════════════════
# Prometheus HTTP Server
# ════════════════════════════════════════════════════════════════

class _MetricsHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for /metrics and /healthz."""

    def do_GET(self):
        if self.path == "/metrics" and PROMETHEUS_AVAILABLE:
            output = generate_latest(REGISTRY)
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(output)
        elif self.path == "/healthz":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
        elif self.path == "/readyz":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ready")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress default request logging
        pass


def start_metrics_server(port: int = 9090):
    """Start the /metrics endpoint in a daemon thread."""
    if not PROMETHEUS_AVAILABLE:
        logger.info("Prometheus not available — skipping metrics server")
        return

    server = HTTPServer(("0.0.0.0", port), _MetricsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Prometheus metrics server started on :{port}/metrics")


# ════════════════════════════════════════════════════════════════
# Sentry
# ════════════════════════════════════════════════════════════════

def init_sentry(dsn: str = "", environment: str = "production", traces_sample_rate: float = 0.1):
    """Initialize Sentry error tracking. Safe to call if DSN is empty."""
    if not dsn:
        logger.info("Sentry DSN not set — error tracking disabled")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.ERROR,
        )

        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            traces_sample_rate=traces_sample_rate,
            integrations=[sentry_logging],
            send_default_pii=False,
            attach_stacktrace=True,
            _experiments={"record_sql_params": True},
        )
        logger.info(f"Sentry initialized (env={environment})")
    except ImportError:
        logger.warning("sentry-sdk not installed — error tracking disabled")
    except Exception as e:
        logger.warning(f"Sentry init failed: {e}")


# ════════════════════════════════════════════════════════════════
# Uptime tracker
# ════════════════════════════════════════════════════════════════

_START_TIME: Optional[float] = None


def mark_started():
    """Call once when bot starts."""
    global _START_TIME
    _START_TIME = time.time()
    if PROMETHEUS_AVAILABLE:
        metrics.bot_uptime.set(0)
        # Uptime is derived from start_time
        try:
            from prometheus_client import Gauge
            # Register uptime as a callback gauge
            def _uptime():
                return time.time() - _START_TIME if _START_TIME else 0
            uptime_gauge = Gauge(
                "foroshgram_uptime_seconds",
                "Bot uptime in seconds",
                registry=REGISTRY,
            )
            uptime_gauge.set_function(_uptime)
        except Exception:
            pass
