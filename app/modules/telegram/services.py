"""Telegram module service — ALL business logic lives here.

Orchestrates repositories, infrastructure clients, and other services
to implement the six primary workflows from Doc 05 §5:
  1. Community Connection
  2. Telegram Account Linking (moved to app.modules.telegram_connect)
  3. Group Access (join link, join requests, grant after payment)
  4. Access Revocation
  5. Synchronization
  6. Webhook Processing

This service NEVER calls the Telegram API directly — it delegates to
TelegramClient (infrastructure).  It NEVER accesses the database
directly — it delegates to TelegramRepository.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import Settings
from app.core.logging import get_logger
from app.infrastructure.telegram.telegram_exceptions import (
    TelegramException,
    TelegramNotFoundException,
    TelegramPermissionException,
    TelegramRateLimitException,
)
from app.infrastructure.telegram.telegram_interface import TelegramClient
from app.infrastructure.telegram.telegram_models import TelegramChatMember
from app.modules.member.enums import MembershipStatus
from app.modules.telegram import constants as tc
from app.modules.telegram.enums import (
    TelegramConnectionStatus,
    TelegramOperationStatus,
    TelegramOperationType,
)
from app.modules.telegram.exceptions import (
    BotCannotRemoveMemberError,
    CommunityNotConnectedError,
    CommunityNotFoundError,
    MemberNotInCommunityError,
    MemberPlanStillActiveError,
    SubscriptionInactiveError,
    TelegramNotLinkedError,
    TelegramOperationFailedError,
    UnauthorizedCommunityAccessError,
)
from app.modules.telegram.repositories import TelegramRepository
from app.modules.telegram.schemas import (
    InviteResponse,
    MemberRemovalResponse,
    TelegramConnectionStatusResponse,
)

logger = get_logger(__name__)

_DEFAULT_BACKOFF = [timedelta(minutes=m) for m in (1, 5, 15, 30, 60)]
_BACKOFF_UNITS = {"s": "seconds", "m": "minutes", "h": "hours"}


def _parse_backoff(value: str) -> list[timedelta]:
    """Parse TELEGRAM_RETRY_BACKOFF such as "1m,5m,15m,30m,60m" (units s, m, h)."""
    steps: list[timedelta] = []
    for part in value.split(","):
        part = part.strip().lower()
        if len(part) < 2 or part[-1] not in _BACKOFF_UNITS or not part[:-1].isdigit():
            return _DEFAULT_BACKOFF
        steps.append(timedelta(**{_BACKOFF_UNITS[part[-1]]: int(part[:-1])}))
    return steps or _DEFAULT_BACKOFF


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
        """The community's join-request link, for a member with an active plan.

        The link is shared by the whole community: tapping it only *asks* to
        join, and the bot approves the request only for members with an
        active plan (see process_webhook_join_request).
        """
        community = await self._repo.get_community_by_id(community_id)
        if community is None or not community.is_active:
            raise CommunityNotFoundError()

        if community.telegram_connection_status != TelegramConnectionStatus.CONNECTED.value:
            raise CommunityNotConnectedError()

        if await self._repo.get_member_telegram_id(member_id) is None:
            raise TelegramNotLinkedError()

        if not await self._repo.has_active_subscription_in_community(member_id, community_id):
            raise SubscriptionInactiveError()

        link = await self._join_link(community)

        membership = await self._repo.get_membership(member_id, community_id)
        if membership is None or membership.status != MembershipStatus.JOINED.value:
            await self._repo.set_membership_status(
                member_id, community_id, MembershipStatus.PAID_NOT_JOINED,
            )

        return InviteResponse(invite_link=link, expires_at=None)

    async def _join_link(self, community: Any) -> str:
        """The community's join-request link, created on first use."""
        if community.telegram_join_link:
            return community.telegram_join_link
        try:
            invite = await self._telegram.create_invite_link(
                chat_id=community.telegram_chat_id,
                creates_join_request=True,
                name=tc.JOIN_LINK_NAME,
            )
        except TelegramException as exc:
            logger.error(
                "Failed to create join link for community %s: %s",
                community.id,
                exc.message,
            )
            raise TelegramOperationFailedError() from exc

        await self._repo.save_join_link(community.id, invite.invite_link)
        community.telegram_join_link = invite.invite_link
        logger.info("Join link created for community %s", community.id)
        return invite.invite_link

    async def grant_access_after_payment(
        self,
        member_id: uuid.UUID,
        plan_id: uuid.UUID,
    ) -> None:
        """After a paid plan: record the membership and DM the member the join button.

        Best effort on the Telegram side: the payment stands even if the
        message can't be sent (the site's "Join group" button still works).
        """
        community_id = await self._repo.get_plan_community_id(plan_id)
        if community_id is None:
            return
        community = await self._repo.get_community_by_id(community_id)
        if community is None:
            return

        telegram_user_id = await self._repo.get_member_telegram_id(member_id)
        membership = await self._repo.get_membership(member_id, community_id)
        if membership is not None and membership.status == MembershipStatus.JOINED.value:
            if telegram_user_id:
                await self._send_private(
                    telegram_user_id, tc.MSG_PAID_ALREADY_IN.format(community=community.name),
                )
            return

        await self._repo.set_membership_status(
            member_id, community_id, MembershipStatus.PAID_NOT_JOINED,
        )

        if (
            not telegram_user_id
            or not community.telegram_chat_id
            or community.telegram_connection_status != TelegramConnectionStatus.CONNECTED.value
        ):
            return

        # Already in the group (e.g. joined before PulseAccess tracked it)?
        try:
            chat_member = await self._telegram.get_chat_member(
                community.telegram_chat_id, int(telegram_user_id),
            )
        except TelegramException:
            chat_member = None
        if chat_member is not None and chat_member.status in tc.MEMBER_PRESENT_STATUSES:
            await self._repo.set_membership_status(
                member_id, community_id, MembershipStatus.JOINED,
            )
            await self._send_private(
                telegram_user_id, tc.MSG_PAID_ALREADY_IN.format(community=community.name),
            )
            return

        try:
            link = await self._join_link(community)
        except TelegramOperationFailedError:
            return
        await self._send_private(
            telegram_user_id,
            tc.MSG_PAID_JOIN.format(community=community.name),
            reply_markup={"inline_keyboard": [[{"text": tc.JOIN_BUTTON_TEXT, "url": link}]]},
        )

    async def process_webhook_join_request(self, update: dict) -> None:
        """Someone tapped a join-request link: approve paying members, decline the rest."""
        request = update.get("chat_join_request", {})
        chat_id = str(request.get("chat", {}).get("id", ""))
        user_id = request.get("from", {}).get("id")
        if not user_id:
            return

        community = await self._repo.get_community_by_chat_id(chat_id)
        if community is None:
            # Not a PulseAccess group; leave the request for its admins.
            return

        member = await self._repo.find_member_by_telegram_id(str(user_id))
        allowed = (
            member is not None
            and community.is_active
            and await self._repo.has_active_subscription_in_community(member.id, community.id)
        )

        if allowed:
            try:
                await self._telegram.approve_join_request(chat_id, int(user_id))
            except TelegramException as exc:
                logger.error(
                    "Approving join request of member %s in community %s failed: %s",
                    member.id, community.id, exc.message,
                )
                return
            await self._repo.set_membership_status(
                member.id, community.id, MembershipStatus.JOINED,
            )
            logger.info("Member %s joined community %s", member.id, community.id)
            return

        try:
            await self._telegram.decline_join_request(chat_id, int(user_id))
        except TelegramException as exc:
            logger.error(
                "Declining join request in community %s failed: %s", community.id, exc.message,
            )
        logger.info(
            "Declined join request for community %s (%s)",
            community.id,
            "member without an active plan" if member else "not a PulseAccess member",
        )
        # user_chat_id lets the bot DM the requester even if they never started it.
        await self._send_private(
            str(request.get("user_chat_id") or user_id),
            tc.MSG_JOIN_DECLINED.format(community=community.name),
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

    async def remove_expired_member(
        self,
        community_id: uuid.UUID,
        member_id: uuid.UUID,
        creator_id: uuid.UUID,
    ) -> MemberRemovalResponse:
        """Creator removes a member whose plan has ended, without waiting for the daily check.

        Only members with no active plan in this community can be removed.
        The Telegram removal runs now; if Telegram is unreachable it is queued
        for the retry worker instead.
        """
        community = await self._repo.get_community_by_id(community_id)
        if community is None:
            raise CommunityNotFoundError()
        if community.creator_id != creator_id:
            raise UnauthorizedCommunityAccessError()

        membership = await self._repo.get_membership(member_id, community_id)
        if membership is None:
            raise MemberNotInCommunityError()
        if await self._repo.has_active_subscription_in_community(member_id, community_id):
            raise MemberPlanStillActiveError()

        def result(removal: str) -> MemberRemovalResponse:
            return MemberRemovalResponse(
                member_id=member_id,
                community_id=community_id,
                membership_status=MembershipStatus.REMOVED.value,
                telegram_removal=removal,
            )

        if membership.status == MembershipStatus.REMOVED.value:
            return result("ALREADY_REMOVED")

        removal = "NOT_NEEDED"
        telegram_user_id = await self._repo.get_member_telegram_id(member_id)
        if community.telegram_chat_id and telegram_user_id:
            try:
                await self._remove_from_group(community, telegram_user_id)
                removal = "DONE"
            except (TelegramPermissionException, TelegramNotFoundException) as exc:
                logger.warning(
                    "Bot could not remove member %s from community %s: %s",
                    member_id, community_id, exc,
                )
                raise BotCannotRemoveMemberError() from exc
            except TelegramException as exc:
                logger.warning(
                    "Telegram unavailable removing member %s from community %s; queued: %s",
                    member_id, community_id, exc,
                )
                await self.revoke_access(community_id, member_id)
                removal = "QUEUED"

        await self._repo.set_membership_status(
            member_id, community_id, MembershipStatus.REMOVED,
        )
        logger.info(
            "Creator %s removed member %s from community %s (%s)",
            creator_id, member_id, community_id, removal,
        )
        return result(removal)

    async def revoke_ended_access(self) -> int:
        """Handle each expired / cancelled subscription once.

        The member is removed from the community's group unless another of
        their plans there is still active. Returns how many removals were queued.
        """
        queued = 0
        for subscription, community_id in await self._repo.find_ended_unhandled_subscriptions():
            member_id = subscription.member_id
            still_covered = await self._repo.has_active_subscription_in_community(
                member_id, community_id,
            )
            membership = await self._repo.get_membership(member_id, community_id)
            already_removed = (
                membership is not None
                and membership.status == MembershipStatus.REMOVED.value
            )

            if not still_covered and not already_removed:
                community = await self._repo.get_community_by_id(community_id)
                if (
                    community is not None
                    and community.telegram_chat_id
                    and await self._repo.get_member_telegram_id(member_id)
                ):
                    await self.revoke_access(community_id, member_id)
                    queued += 1
                await self._repo.set_membership_status(
                    member_id, community_id, MembershipStatus.REMOVED,
                )

            await self._repo.mark_access_handled(subscription.id)
        return queued

    # ══════════════════════════════════════════════════════════════════
    #  Workflow 5 — Operation Execution (called by workers)
    # ══════════════════════════════════════════════════════════════════

    async def execute_operation(self, operation_id: uuid.UUID) -> None:
        """Execute a single queued Telegram operation."""
        op = await self._repo.get_operation(operation_id)
        if op is None or op.status in (
            TelegramOperationStatus.COMPLETED.value,
            TelegramOperationStatus.FAILED.value,
        ):
            return

        # The lease: if this attempt never finishes, the op is picked up again after it.
        timeout = getattr(self._settings, "TELEGRAM_PROCESSING_TIMEOUT", 300)
        await self._repo.claim_operation(
            operation_id, datetime.now(timezone.utc) + timedelta(seconds=timeout),
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

        except Exception as exc:
            # Transient Telegram error, or a bug: retry a bounded number of times.
            if not isinstance(exc, TelegramException):
                logger.exception("Operation %s raised an unexpected error", operation_id)
            max_retries = getattr(self._settings, "TELEGRAM_MAX_RETRIES", 5)
            if op.retry_count >= max_retries:
                await self._repo.mark_failed(operation_id, error=str(exc))
                logger.error("Operation %s exhausted retries", operation_id)
            else:
                delay = self._retry_delay(op.retry_count, exc)
                scheduled = datetime.now(timezone.utc) + delay
                await self._repo.increment_retry(operation_id, scheduled, error=str(exc))
                logger.info(
                    "Operation %s scheduled for retry in %d s",
                    operation_id,
                    int(delay.total_seconds()),
                )

    def _retry_delay(self, retry_count: int, exc: Exception) -> timedelta:
        """Next delay from TELEGRAM_RETRY_BACKOFF; never sooner than Telegram's retry_after."""
        steps = _parse_backoff(getattr(self._settings, "TELEGRAM_RETRY_BACKOFF", ""))
        delay = steps[min(retry_count, len(steps) - 1)]
        if isinstance(exc, TelegramRateLimitException) and exc.retry_after:
            delay = max(delay, timedelta(seconds=int(exc.retry_after)))
        return delay

    async def _execute_remove_member(self, op: Any) -> None:
        """Remove a member from a Telegram group (ban then unban)."""
        # The member may have bought or renewed a plan after this was queued.
        if await self._repo.has_active_subscription_in_community(op.member_id, op.community_id):
            logger.info(
                "Skipping removal of member %s from community %s: plan active again",
                op.member_id, op.community_id,
            )
            return

        community = await self._repo.get_community_by_id(op.community_id)
        if community is None or not community.telegram_chat_id:
            raise TelegramNotFoundException("Community or chat not found")

        telegram_user_id = await self._repo.get_member_telegram_id(op.member_id)
        if telegram_user_id is None:
            raise TelegramNotFoundException("Member or telegram ID not found")

        await self._remove_from_group(community, telegram_user_id)

    async def _remove_from_group(self, community: Any, telegram_user_id: str) -> None:
        """Ban then unban (so they can rejoin after renewing), then tell them why."""
        await self._telegram.ban_member(
            community.telegram_chat_id,
            int(telegram_user_id),
        )
        await self._telegram.unban_member(
            community.telegram_chat_id,
            int(telegram_user_id),
        )
        await self._send_private(
            telegram_user_id, tc.MSG_ACCESS_ENDED.format(community=community.name),
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
                # Links the bot made may be revoked with it; make a fresh one later.
                await self._repo.save_join_link(community.id, None)
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
        await self._apply_bot_rights(community, chat_id, member, title)

    async def verify_connection(self, community: Any, bot_user_id: int) -> None:
        """Sync worker: re-check the bot's rights in a linked group.

        Moves CONNECTED → NEEDS_ATTENTION when the bot was removed or lost its
        rights, and NEEDS_ATTENTION → CONNECTED once they are back. Temporary
        errors (network, rate limit, Telegram 5xx, our own token) change nothing.
        """
        chat_id = community.telegram_chat_id
        try:
            member = await self._telegram.get_chat_member(chat_id, bot_user_id)
        except (TelegramPermissionException, TelegramNotFoundException) as exc:
            logger.warning("Sync: bot has no access to chat %s: %s", chat_id, exc)
            member = None
        except TelegramException as exc:
            if not str(exc).startswith("HTTP 400"):
                logger.warning("Sync: could not check chat %s: %s", chat_id, exc)
                return
            # e.g. "chat not found": the group is gone or the bot can't see it.
            logger.warning("Sync: bot has no access to chat %s: %s", chat_id, exc)
            member = None
        await self._apply_bot_rights(community, chat_id, member, None)

    async def _apply_bot_rights(
        self,
        community: Any,
        chat_id: str,
        member: TelegramChatMember | None,
        title: str | None,
    ) -> None:
        """Store CONNECTED / NEEDS_ATTENTION and tell the creator when it changes.

        title is the group's title from a webhook; None means the sync check.
        """
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
                text = (
                    tc.MSG_GROUP_CONNECTED.format(title=title, community=community.name)
                    if title is not None
                    else tc.MSG_GROUP_ACCESS_RESTORED.format(community=community.name)
                )
                await self._notify_creator(community.creator_id, text)
            return

        if previous != TelegramConnectionStatus.NEEDS_ATTENTION.value:
            await self._repo.update_connection_status(
                community.id, TelegramConnectionStatus.NEEDS_ATTENTION,
            )
            community.telegram_connection_status = TelegramConnectionStatus.NEEDS_ATTENTION.value
            # Links the bot made may be revoked with its rights; make a fresh one later.
            await self._repo.save_join_link(community.id, None)
            community.telegram_join_link = None
            logger.warning(
                "Community %s NEEDS_ATTENTION: bot lacks admin rights in chat %s",
                community.id, chat_id,
            )
            text = (
                tc.MSG_GROUP_NEEDS_ADMIN.format(title=title, community=community.name)
                if title is not None
                else tc.MSG_GROUP_ACCESS_LOST.format(community=community.name)
            )
            await self._notify_creator(community.creator_id, text)

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

    async def _send_private(
        self,
        telegram_user_id: str,
        text: str,
        reply_markup: dict | None = None,
    ) -> None:
        """Best effort: the result stands even if the message fails."""
        try:
            await self._telegram.send_message(
                int(telegram_user_id), text, reply_markup=reply_markup,
            )
        except (TelegramException, ValueError):
            logger.exception("Failed to message Telegram user %s", telegram_user_id)

    # ── Webhook de-duplication ───────────────────────────────────────

    async def is_update_processed(self, update_id: int) -> bool:
        return await self._repo.is_update_processed(update_id)

    async def record_update(self, update_id: int) -> None:
        await self._repo.record_update(update_id)

    async def process_webhook_chat_member(self, update: dict) -> None:
        """Keep community_members in step when a member joins or leaves the group."""
        event = update.get("chat_member", {})
        chat_id = str(event.get("chat", {}).get("id", ""))
        new_member = event.get("new_chat_member", {})
        new_status = new_member.get("status", "")
        user_id = str(new_member.get("user", {}).get("id", ""))

        community = await self._repo.get_community_by_chat_id(chat_id)
        if community is None:
            return
        member = await self._repo.find_member_by_telegram_id(user_id)
        if member is None:
            return

        present = new_status in tc.MEMBER_PRESENT_STATUSES and new_member.get("is_member", True)
        membership = await self._repo.get_membership(member.id, community.id)

        if present:
            if membership is None and not await self._repo.has_active_subscription_in_community(
                member.id, community.id,
            ):
                return  # someone already in the group without a plan: leave them be
            if membership is None or membership.status != MembershipStatus.JOINED.value:
                await self._repo.set_membership_status(
                    member.id, community.id, MembershipStatus.JOINED,
                )
            return

        if membership is not None and membership.status in (
            MembershipStatus.JOINED.value,
            MembershipStatus.PAID_NOT_JOINED.value,
        ):
            # REMOVED stays REMOVED: our own ban/unban also arrives here.
            await self._repo.set_membership_status(
                member.id, community.id, MembershipStatus.LEFT,
            )
            logger.info("Member %s left community %s", member.id, community.id)

    # ══════════════════════════════════════════════════════════════════
    #  Health Check
    # ══════════════════════════════════════════════════════════════════

    async def health_check(self) -> bool:
        """Proxy to infrastructure health check."""
        return await self._telegram.health_check()
