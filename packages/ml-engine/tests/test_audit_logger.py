import json
import os
import time

import pytest

from security.audit_logger import AuditEntry, AuditLogger


@pytest.fixture
def audit_logger(tmp_path):
    return AuditLogger(max_entries=100, persist_path=str(tmp_path / "audit_log"))


@pytest.fixture
def small_audit_logger(tmp_path):
    return AuditLogger(max_entries=5, persist_path=str(tmp_path / "audit_log_small"))


# ── Event creation ───────────────────────────────────────────────────────


class TestEventCreation:
    def test_record_creates_entry(self, audit_logger):
        audit_logger.record(action="unlearn", resource="model_v1")
        entries = audit_logger.get_recent(10)
        assert len(entries) == 1
        assert entries[0]["action"] == "unlearn"
        assert entries[0]["resource"] == "model_v1"

    def test_default_values(self, audit_logger):
        audit_logger.record(action="test", resource="res")
        entry = audit_logger.get_recent(1)[0]
        assert entry["status"] == "success"
        assert entry["actor"] == "system"
        assert entry["details"] == {}
        assert entry["duration_ms"] == 0.0

    def test_custom_values(self, audit_logger):
        audit_logger.record(
            action="delete",
            resource="dataset",
            status="failure",
            actor="admin",
            details={"reason": "permission denied"},
            duration_ms=123.456,
        )
        entry = audit_logger.get_recent(1)[0]
        assert entry["status"] == "failure"
        assert entry["actor"] == "admin"
        assert entry["details"] == {"reason": "permission denied"}
        assert entry["duration_ms"] == 123.46

    def test_duration_ms_rounded(self, audit_logger):
        audit_logger.record(action="x", resource="y", duration_ms=99.999)
        entry = audit_logger.get_recent(1)[0]
        assert entry["duration_ms"] == 100.0

    def test_none_details_becomes_empty_dict(self, audit_logger):
        audit_logger.record(action="a", resource="r", details=None)
        entry = audit_logger.get_recent(1)[0]
        assert entry["details"] == {}

    def test_timestamp_is_valid_iso_format(self, audit_logger):
        audit_logger.record(action="check", resource="time")
        entry = audit_logger.get_recent(1)[0]
        ts = entry["timestamp"]
        assert "T" in ts
        assert len(ts) > 10


# ── Event storage ────────────────────────────────────────────────────────


class TestEventStorage:
    def test_multiple_entries_stored(self, audit_logger):
        for i in range(10):
            audit_logger.record(action=f"action_{i}", resource="res")
        assert len(audit_logger.get_recent(100)) == 10

    def test_entries_stored_in_order(self, audit_logger):
        for i in range(5):
            audit_logger.record(action=f"action_{i}", resource="res")
        entries = audit_logger.get_recent(100)
        for i, entry in enumerate(entries):
            assert entry["action"] == f"action_{i}"

    def test_max_entries_enforced(self, small_audit_logger):
        for i in range(10):
            small_audit_logger.record(action=f"action_{i}", resource="res")
        entries = small_audit_logger.get_recent(100)
        assert len(entries) == 5
        assert entries[0]["action"] == "action_5"
        assert entries[-1]["action"] == "action_9"


# ── Event retrieval ──────────────────────────────────────────────────────


class TestEventRetrieval:
    def test_get_recent_default_50(self, audit_logger):
        for i in range(60):
            audit_logger.record(action=f"action_{i}", resource="res")
        entries = audit_logger.get_recent()
        assert len(entries) == 50
        assert entries[0]["action"] == "action_10"

    def test_get_recent_n(self, audit_logger):
        for i in range(20):
            audit_logger.record(action=f"action_{i}", resource="res")
        entries = audit_logger.get_recent(5)
        assert len(entries) == 5
        assert entries[0]["action"] == "action_15"

    def test_get_recent_empty(self, audit_logger):
        entries = audit_logger.get_recent()
        assert entries == []

    def test_get_recent_larger_than_stored(self, audit_logger):
        audit_logger.record(action="only", resource="r")
        entries = audit_logger.get_recent(100)
        assert len(entries) == 1

    def test_returns_list_of_dicts(self, audit_logger):
        audit_logger.record(action="test", resource="r")
        entries = audit_logger.get_recent()
        assert isinstance(entries, list)
        assert isinstance(entries[0], dict)


# ── Severity / status levels ─────────────────────────────────────────────


