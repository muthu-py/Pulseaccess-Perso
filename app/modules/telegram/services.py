"""Telegram module service — ALL business logic lives here.

Orchestrates repositories, infrastructure clients, and other services
to implement the six primary workflows from Doc 05 §5:
  1. Community Connection
  2. Telegram Account Linking (moved to app.modules.telegram_connect)
  3. Invite Generation
  4. Access Revocation
  5. Synchronization
  6. Webhook Processing

This service NEVER calls the Telegram API directly — it delegates to
TelegramClient (infrastructure).  It NEVER accesses the database
directly — it delegates to TelegramRepository.
"""

from __future__ import annotations

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
from app.infrastructure.telegram.telegram_models import TelegramChatMember
from app.modules.telegram import constants as tc
from app.modules.telegram.enums import (
    TelegramConnectionStatus,
    TelegramOperationStatus,
    TelegramOperationType,
)
from app.modules.telegram.exceptions import (
    CommunityNotConnectedError,
    CommunityNotFoundError,
    SubscriptionInactiveError,
    TelegramNotLinkedError,
    TelegramOperationFailedError,
    UnauthorizedCommunityAccessError,
)
from app.modules.telegram.repositories import TelegramRepository
from app.modules.telegram.schemas import (
    InviteResponse,
    TelegramConnectionStatusResponse,
)

