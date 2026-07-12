from __future__ import annotations

from prometheus_client import Counter, Histogram, Gauge, Info

APP_INFO = Info("veriunlearn", "VeriUnlearn application information")
APP_INFO.info({
    "version": "1.0.0",
    "algorithms": "certified_removal,gradient_ascent,influence_functions,sisa,bad_teacher,catastrophic_forgetting,relu_erasure",
})

HTTP_REQUESTS_TOTAL = Counter(
    "veriunlearn_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "veriunlearn_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

TRAINING_JOBS_TOTAL = Counter(
    "veriunlearn_training_jobs_total",
    "Total training jobs",
    ["status"],
)

TRAINING_DURATION = Histogram(
    "veriunlearn_training_duration_seconds",
    "Training job duration in seconds",
    buckets=[10, 30, 60, 120, 300, 600],
)

UNLEARNING_REQUESTS_TOTAL = Counter(
    "veriunlearn_unlearning_requests_total",
    "Total unlearning requests",
    ["algorithm", "status"],
)

UNLEARNING_DURATION = Histogram(
    "veriunlearn_unlearning_duration_seconds",
    "Unlearning operation duration in seconds",
    ["algorithm"],
    buckets=[1, 5, 10, 30, 60, 120],
)

CHAT_MESSAGES_TOTAL = Counter(
    "veriunlearn_chat_messages_total",
    "Total chat messages processed",
)

ACTIVE_USERS = Gauge(
    "veriunlearn_active_users",
    "Number of active users",
)

DOCUMENTS_PROCESSED = Counter(
    "veriunlearn_documents_processed_total",
    "Total documents processed",
    ["status"],
)

MODEL_VERSIONS = Gauge(
    "veriunlearn_model_versions",
    "Number of model versions",
    ["status"],
)

RATE_LIMIT_HITS = Counter(
    "veriunlearn_rate_limit_hits_total",
    "Total rate limit hits",
    ["category"],
)
