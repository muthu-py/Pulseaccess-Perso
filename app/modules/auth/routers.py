import uuid

from fastapi import APIRouter, Depends, Request, Response

from app.api.dependencies import get_auth_service, get_current_creator
from app.modules.auth.schemas import (
    BaseSuccessResponse,
    CreatorResponse,
    LogoutResponse,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
    RequestOTPRequest,
    RequestOTPResponse,
    UpdatePhoneRequest,
    VerifyOTPRequest,
    VerifyOTPResponse,
)
from app.modules.auth.services import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=BaseSuccessResponse[RegisterResponse],
    status_code=201,
    summary="Register a new Creator",
    description=(
        "Creates a new creator account in the system.\n\n"
        "**Validation:**\n"
        "- Email and username must be globally unique.\n"
        "- Username must be at least 3 characters long.\n"
        "- Email must be a valid email format."
    ),
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
    summary="Request a Login OTP",
    description=(
        "Requests a 6-digit one-time passcode (OTP) to be sent via email.\n\n"
        "To prevent account enumeration attacks, this endpoint will always return "
        "a generic success response, even if the provided email or username does not exist."
    ),
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
    summary="Verify OTP & Login",
    description=(
        "Verifies the OTP sent to the user's email.\n\n"
        "**Security Features:**\n"
        "- Limited to 5 attempts to prevent brute-force attacks.\n"
        "- OTPs expire after 5 minutes.\n"
        "- On success, the access token is returned in the JSON payload, "
        "while the refresh token is securely set in an HttpOnly, SameSite=Lax cookie."
    ),
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
    summary="Refresh Access Token",
    description=(
        "Issues a new access token and rotates the refresh token.\n\n"
        "This endpoint reads the HttpOnly refresh cookie. If valid, it revokes the old "
        "refresh token, generates a new pair, and updates the HttpOnly cookie."
    ),
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
    summary="Logout & Revoke Session",
    description=(
        "Logs the user out by revoking their current session in the database and clearing "
        "the HttpOnly refresh cookie."
    ),
)
async def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> BaseSuccessResponse[LogoutResponse]:
    """Logout by revoking the refresh token and clearing the cookie."""
    result = await auth_service.logout(request, response)
    return BaseSuccessResponse(data=result)


@router.put(
    "/phone",
    response_model=BaseSuccessResponse[CreatorResponse],
    summary="Set Phone Number",
    description=(
        "Sets the authenticated creator's phone number (with country code). "
        "A phone number is required before connecting Telegram."
    ),
)
async def update_phone(
    request: UpdatePhoneRequest,
    creator_id: uuid.UUID = Depends(get_current_creator),
    auth_service: AuthService = Depends(get_auth_service),
) -> BaseSuccessResponse[CreatorResponse]:
    """Set or change the creator's phone number."""
    result = await auth_service.update_phone(creator_id, request)
    return BaseSuccessResponse(data=result)


@router.get(
    "/me",
    response_model=BaseSuccessResponse[CreatorResponse],
    summary="Current Creator",
    description="Returns the logged-in creator's profile.",
)
async def get_me(
    creator_id: uuid.UUID = Depends(get_current_creator),
    auth_service: AuthService = Depends(get_auth_service),
) -> BaseSuccessResponse[CreatorResponse]:
    """Return the authenticated creator."""
    result = await auth_service.get_me(creator_id)
    return BaseSuccessResponse(data=result)
