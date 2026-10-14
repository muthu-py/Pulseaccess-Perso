"""Telegram module routers — REST API + Webhook endpoint.

Defines all Creator, Member, and Webhook endpoints (Doc 06, Doc 07).
Routers are thin: validate → authenticate → authorize → delegate to service.

Auth guard:
  - Creator endpoints: Bearer JWT via get_current_creator
  - Member endpoints: Bearer JWT via get_current_member (member ID from token)
  - Webhook endpoint: TELEGRAM_WEBHOOK_SECRET header verification only
"""

from __future__ import annotations

import hmac
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_creator, get_current_member
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.infrastructure.database.session import get_db
from app.modules.auth.schemas import BaseSuccessResponse
from app.modules.telegram import constants as tc
from app.modules.telegram.dependencies import get_telegram_service
from app.modules.telegram.schemas import (
    InviteResponse,
    TelegramConnectionStatusResponse,
)
from app.modules.telegram.services import TelegramService
from app.modules.telegram_connect.dependencies import get_telegram_connect_service
from app.modules.telegram_connect.services import TelegramConnectService

logger = get_logger(__name__)

router = APIRouter(tags=["telegram"])


# ======================================================================
# Creator APIs — /api/v1/telegram/communities/...
# JWT Bearer required: creator must own the community.
# ======================================================================

@router.get(
    "/api/v1/telegram/communities/{community_id}/status",
    response_model=BaseSuccessResponse[TelegramConnectionStatusResponse],
    summary="Get Connection Status",
    description=(
        "Returns the current Telegram connection status for a community. "
        "Requires a valid Bearer access token. Creator must own the community."
    ),
)
async def get_connection_status(
    community_id: uuid.UUID,
    creator_id: uuid.UUID = Depends(get_current_creator),
    service: TelegramService = Depends(get_telegram_service),
) -> BaseSuccessResponse[TelegramConnectionStatusResponse]:
    """Get the Telegram connection status for a community."""
    result = await service.get_connection_status(community_id, creator_id)
    return BaseSuccessResponse(data=result)


@router.delete(
    "/api/v1/telegram/communities/{community_id}",
    status_code=204,
    response_model=None,
    summary="Disconnect Community",
    description=(
        "Disconnects Telegram from the community. Does not delete business data. "
        "Requires a valid Bearer access token. Creator must own the community."
    ),
)
async def disconnect_community(
    community_id: uuid.UUID,
    creator_id: uuid.UUID = Depends(get_current_creator),
    service: TelegramService = Depends(get_telegram_service),
) -> None:
    """Disconnect Telegram from a community."""
    await service.disconnect_community(community_id, creator_id)


# ======================================================================
# Member APIs
# JWT Bearer required (member login): the sub claim is the member_id.
# Account linking lives in app.modules.telegram_connect.
# ======================================================================

@router.post(
    "/api/v1/telegram/communities/{community_id}/invite",
    response_model=BaseSuccessResponse[InviteResponse],
    summary="Generate Telegram Invite",
    description=(
        "Creates a temporary Telegram invite link for the authenticated member. "
        "Requires an active subscription and a linked Telegram account. "
        "Requires a valid Bearer access token."
    ),
)
async def generate_invite(
    community_id: uuid.UUID,
    member_id: uuid.UUID = Depends(get_current_member),
    service: TelegramService = Depends(get_telegram_service),
) -> BaseSuccessResponse[InviteResponse]:
    """Generate a Telegram invite for an eligible member."""
    result = await service.generate_invite(community_id, member_id)
    return BaseSuccessResponse(data=result)


# ======================================================================
# Webhook API — /api/v1/webhooks/telegram
# No JWT — verified exclusively via TELEGRAM_WEBHOOK_SECRET header.
# Secret check occurs BEFORE any JSON parsing or business processing.
# ======================================================================

@router.post(
    tc.WEBHOOK_PATH,
    status_code=200,
    summary="Telegram Webhook",
    description=(
        "Receives Telegram Bot updates. Verified via the "
        "`X-Telegram-Bot-Api-Secret-Token` header before processing."
    ),
)
async def telegram_webhook(
    request: Request,
    service: TelegramService = Depends(get_telegram_service),
    connect_service: TelegramConnectService = Depends(get_telegram_connect_service),
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_db),
    x_telegram_bot_api_secret_token: str | None = Header(None),
) -> dict:
    """Process incoming Telegram webhook updates."""

    # ── Verify webhook secret FIRST (Doc 10 §8) ─────────────────────
    webhook_secret = settings.TELEGRAM_WEBHOOK_SECRET

    if not webhook_secret or not hmac.compare_digest(
        webhook_secret, x_telegram_bot_api_secret_token or ""
    ):
        logger.warning("Webhook secret mismatch — rejecting request")
        raise HTTPException(status_code=401, detail="Unauthorized")

    # ── Parse payload ────────────────────────────────────────────────
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed JSON payload")

    update_id = body.get("update_id")
    if not isinstance(update_id, int):
        raise HTTPException(status_code=400, detail="Missing update_id")

    # ── De-duplicate: Telegram may deliver the same update twice ─────
    if await service.is_update_processed(update_id):
        logger.debug("Webhook update %s already processed, skipping", update_id)
        return {"ok": True}

    # ── Dispatch to appropriate handler (Doc 07 §8-11) ───────────────
    try:
        if "message" in body:
            message = body["message"]
            if message.get("chat", {}).get("type") == "private":
                logger.debug("Webhook update %s: private message", update_id)
                await connect_service.handle_private_message(message)
            else:
                logger.debug("Webhook update %s: group message", update_id)
                await service.process_webhook_group_message(message)
        elif "my_chat_member" in body:
            logger.debug("Webhook update %s: my_chat_member", update_id)
            await service.process_webhook_my_chat_member(body)
        elif "chat_member" in body:
            logger.debug("Webhook update %s: chat_member", update_id)
            await service.process_webhook_chat_member(body)
        else:
            # Unsupported update type — log at DEBUG and ignore (Doc 07 §12)
            logger.debug("Webhook update %s: unsupported type, ignoring", update_id)
    except Exception:
        logger.exception("Error processing webhook update %s", update_id)
        # Drop the handler's partial writes; still record the update below.
        await session.rollback()
        # Always return 200 to prevent Telegram infinite retry (Doc 07 §16)

    await service.record_update(update_id)
    return {"ok": True}
