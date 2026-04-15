import time

from fastapi import APIRouter, HTTPException

from app.core.schema import (
    HealthResponse,
    QuotaCheckRequest,
    QuotaCheckResponse,
    RegisterTenantRequest,
    TenantConfigResponse,
)
from app.core.service import QuotaManager

quota_manager = QuotaManager()
router = APIRouter(prefix="/quota")


@router.post("/check", response_model=QuotaCheckResponse)
async def check_quota(request: QuotaCheckRequest) -> QuotaCheckResponse:
    now_sec = request.now_sec if request.now_sec is not None else int(time.time())

    decision = quota_manager.check_admission(
        tenant_id=request.tenant_id,
        request_id=request.request_id,
        requested_tokens=request.requested_tokens,
        now_sec=now_sec,
    )

    if not decision.allowed and decision.reason == "Tenant not found":
        raise HTTPException(status_code=404, detail=decision.reason)

    if not decision.allowed and decision.reason == "Budget exceeded":
        raise HTTPException(status_code=429, detail=decision.reason)

    return QuotaCheckResponse(
        tenant_id=decision.tenant_id,
        request_id=decision.request_id,
        allowed=decision.allowed,
        deduplicated=decision.deduplicated,
        used_tokens=decision.used_tokens,
        remaining_tokens=decision.remaining_tokens,
        budget_tokens=decision.budget_tokens,
        window_seconds=decision.window_seconds,
        reason=decision.reason,
    )


@router.post("/tenants", response_model=TenantConfigResponse, status_code=201)
async def register_tenant(request: RegisterTenantRequest) -> TenantConfigResponse:
    try:
        quota_manager.register_tenant(
            tenant_id=request.tenant_id,
            budget_tokens=request.budget_tokens,
            window_seconds=request.window_seconds,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return TenantConfigResponse(
        tenant_id=request.tenant_id,
        budget_tokens=request.budget_tokens,
        window_seconds=request.window_seconds,
    )


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")