class TestStatusLevels:
    def test_success_status(self, audit_logger):
        audit_logger.record(action="op", resource="r", status="success")
        entry = audit_logger.get_recent(1)[0]
        assert entry["status"] == "success"

    def test_failure_status(self, audit_logger):
        audit_logger.record(action="op", resource="r", status="failure")
        entry = audit_logger.get_recent(1)[0]
        assert entry["status"] == "failure"

    def test_warning_status(self, audit_logger):
        audit_logger.record(action="op", resource="r", status="warning")
        entry = audit_logger.get_recent(1)[0]
        assert entry["status"] == "warning"

    def test_filter_by_status(self, audit_logger):
        audit_logger.record(action="a1", resource="r", status="success")
        audit_logger.record(action="a2", resource="r", status="failure")
        audit_logger.record(action="a3", resource="r", status="success")
        failures = audit_logger.filter(status="failure")
        assert len(failures) == 1
        assert failures[0]["action"] == "a2"

    def test_filter_by_action(self, audit_logger):
        audit_logger.record(action="unlearn", resource="m1")
        audit_logger.record(action="verify", resource="m2")
        audit_logger.record(action="unlearn", resource="m3")
        unlearns = audit_logger.filter(action="unlearn")
        assert len(unlearns) == 2

    def test_filter_by_action_and_status(self, audit_logger):
        audit_logger.record(action="unlearn", resource="m1", status="success")
        audit_logger.record(action="unlearn", resource="m2", status="failure")
        audit_logger.record(action="verify", resource="m3", status="success")
        result = audit_logger.filter(action="unlearn", status="failure")
        assert len(result) == 1
        assert result[0]["resource"] == "m2"


# ── Timestamp handling ───────────────────────────────────────────────────


class TestTimestampHandling:
    def test_timestamp_present(self, audit_logger):
        audit_logger.record(action="ts_check", resource="r")
        entry = audit_logger.get_recent(1)[0]
        assert "timestamp" in entry
        assert isinstance(entry["timestamp"], str)

    def test_timestamps_are_unique(self, audit_logger):
        audit_logger.record(action="a1", resource="r")
        time.sleep(0.01)
        audit_logger.record(action="a2", resource="r")
        entries = audit_logger.get_recent(2)
        assert entries[0]["timestamp"] != entries[1]["timestamp"]

    def test_timestamps_are_chronological(self, audit_logger):
        audit_logger.record(action="first", resource="r")
        time.sleep(0.01)
        audit_logger.record(action="second", resource="r")
        entries = audit_logger.get_recent(2)
        assert entries[0]["timestamp"] <= entries[1]["timestamp"]


# ── Stats ────────────────────────────────────────────────────────────────


class TestStats:
    def test_empty_stats(self, audit_logger):
        stats = audit_logger.get_stats()
        assert stats["total_entries"] == 0
        assert stats["status_counts"] == {}
        assert stats["action_counts"] == {}
        assert stats["most_common_action"] is None

    def test_stats_count_correctly(self, audit_logger):
        audit_logger.record(action="unlearn", resource="m1", status="success")
        audit_logger.record(action="unlearn", resource="m2", status="failure")
        audit_logger.record(action="verify", resource="m3", status="success")
        stats = audit_logger.get_stats()
        assert stats["total_entries"] == 3
        assert stats["status_counts"] == {"success": 2, "failure": 1}
        assert stats["action_counts"] == {"unlearn": 2, "verify": 1}
        assert stats["most_common_action"] == "unlearn"

    def test_most_common_action_with_single_action(self, audit_logger):
        audit_logger.record(action="only", resource="r")
        stats = audit_logger.get_stats()
        assert stats["most_common_action"] == "only"


# ── Persistence ──────────────────────────────────────────────────────────


class TestPersistence:
    def test_persist_called_at_100_entries(self, tmp_path):
        logger = AuditLogger(max_entries=100, persist_path=str(tmp_path / "persist_test"))
        for i in range(100):
            logger.record(action=f"action_{i}", resource="r")
        log_file = tmp_path / "persist_test" / "audit_log.json"
        assert log_file.exists()
        data = json.loads(log_file.read_text())
        assert len(data) == 100

    def test_persist_creates_correct_json(self, tmp_path):
        logger = AuditLogger(max_entries=100, persist_path=str(tmp_path / "json_test"))
        logger.record(action="test_action", resource="test_resource", details={"key": "value"})
        for i in range(99):
            logger.record(action="filler", resource="r")
        log_file = tmp_path / "json_test" / "audit_log.json"
        data = json.loads(log_file.read_text())
        assert data[0]["action"] == "test_action"
        assert data[0]["resource"] == "test_resource"
        assert data[0]["details"]["key"] == "value"

    def test_persist_path_created_automatically(self, tmp_path):
        deep_path = str(tmp_path / "a" / "b" / "c" / "audit_log")
        logger = AuditLogger(persist_path=deep_path)
        assert os.path.isdir(deep_path)


# ── Thread safety ────────────────────────────────────────────────────────


class TestThreadSafety:
    def test_concurrent_records(self, tmp_path):
        import threading

        logger = AuditLogger(max_entries=10000, persist_path=str(tmp_path / "thread_test"))
        errors = []

        def record_events(prefix):
            try:
                for i in range(50):
                    logger.record(action=f"{prefix}_{i}", resource="r")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_events, args=(f"t{t}",)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        entries = logger.get_recent(10000)
        assert len(entries) == 200
