"""Member module routers — member registration, login and profile.

Members have their own login, separate from creators. Their access tokens
carry role=member and are rejected by creator-only endpoints.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.api.dependencies import get_current_member
from app.modules.auth.schemas import BaseSuccessResponse
from app.modules.member.dependencies import get_member_service
from app.modules.member.schemas import (
    MemberRegisterRequest,
    MemberRequestOTPRequest,
    MemberRequestOTPResponse,
    MemberResponse,
    MemberTokenResponse,
    MemberVerifyOTPRequest,
)
from app.modules.member.services import MemberService

router = APIRouter(tags=["members"])


@router.get("/api/v1/communities/{id}/members")
async def get_members(id: str):
    return []


@router.post(
    "/api/v1/members/register",
    response_model=BaseSuccessResponse[MemberResponse],
    status_code=201,
    summary="Register a Member",
    description=(
        "Creates a member account. Email and phone (with country code) must be unique. "
        "After logging in, the member connects Telegram before subscribing to any plan."
    ),
)
async def register_member(
    request: MemberRegisterRequest,
    service: MemberService = Depends(get_member_service),
) -> BaseSuccessResponse[MemberResponse]:
    return BaseSuccessResponse(data=await service.register(request))


@router.post(
    "/api/v1/members/request-otp",
    response_model=BaseSuccessResponse[MemberRequestOTPResponse],
    summary="Request a Member Login OTP",
)
async def request_member_otp(
    request: MemberRequestOTPRequest,
    service: MemberService = Depends(get_member_service),
) -> BaseSuccessResponse[MemberRequestOTPResponse]:
    return BaseSuccessResponse(data=await service.request_otp(request))


@router.post(
    "/api/v1/members/verify-otp",
    response_model=BaseSuccessResponse[MemberTokenResponse],
    summary="Verify OTP & Login (member)",
)
async def verify_member_otp(
    request: MemberVerifyOTPRequest,
    service: MemberService = Depends(get_member_service),
) -> BaseSuccessResponse[MemberTokenResponse]:
    return BaseSuccessResponse(data=await service.verify_otp(request))


@router.get(
    "/api/v1/members/me",
    response_model=BaseSuccessResponse[MemberResponse],
    summary="Current Member",
)
async def get_me(
    member_id: uuid.UUID = Depends(get_current_member),
    service: MemberService = Depends(get_member_service),
) -> BaseSuccessResponse[MemberResponse]:
    return BaseSuccessResponse(data=await service.get_me(member_id))
