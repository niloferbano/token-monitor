from dataclasses import dataclass
from typing import OrderedDict

from app.core.quota import SlidingWindowState


@dataclass
class QuotaDecision:
    tenant_id: str
    request_id: str
    allowed: bool
    deduplicated: bool
    used_tokens: int
    remaining_tokens: int
    budget_tokens: int
    window_seconds: int
    reason: str | None = None


class QuotaManager:
    def __init__(self, max_history = 10000) -> None:
        self.tenants: dict[str, SlidingWindowState] = {}
        self.seen_requests: OrderedDict[tuple[str, str], QuotaDecision] = OrderedDict()
        self.max_history = max_history

    def register_tenant(
        self,
        tenant_id: str,
        budget_tokens: int,
        window_seconds: int = 60,
    ) -> None:
        if tenant_id in self.tenants:
            raise ValueError(f"Tenant already registered: {tenant_id}")

        self.tenants[tenant_id] = SlidingWindowState(
            budget_tokens=budget_tokens,
            window_seconds=window_seconds,
        )

    def check_admission(
        self,
        tenant_id: str,
        request_id: str,
        requested_tokens: int,
        now_sec: int,
    ) -> QuotaDecision:
        if tenant_id not in self.tenants:
            return self._build_rejection(
                tenant_id=tenant_id,
                request_id=request_id,
                reason="Tenant not found",
            )

        dedupe_key = (tenant_id, request_id)
        if dedupe_key in self.seen_requests:
            previous = self.seen_requests[dedupe_key]
            return QuotaDecision(
                tenant_id=previous.tenant_id,
                request_id=previous.request_id,
                allowed=previous.allowed,
                deduplicated=True,
                used_tokens=previous.used_tokens,
                remaining_tokens=previous.remaining_tokens,
                budget_tokens=previous.budget_tokens,
                window_seconds=previous.window_seconds,
                reason=previous.reason,
            )

        state = self.tenants[tenant_id]
        allowed, used, remaining = state.allow_and_reserve(now_sec, requested_tokens)

        decision = QuotaDecision(
            tenant_id=tenant_id,
            request_id=request_id,
            allowed=allowed,
            deduplicated=False,
            used_tokens=used,
            remaining_tokens=remaining,
            budget_tokens=state.budget_tokens,
            window_seconds=state.window_seconds,
            reason=None if allowed else "Budget exceeded",
        )

        self.seen_requests[dedupe_key] = decision
        self.seen_requests.move_to_end(dedupe_key)

        if len(self.seen_requests) > self.max_history:
            self.seen_requests.popitem(last=False)
        return decision

    def _build_rejection(self, tenant_id: str, request_id: str, reason: str) -> QuotaDecision:
        return QuotaDecision(
            tenant_id=tenant_id,
            request_id=request_id,
            allowed=False,
            deduplicated=False,
            used_tokens=0,
            remaining_tokens=0,
            budget_tokens=0,
            window_seconds=0,
            reason=reason,
        )