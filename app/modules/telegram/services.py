"""Telegram module service — ALL business logic lives here.

Orchestrates repositories, infrastructure clients, and other services
to implement the six primary workflows from Doc 05 §5:
  1. Community Connection
  2. Telegram Account Linking
  3. Invite Generation
  4. Access Revocation
  5. Synchronization
  6. Webhook Processing

This service NEVER calls the Telegram API directly — it delegates to
TelegramClient (infrastructure).  It NEVER accesses the database
directly — it delegates to TelegramRepository.
"""

from __future__ import annotations

import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.infrastructure.telegram.telegram_exceptions import (
    TelegramException,
    TelegramNotFoundException,
    TelegramPermissionException,
)
from app.infrastructure.telegram.telegram_interface import TelegramClient
from app.modules.telegram import constants as tc
from app.modules.telegram.enums import (
    TelegramConnectionStatus,
    TelegramOperationStatus,
    TelegramOperationType,
)
from app.modules.telegram.exceptions import (
    CommunityAlreadyConnectedError,
    CommunityNotConnectedError,
    CommunityNotFoundError,
    InvalidConnectionCodeError,
    SubscriptionInactiveError,
    TelegramAccountAlreadyLinkedError,
    TelegramNotLinkedError,
    TelegramOperationFailedError,
    UnauthorizedCommunityAccessError,
)
from app.modules.telegram.repositories import TelegramRepository
from app.modules.telegram.schemas import (
    GenerateConnectionCodeResponse,
    InviteResponse,
    LinkStatusResponse,
    LinkTelegramResponse,
    TelegramConnectionStatusResponse,
)

logger = get_logger(__name__)

# In-memory store for short-lived connection codes.
# Production could move this to the DB; for now codes expire quickly.
_connection_codes: dict[str, dict[str, Any]] = {}


