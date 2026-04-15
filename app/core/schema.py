from pydantic import BaseModel, Field

class TenantConfig(BaseModel):
    tenant_id: str
    budget_tokens: int
    window_seconds: int
    # created_at: int
    # updated_at: int
    is_active: bool = True
    
class ErrorResponse(BaseModel):
    error_code: str 
    message: str
    tenant_id: str | None = None
    retry_after: int | None = None

class RegisterTenantRequest(BaseModel):
    tenant_id: str = Field(min_length=1)
    budget_tokens: int = Field(gt=0)
    window_seconds: int = Field(default=60, gt=0)


class QuotaCheckRequest(BaseModel):
    tenant_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    requested_tokens: int = Field(gt=0)
    now_sec: int | None = None


class QuotaCheckResponse(BaseModel):
    tenant_id: str
    request_id: str
    allowed: bool
    deduplicated: bool
    used_tokens: int
    remaining_tokens: int
    budget_tokens: int
    window_seconds: int
    reason: str | None = None


class TenantConfigResponse(BaseModel):
    tenant_id: str
    budget_tokens: int
    window_seconds: int


class HealthResponse(BaseModel):
    status: str