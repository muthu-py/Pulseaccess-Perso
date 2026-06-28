from fastapi import APIRouter, Depends, Request, Response

from app.api.dependencies import get_auth_service
from app.modules.auth.schemas import (
    BaseSuccessResponse,
    LogoutResponse,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
    RequestOTPRequest,
    RequestOTPResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
)
from app.modules.auth.services import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=BaseSuccessResponse[RegisterResponse],
    status_code=201,
)
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> BaseSuccessResponse[RegisterResponse]:
    """Register a new creator account."""
    result = await auth_service.register(request)
    return BaseSuccessResponse(data=result)


@router.post(
    "/request-otp",
    response_model=BaseSuccessResponse[RequestOTPResponse],
)
async def request_otp(
    request: RequestOTPRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> BaseSuccessResponse[RequestOTPResponse]:
    """Request a one-time login code sent to your email."""
    result = await auth_service.request_otp(request)
    return BaseSuccessResponse(data=result)


@router.post(
    "/verify-otp",
    response_model=BaseSuccessResponse[VerifyOTPResponse],
)
async def verify_otp(
    request_body: VerifyOTPRequest,
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> BaseSuccessResponse[VerifyOTPResponse]:
    """Verify the OTP and receive an access token. Refresh token set as HttpOnly cookie."""
    result = await auth_service.verify_otp(request_body, response)
    return BaseSuccessResponse(data=result)


@router.post(
    "/refresh",
    response_model=BaseSuccessResponse[RefreshResponse],
)
async def refresh(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> BaseSuccessResponse[RefreshResponse]:
    """Refresh the access token using the HttpOnly refresh cookie."""
    result = await auth_service.refresh(request, response)
    return BaseSuccessResponse(data=result)


@router.post(
    "/logout",
    response_model=BaseSuccessResponse[LogoutResponse],
)
async def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> BaseSuccessResponse[LogoutResponse]:
    """Logout by revoking the refresh token and clearing the cookie."""
    result = await auth_service.logout(request, response)
    return BaseSuccessResponse(data=result)
