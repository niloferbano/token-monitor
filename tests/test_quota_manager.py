from app.core.service import QuotaManager


def test_quota_manager_allows_within_budget() -> None:
    manager = QuotaManager()
    manager.register_tenant("tenant-a", budget_tokens=10, window_seconds=60)

    decision = manager.check_admission(
        tenant_id="tenant-a",
        request_id="req-1",
        requested_tokens=4,
        now_sec=100,
    )

    assert decision.allowed is True
    assert decision.deduplicated is False
    assert decision.used_tokens == 4
    assert decision.remaining_tokens == 6
    assert decision.reason is None


def test_quota_manager_rejects_when_budget_exceeded() -> None:
    manager = QuotaManager()
    manager.register_tenant("tenant-a", budget_tokens=5, window_seconds=60)

    first = manager.check_admission(
        tenant_id="tenant-a",
        request_id="req-1",
        requested_tokens=3,
        now_sec=100,
    )
    second = manager.check_admission(
        tenant_id="tenant-a",
        request_id="req-2",
        requested_tokens=3,
        now_sec=101,
    )

    assert first.allowed is True
    assert second.allowed is False
    assert second.used_tokens == 3
    assert second.remaining_tokens == 2
    assert second.reason == "Budget exceeded"


def test_quota_manager_deduplicates_request_id() -> None:
    manager = QuotaManager()
    manager.register_tenant("tenant-a", budget_tokens=10, window_seconds=60)

    first = manager.check_admission(
        tenant_id="tenant-a",
        request_id="req-1",
        requested_tokens=4,
        now_sec=100,
    )
    duplicate = manager.check_admission(
        tenant_id="tenant-a",
        request_id="req-1",
        requested_tokens=4,
        now_sec=100,
    )

    assert first.allowed is True
    assert duplicate.allowed is True
    assert duplicate.deduplicated is True
    assert duplicate.used_tokens == 4
    assert duplicate.remaining_tokens == 6


def test_quota_manager_expires_usage_after_window() -> None:
    manager = QuotaManager()
    manager.register_tenant("tenant-a", budget_tokens=5, window_seconds=3)

    first = manager.check_admission(
        tenant_id="tenant-a",
        request_id="req-1",
        requested_tokens=5,
        now_sec=10,
    )
    second = manager.check_admission(
        tenant_id="tenant-a",
        request_id="req-2",
        requested_tokens=5,
        now_sec=13,
    )

    assert first.allowed is True
    assert second.allowed is True
    assert second.used_tokens == 5
    assert second.remaining_tokens == 0