logger = get_logger(__name__)



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
    #  Lives in app.modules.telegram_connect (shared by creators and members).
    # ══════════════════════════════════════════════════════════════════

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

        if await self._repo.get_member_telegram_id(member_id) is None:
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

        telegram_user_id = await self._repo.get_member_telegram_id(op.member_id)
        if telegram_user_id is None:
            raise TelegramNotFoundException("Member or telegram ID not found")

        await self._telegram.ban_member(
            community.telegram_chat_id,
            int(telegram_user_id),
        )
        await self._telegram.unban_member(
            community.telegram_chat_id,
            int(telegram_user_id),
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

    async def process_webhook_my_chat_member(self, update: dict) -> None:
        """Bot added / promoted / demoted / removed in a group or channel.

        Connection rule: the bot must be added by a creator (matched through
        their verified Telegram account), and that creator must have exactly
        one active community not yet linked to a chat. That community gets
        this chat. The bot's real admin rights decide CONNECTED vs
        NEEDS_ATTENTION.
        """
        event = update.get("my_chat_member", {})
        chat = event.get("chat", {})
        if chat.get("type") not in tc.GROUP_CHAT_TYPES:
            return

        chat_id = str(chat.get("id", ""))
        title = chat.get("title") or chat_id
        actor_id = str(event.get("from", {}).get("id", ""))
        new_member = event.get("new_chat_member", {})
        new_status = new_member.get("status", "")
        bot_user_id = new_member.get("user", {}).get("id")

        community = await self._repo.get_community_by_chat_id(chat_id)

        if new_status in tc.BOT_GONE_STATUSES:
            if community is not None:
                await self._repo.update_connection_status(
                    community.id, TelegramConnectionStatus.NEEDS_ATTENTION,
                )
                logger.warning("Bot removed from chat %s → community %s", chat_id, community.id)
                await self._notify_creator(
                    community.creator_id,
                    tc.MSG_GROUP_BOT_REMOVED.format(title=title, community=community.name),
                )
            return

        if new_status not in tc.BOT_PRESENT_STATUSES:
            return

        if community is None:
            community = await self._link_pending_community(chat_id, title, actor_id)
            if community is None:
                return

        await self._refresh_connection(community, chat_id, title, bot_user_id, new_member)

    async def _link_pending_community(self, chat_id: str, title: str, actor_id: str):
        """Attach this chat to the actor's single pending community, if any."""
        creator_id = await self._repo.get_creator_id_by_telegram_user(actor_id)
        if creator_id is None:
            logger.info(
                "Bot added to chat %s by Telegram user %s who is not a connected creator; ignoring",
                chat_id, actor_id,
            )
            return None

        pending = await self._repo.get_unlinked_communities(creator_id)
        if len(pending) != 1:
            logger.info(
                "Bot added to chat %s by creator %s with %d pending communities; ignoring",
                chat_id, creator_id, len(pending),
            )
            if not pending:
                await self._send_private(actor_id, tc.MSG_GROUP_NO_PENDING.format(title=title))
            return None

        community = pending[0]
        await self._repo.save_chat_id(community.id, chat_id)
        community.telegram_chat_id = chat_id
        logger.info("Chat %s linked to community %s", chat_id, community.id)
        return community

    async def _refresh_connection(
        self,
        community: Any,
        chat_id: str,
        title: str,
        bot_user_id: int | None,
        reported_member: dict,
    ) -> None:
        """Set CONNECTED / NEEDS_ATTENTION from the bot's actual rights."""
        member = await self._fetch_bot_member(chat_id, bot_user_id, reported_member)
        has_rights = (
            member is not None
            and member.status == "administrator"
            and member.can_invite_users
            and member.can_restrict_members
        )
        previous = community.telegram_connection_status

        if has_rights:
            if previous != TelegramConnectionStatus.CONNECTED.value:
                await self._repo.mark_connected(community.id, chat_id)
                community.telegram_connection_status = TelegramConnectionStatus.CONNECTED.value
                logger.info("Community %s CONNECTED to chat %s", community.id, chat_id)
                await self._notify_creator(
                    community.creator_id,
                    tc.MSG_GROUP_CONNECTED.format(title=title, community=community.name),
                )
            return

        if previous != TelegramConnectionStatus.NEEDS_ATTENTION.value:
            await self._repo.update_connection_status(
                community.id, TelegramConnectionStatus.NEEDS_ATTENTION,
            )
            community.telegram_connection_status = TelegramConnectionStatus.NEEDS_ATTENTION.value
            logger.info(
                "Community %s NEEDS_ATTENTION: bot lacks admin rights in chat %s",
                community.id, chat_id,
            )
            await self._notify_creator(
                community.creator_id,
                tc.MSG_GROUP_NEEDS_ADMIN.format(title=title, community=community.name),
            )

    async def _fetch_bot_member(
        self,
        chat_id: str,
        bot_user_id: int | None,
        reported_member: dict,
    ) -> TelegramChatMember | None:
        """Ask Telegram for the bot's current rights; fall back to the update's copy."""
        if bot_user_id is None:
            bot_user_id = (await self._telegram.get_me()).id
        try:
            return await self._telegram.get_chat_member(chat_id, int(bot_user_id))
        except TelegramException:
            logger.warning(
                "getChatMember failed for chat %s; using rights from the update", chat_id,
            )
            try:
                return TelegramChatMember.model_validate(reported_member)
            except ValueError:
                return None

    async def process_webhook_group_message(self, message: dict) -> None:
        """Group upgraded to supergroup: Telegram moves it to a new chat id."""
        new_chat_id = message.get("migrate_to_chat_id")
        if new_chat_id is None:
            return

        old_chat_id = str(message.get("chat", {}).get("id", ""))
        community = await self._repo.replace_chat_id(old_chat_id, str(new_chat_id))
        if community is None:
            return
        logger.info(
            "Community %s chat migrated %s → %s", community.id, old_chat_id, new_chat_id,
        )
        # Rights may have changed with the upgrade; re-check on the new chat.
        await self._refresh_connection(
            community,
            str(new_chat_id),
            message.get("chat", {}).get("title") or str(new_chat_id),
            None,
            {},
        )

    async def _notify_creator(self, creator_id: uuid.UUID, text: str) -> None:
        telegram_user_id = await self._repo.get_creator_telegram_user_id(creator_id)
        if telegram_user_id:
            await self._send_private(telegram_user_id, text)

    async def _send_private(self, telegram_user_id: str, text: str) -> None:
        """Best effort: the connection result stands even if the message fails."""
        try:
            await self._telegram.send_message(int(telegram_user_id), text)
        except (TelegramException, ValueError):
            logger.exception("Failed to message Telegram user %s", telegram_user_id)

    # ── Webhook de-duplication ───────────────────────────────────────

    async def is_update_processed(self, update_id: int) -> bool:
        return await self._repo.is_update_processed(update_id)

    async def record_update(self, update_id: int) -> None:
        await self._repo.record_update(update_id)

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