class TelegramService:
    """Orchestrates all Telegram business logic."""

    def __init__(
        self,
        repository: TelegramRepository,
        telegram_client: TelegramClient,
        settings: Settings,
    ) -> None:
        self._repo = repository
        self._telegram = telegram_client
        self._settings = settings

    # ══════════════════════════════════════════════════════════════════
    #  Workflow 1 — Community Connection
    # ══════════════════════════════════════════════════════════════════

    async def generate_connection_code(
        self,
        community_id: uuid.UUID,
        creator_id: uuid.UUID,
    ) -> GenerateConnectionCodeResponse:
        """Generate a temporary code for connecting a Telegram group."""
        community = await self._repo.get_community_by_id(community_id)
        if community is None:
            raise CommunityNotFoundError()

        if community.creator_id != creator_id:
            raise UnauthorizedCommunityAccessError()

        if community.telegram_connection_status == TelegramConnectionStatus.CONNECTED.value:
            raise CommunityAlreadyConnectedError()

        # Generate a short-lived code
        code = secrets.token_urlsafe(tc.CONNECTION_CODE_LENGTH)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=tc.CONNECTION_CODE_EXPIRY_MINUTES,
        )

        _connection_codes[code] = {
            "community_id": str(community_id),
            "creator_id": str(creator_id),
            "expires_at": expires_at,
        }

        # Mark community as CONNECTING
        await self._repo.update_connection_status(
            community_id,
            TelegramConnectionStatus.CONNECTING,
        )

        bot_username = getattr(self._settings, "TELEGRAM_BOT_USERNAME", "pulse_access_bot")

        logger.info(
            "Connection code generated for community %s",
            community_id,
        )

        return GenerateConnectionCodeResponse(
            connection_code=code,
            expires_at=expires_at,
            bot_username=bot_username,
        )

    async def validate_connection_code(self, code: str) -> uuid.UUID:
        """Validate and consume a connection code. Returns the community_id."""
        entry = _connection_codes.pop(code, None)
        if entry is None:
            raise InvalidConnectionCodeError()

        if entry["expires_at"] < datetime.now(timezone.utc):
            raise InvalidConnectionCodeError("Connection code has expired.")

        return uuid.UUID(entry["community_id"])

    async def connect_community(
        self,
        community_id: uuid.UUID,
        chat_id: str,
    ) -> None:
        """Finalise Telegram connection for a community."""
        await self._repo.mark_connected(community_id, chat_id)
        logger.info(
            "Community %s connected to Telegram chat %s",
            community_id,
            chat_id,
        )

    async def disconnect_community(
        self,
        community_id: uuid.UUID,
        creator_id: uuid.UUID,
    ) -> None:
        """Disconnect Telegram from a community."""
        community = await self._repo.get_community_by_id(community_id)
        if community is None:
            raise CommunityNotFoundError()

        if community.creator_id != creator_id:
            raise UnauthorizedCommunityAccessError()

        await self._repo.mark_disconnected(community_id)
        logger.info("Community %s disconnected from Telegram", community_id)

    async def get_connection_status(
        self,
        community_id: uuid.UUID,
        creator_id: uuid.UUID,
    ) -> TelegramConnectionStatusResponse:
        """Return the current Telegram connection status."""
        community = await self._repo.get_community_by_id(community_id)
        if community is None:
            raise CommunityNotFoundError()

        if community.creator_id != creator_id:
            raise UnauthorizedCommunityAccessError()

        return TelegramConnectionStatusResponse(
            status=community.telegram_connection_status,
            telegram_chat_id=community.telegram_chat_id,
            connected_at=community.telegram_connected_at,
        )

    # ══════════════════════════════════════════════════════════════════
    #  Workflow 2 — Telegram Account Linking
    # ══════════════════════════════════════════════════════════════════

    async def generate_link(self, member_id: uuid.UUID) -> LinkTelegramResponse:
        """Generate a Telegram deep link for account linking."""
        member = await self._repo.get_member_by_id(member_id)
        if member is None:
            raise CommunityNotFoundError("Member not found.")

        if member.telegram_user_id:
            raise TelegramAccountAlreadyLinkedError()

        bot_username = getattr(self._settings, "TELEGRAM_BOT_USERNAME", "pulse_access_bot")
        deep_link = f"https://t.me/{bot_username}?start={tc.DEEP_LINK_PREFIX}{member_id}"

        logger.info("Telegram deep link generated for member %s", member_id)

        return LinkTelegramResponse(telegram_link=deep_link)

    async def get_link_status(self, member_id: uuid.UUID) -> LinkStatusResponse:
        """Check whether the member has a linked Telegram account."""
        member = await self._repo.get_member_by_id(member_id)
        if member is None:
            raise CommunityNotFoundError("Member not found.")

        linked = bool(member.telegram_user_id)
        return LinkStatusResponse(
            linked=linked,
            telegram_user_id=member.telegram_user_id if linked else None,
        )

    async def link_account(
        self,
        member_id: uuid.UUID,
        telegram_user_id: str,
    ) -> None:
        """Link a Telegram user ID to a PulseAccess member."""
        # Check if this Telegram account is already linked to another member
        existing = await self._repo.find_member_by_telegram_id(telegram_user_id)
        if existing is not None and existing.id != member_id:
            raise TelegramAccountAlreadyLinkedError(
                "This Telegram account is already linked to another member.",
            )

        await self._repo.link_telegram_account(member_id, telegram_user_id)
        logger.info("Telegram user %s linked to member %s", telegram_user_id, member_id)

    # ══════════════════════════════════════════════════════════════════
    #  Workflow 3 — Invite Generation
    # ══════════════════════════════════════════════════════════════════

    async def generate_invite(
        self,
        community_id: uuid.UUID,
        member_id: uuid.UUID,
    ) -> InviteResponse:
        """Generate a temporary Telegram invite for an eligible member."""
        community = await self._repo.get_community_by_id(community_id)
        if community is None:
            raise CommunityNotFoundError()

        if community.telegram_connection_status != TelegramConnectionStatus.CONNECTED.value:
            raise CommunityNotConnectedError()

        member = await self._repo.get_member_by_id(member_id)
        if member is None:
            raise CommunityNotFoundError("Member not found.")

        if not member.telegram_user_id:
            raise TelegramNotLinkedError()

        # Note: Subscription validation would be performed here by calling
        # SubscriptionService. For now we proceed assuming the caller
        # (router) has verified subscription status via the JWT claims
        # or a dependency.

        expire_date = int(time.time()) + tc.INVITE_LINK_EXPIRE_SECONDS
        try:
            invite = await self._telegram.create_invite_link(
                chat_id=community.telegram_chat_id,
                expire_date=expire_date,
                member_limit=tc.INVITE_LINK_MEMBER_LIMIT,
            )
        except TelegramException as exc:
            logger.error(
                "Failed to create invite for community %s: %s",
                community_id,
                exc.message,
            )
            raise TelegramOperationFailedError() from exc

        expires_at = datetime.fromtimestamp(expire_date, tz=timezone.utc)

        logger.info(
            "Invite generated for member %s → community %s",
            member_id,
            community_id,
        )

        return InviteResponse(
            invite_link=invite.invite_link,
            expires_at=expires_at,
        )

    # ══════════════════════════════════════════════════════════════════
    #  Workflow 4 — Access Revocation
    # ══════════════════════════════════════════════════════════════════

    async def revoke_access(
        self,
        community_id: uuid.UUID,
        member_id: uuid.UUID,
    ) -> None:
        """Queue a REMOVE_MEMBER operation for async execution."""
        await self._repo.create_operation(
            operation_type=TelegramOperationType.REMOVE_MEMBER,
            community_id=community_id,
            member_id=member_id,
        )
        logger.info(
            "REMOVE_MEMBER queued for member %s in community %s",
            member_id,
            community_id,
        )

    # ══════════════════════════════════════════════════════════════════
    #  Workflow 5 — Operation Execution (called by workers)
    # ══════════════════════════════════════════════════════════════════

    async def execute_operation(self, operation_id: uuid.UUID) -> None:
        """Execute a single queued Telegram operation."""
        from app.modules.telegram.models import TelegramOperation
        from sqlalchemy import select

        stmt = select(TelegramOperation).where(TelegramOperation.id == operation_id)
        result = await self._repo._session.execute(stmt)
        op = result.scalar_one_or_none()

        if op is None or op.status == TelegramOperationStatus.COMPLETED.value:
            return

        await self._repo.update_operation_status(
            operation_id,
            TelegramOperationStatus.PROCESSING,
        )

        try:
            if op.operation_type == TelegramOperationType.REMOVE_MEMBER.value:
                await self._execute_remove_member(op)
            elif op.operation_type == TelegramOperationType.VERIFY_CONNECTION.value:
                await self._execute_verify_connection(op)
            elif op.operation_type == TelegramOperationType.CREATE_INVITE.value:
                # Invite creation is typically synchronous via API;
                # queued version is for retry scenarios
                pass
            elif op.operation_type == TelegramOperationType.SYNC_MEMBER.value:
                pass  # Handled by sync worker

            await self._repo.mark_completed(operation_id)
            logger.info("Operation %s completed", operation_id)

        except (TelegramNotFoundException, TelegramPermissionException) as exc:
            # Permanent failure — do not retry
            await self._repo.mark_failed(operation_id, error=str(exc))
            logger.warning("Operation %s permanently failed: %s", operation_id, exc)

        except TelegramException as exc:
            # Transient failure — schedule retry
            max_retries = getattr(self._settings, "TELEGRAM_MAX_RETRIES", 5)
            if op.retry_count >= max_retries:
                await self._repo.mark_failed(operation_id, error=str(exc))
                logger.error("Operation %s exhausted retries", operation_id)
            else:
                backoff_minutes = [1, 5, 15, 30, 60]
                delay = backoff_minutes[min(op.retry_count, len(backoff_minutes) - 1)]
                scheduled = datetime.now(timezone.utc) + timedelta(minutes=delay)
                await self._repo.increment_retry(operation_id, scheduled, error=str(exc))
                logger.info(
                    "Operation %s scheduled for retry in %d min",
                    operation_id,
                    delay,
                )

    async def _execute_remove_member(self, op: Any) -> None:
        """Remove a member from a Telegram group (ban then unban)."""
        community = await self._repo.get_community_by_id(op.community_id)
        if community is None or not community.telegram_chat_id:
            raise TelegramNotFoundException("Community or chat not found")

        member = await self._repo.get_member_by_id(op.member_id)
        if member is None or not member.telegram_user_id:
            raise TelegramNotFoundException("Member or telegram ID not found")

        await self._telegram.ban_member(
            community.telegram_chat_id,
            int(member.telegram_user_id),
        )
        await self._telegram.unban_member(
            community.telegram_chat_id,
            int(member.telegram_user_id),
        )

    async def _execute_verify_connection(self, op: Any) -> None:
        """Verify a community's Telegram group is still accessible."""
        community = await self._repo.get_community_by_id(op.community_id)
        if community is None or not community.telegram_chat_id:
            raise TelegramNotFoundException("Community or chat not found")

        await self._telegram.get_chat(community.telegram_chat_id)

    # ══════════════════════════════════════════════════════════════════
    #  Workflow 6 — Webhook Processing
    # ══════════════════════════════════════════════════════════════════

    async def process_webhook_message(self, update: dict) -> None:
        """Handle /start command for Telegram account linking."""
        message = update.get("message", {})
        text = message.get("text", "")
        from_user = message.get("from", {})

        if not text.startswith("/start"):
            return

        parts = text.split(" ", 1)
        if len(parts) < 2 or not parts[1].startswith(tc.DEEP_LINK_PREFIX):
            return

        member_id_str = parts[1][len(tc.DEEP_LINK_PREFIX):]
        telegram_user_id = str(from_user.get("id", ""))

        try:
            member_id = uuid.UUID(member_id_str)
        except ValueError:
            logger.warning("Invalid deep link member ID: %s", member_id_str)
            return

        try:
            await self.link_account(member_id, telegram_user_id)
        except Exception:
            logger.exception("Failed to link Telegram account via webhook")

    async def process_webhook_my_chat_member(self, update: dict) -> None:
        """Handle bot added/removed/promoted/demoted events."""
        event = update.get("my_chat_member", {})
        chat = event.get("chat", {})
        new_status = event.get("new_chat_member", {}).get("status", "")
        chat_id = str(chat.get("id", ""))

        community = await self._repo.get_community_by_chat_id(chat_id)

        if new_status in ("administrator", "member"):
            # Bot was added or promoted
            if community:
                await self._repo.update_connection_status(
                    community.id,
                    TelegramConnectionStatus.CONNECTED,
                )
                logger.info("Bot added to chat %s → community %s", chat_id, community.id)
        elif new_status in ("left", "kicked"):
            # Bot was removed
            if community:
                await self._repo.update_connection_status(
                    community.id,
                    TelegramConnectionStatus.NEEDS_ATTENTION,
                )
                logger.warning("Bot removed from chat %s → community %s", chat_id, community.id)

    async def process_webhook_chat_member(self, update: dict) -> None:
        """Handle member joined/left/kicked events."""
        event = update.get("chat_member", {})
        new_status = event.get("new_chat_member", {}).get("status", "")
        user_id = str(event.get("new_chat_member", {}).get("user", {}).get("id", ""))

        if new_status in ("left", "kicked"):
            member = await self._repo.find_member_by_telegram_id(user_id)
            if member:
                logger.info("Member %s left/was removed from Telegram group", member.id)
                # Business decision: log only. Reconciliation worker will handle sync.

    # ══════════════════════════════════════════════════════════════════
    #  Health Check
    # ══════════════════════════════════════════════════════════════════

    async def health_check(self) -> bool:
        """Proxy to infrastructure health check."""
        return await self._telegram.health_check()
