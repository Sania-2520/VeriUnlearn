"""Prometheus metrics for the VeriUnlearn backend.

Exposes an OpenMetrics `/metrics` endpoint scraped by Prometheus plus the
in-process metric primitives used across the app (HTTP request telemetry and
the unlearning/deletion queue gauges referenced by production alert rules).
"""
from prometheus_client import Counter, Gauge, Histogram, generate_latest

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests handled by the backend.",
    labelnames=("method", "path", "status"),
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    labelnames=("method", "path"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

inference_request_duration_seconds = Histogram(
    "inference_request_duration_seconds",
    "End-to-end inference/chat latency in seconds.",
    labelnames=("method", "path"),
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30),
)

unlearning_queue_size = Gauge(
    "unlearning_queue_size",
    "Number of pending unlearning/deletion requests awaiting execution.",
    labelnames=("status",),
)

deletion_queue_size = Gauge(
    "deletion_queue_size",
    "Number of pending deletion queue items.",
    labelnames=("status",),
)


def metrics_body() -> bytes:
    """Render the current registry in Prometheus text format."""
    return generate_latest()
