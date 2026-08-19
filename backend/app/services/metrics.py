"""Prometheus metrics (Phase 7 observability).

Exposes request counters/histograms plus custom gauges fed by the monitoring
service. The ``/metrics`` endpoint renders this registry as Prometheus text
format; see ``deploy/prometheus/prometheus.yml`` for scrape config.
"""
from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, generate_latest

REQUESTS_TOTAL = Counter(
    "veriunlearn_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)
REQUESTS_LATENCY = Histogram(
    "veriunlearn_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
SYSTEM_CPU = Gauge("veriunlearn_system_cpu_percent", "System CPU percent")
SYSTEM_RAM = Gauge("veriunlearn_system_ram_mb", "System RAM in MB")
DISK_USED = Gauge("veriunlearn_disk_used_mb", "Disk used in MB")
QUEUE_IN_FLIGHT = Gauge("veriunlearn_deletion_queue_in_flight", "In-flight deletion requests")
API_LATENCY = Gauge("veriunlearn_api_avg_latency_ms", "Average API latency in ms")
API_ERROR_RATE = Gauge("veriunlearn_api_error_rate", "API error rate (ratio)")
UPTIME = Gauge("veriunlearn_uptime_seconds", "Process uptime in seconds")


def observe_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    REQUESTS_TOTAL.labels(method=method, path=path, status=str(status_code)).inc()
    REQUESTS_LATENCY.labels(method=method, path=path).observe(duration_seconds)


def update_system_gauges(snapshot: dict) -> None:
    """Feed the latest monitoring snapshot into Prometheus gauges."""
    system = snapshot.get("system", {})
    if system.get("system_cpu_percent") is not None:
        SYSTEM_CPU.set(system["system_cpu_percent"])
    if system.get("system_ram_mb") is not None:
        SYSTEM_RAM.set(system["system_ram_mb"])
    if system.get("disk_used_mb") is not None:
        DISK_USED.set(system["disk_used_mb"])
    if snapshot.get("queue", {}).get("in_flight") is not None:
        QUEUE_IN_FLIGHT.set(snapshot["queue"]["in_flight"])
    api = snapshot.get("api", {})
    if api.get("avg_latency_ms") is not None:
        API_LATENCY.set(api["avg_latency_ms"])
    if api.get("error_rate") is not None:
        API_ERROR_RATE.set(api["error_rate"])
    if api.get("uptime_seconds") is not None:
        UPTIME.set(api["uptime_seconds"])


def render_metrics() -> bytes:
    return generate_latest()
