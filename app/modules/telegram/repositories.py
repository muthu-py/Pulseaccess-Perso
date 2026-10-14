"""Telegram module repository — persistence layer.

Handles all database operations for telegram-related data:
community Telegram state, operation queue, and member lookups.
Contains NO business logic, NO external HTTP calls (Doc 05 §7).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.community.models import Community
from app.modules.member.enums import MembershipStatus
from app.modules.member.models import CommunityMember, Member
from app.modules.plan.models import Plan
from app.modules.subscription.enums import SubscriptionStatus
from app.modules.subscription.models import Subscription
from app.modules.telegram.enums import (
    TelegramConnectionStatus,
    TelegramOperationStatus,
    TelegramOperationType,
)
from app.modules.telegram.models import TelegramOperation, TelegramProcessedUpdate
from app.modules.telegram_connect.enums import OwnerType
from app.modules.telegram_connect.models import TelegramAccount


class TelegramRepository:
    """Data access layer for Telegram integration persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── Community queries ────────────────────────────────────────────

    async def get_community_by_id(self, community_id: uuid.UUID) -> Community | None:
        stmt = select(Community).where(Community.id == community_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_community_by_chat_id(self, chat_id: str) -> Community | None:
        stmt = select(Community).where(Community.telegram_chat_id == chat_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_chat_id(
        self,
        community_id: uuid.UUID,
        chat_id: str,
    ) -> None:
        stmt = (
            update(Community)
            .where(Community.id == community_id)
            .values(telegram_chat_id=chat_id)
        )
        await self._session.execute(stmt)

    async def update_connection_status(
        self,
        community_id: uuid.UUID,
        status: TelegramConnectionStatus,
    ) -> None:
        stmt = (
            update(Community)
            .where(Community.id == community_id)
            .values(telegram_connection_status=status.value)
        )
        await self._session.execute(stmt)

    async def mark_connected(self, community_id: uuid.UUID, chat_id: str) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(Community)
            .where(Community.id == community_id)
            .values(
                telegram_chat_id=chat_id,
                telegram_connection_status=TelegramConnectionStatus.CONNECTED.value,
                telegram_connected_at=now,
            )
        )
        await self._session.execute(stmt)

    async def mark_disconnected(self, community_id: uuid.UUID) -> None:
        stmt = (
            update(Community)
            .where(Community.id == community_id)
            .values(
                telegram_chat_id=None,
                telegram_connection_status=TelegramConnectionStatus.DISCONNECTED.value,
                telegram_connected_at=None,
                telegram_join_link=None,
            )
        )
        await self._session.execute(stmt)

    async def get_unlinked_communities(self, creator_id: uuid.UUID) -> Sequence[Community]:
        """Active communities of this creator still waiting for a Telegram chat."""
        stmt = select(Community).where(
            Community.creator_id == creator_id,
            Community.is_active.is_(True),
            Community.telegram_chat_id.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def replace_chat_id(self, old_chat_id: str, new_chat_id: str) -> Community | None:
        """Point a community at a new chat id (group → supergroup migration)."""
        community = await self.get_community_by_chat_id(old_chat_id)
        if community is None:
            return None
        # Links belong to the old chat; a new one is made on next use.
        await self._session.execute(
            update(Community)
            .where(Community.id == community.id)
            .values(telegram_chat_id=new_chat_id, telegram_join_link=None)
        )
        community.telegram_chat_id = new_chat_id
        community.telegram_join_link = None
        return community

    async def save_join_link(self, community_id: uuid.UUID, link: str | None) -> None:
        await self._session.execute(
            update(Community)
            .where(Community.id == community_id)
            .values(telegram_join_link=link)
        )

    # ── Creator lookup ───────────────────────────────────────────────

    async def get_creator_id_by_telegram_user(self, telegram_user_id: str) -> uuid.UUID | None:
        """Creator whose verified Telegram account has this user id."""
        stmt = select(TelegramAccount.owner_id).where(
            TelegramAccount.owner_type == OwnerType.CREATOR.value,
            TelegramAccount.telegram_user_id == telegram_user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_creator_telegram_user_id(self, creator_id: uuid.UUID) -> str | None:
        stmt = select(TelegramAccount.telegram_user_id).where(
            TelegramAccount.owner_type == OwnerType.CREATOR.value,
            TelegramAccount.owner_id == creator_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ── Processed webhook updates ────────────────────────────────────

    async def is_update_processed(self, update_id: int) -> bool:
        result = await self._session.execute(
            select(TelegramProcessedUpdate.update_id).where(
                TelegramProcessedUpdate.update_id == update_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def record_update(self, update_id: int) -> None:
        self._session.add(TelegramProcessedUpdate(update_id=update_id))
        await self._session.flush()

    # ── Member queries ───────────────────────────────────────────────

    async def get_member_by_id(self, member_id: uuid.UUID) -> Member | None:
        stmt = select(Member).where(Member.id == member_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_member_telegram_id(self, member_id: uuid.UUID) -> str | None:
        """Telegram user ID the member connected, if any."""
        stmt = select(TelegramAccount.telegram_user_id).where(
            TelegramAccount.owner_type == OwnerType.MEMBER.value,
            TelegramAccount.owner_id == member_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_member_by_telegram_id(self, telegram_user_id: str) -> Member | None:
        stmt = (
            select(Member)
            .join(
                TelegramAccount,
                (TelegramAccount.owner_id == Member.id)
                & (TelegramAccount.owner_type == OwnerType.MEMBER.value),
            )
            .where(TelegramAccount.telegram_user_id == telegram_user_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ── Access: subscriptions and group membership ───────────────────

    async def has_active_subscription_in_community(
        self,
        member_id: uuid.UUID,
        community_id: uuid.UUID,
    ) -> bool:
        """True if any of the member's plans in this community is active right now."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(Subscription.id)
            .join(Plan, Plan.id == Subscription.plan_id)
            .where(
                Subscription.member_id == member_id,
                Plan.community_id == community_id,
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                Subscription.ends_at > now,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_plan_community_id(self, plan_id: uuid.UUID) -> uuid.UUID | None:
        result = await self._session.execute(
            select(Plan.community_id).where(Plan.id == plan_id)
        )
        return result.scalar_one_or_none()

    async def get_membership(
        self,
        member_id: uuid.UUID,
        community_id: uuid.UUID,
    ) -> CommunityMember | None:
        stmt = select(CommunityMember).where(
            CommunityMember.member_id == member_id,
            CommunityMember.community_id == community_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_membership_status(
        self,
        member_id: uuid.UUID,
        community_id: uuid.UUID,
        status: MembershipStatus,
    ) -> CommunityMember:
        """Create or update the member's row for this community."""
        now = datetime.now(timezone.utc)
        membership = await self.get_membership(member_id, community_id)
        if membership is None:
            membership = CommunityMember(member_id=member_id, community_id=community_id)
            self._session.add(membership)
        membership.status = status.value
        if status == MembershipStatus.JOINED:
            membership.group_joined_at = now
        elif status in (MembershipStatus.LEFT, MembershipStatus.REMOVED):
            membership.group_left_at = now
        await self._session.flush()
        return membership

    async def find_ended_unhandled_subscriptions(
        self,
        limit: int = 200,
    ) -> Sequence[tuple[Subscription, uuid.UUID]]:
        """Expired / cancelled subscriptions the expiry job hasn't handled yet,
        each with its plan's community id."""
        stmt = (
            select(Subscription, Plan.community_id)
            .join(Plan, Plan.id == Subscription.plan_id)
            .where(
                Subscription.status.in_([
                    SubscriptionStatus.EXPIRED.value,
                    SubscriptionStatus.CANCELLED.value,
                ]),
                Subscription.access_revoked_at.is_(None),
            )
            .order_by(Subscription.ends_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def mark_access_handled(self, subscription_id: uuid.UUID) -> None:
        await self._session.execute(
            update(Subscription)
            .where(Subscription.id == subscription_id)
            .values(access_revoked_at=datetime.now(timezone.utc))
        )

    # ── Operation queue ──────────────────────────────────────────────

    async def create_operation(
        self,
        operation_type: TelegramOperationType,
        community_id: uuid.UUID,
        member_id: uuid.UUID | None = None,
        scheduled_at: datetime | None = None,
    ) -> TelegramOperation:
        op = TelegramOperation(
            operation_type=operation_type.value,
            community_id=community_id,
            member_id=member_id,
            status=TelegramOperationStatus.PENDING.value,
            scheduled_at=scheduled_at,
        )
        self._session.add(op)
        await self._session.flush()
        return op

    async def update_operation_status(
        self,
        operation_id: uuid.UUID,
        status: TelegramOperationStatus,
        last_error: str | None = None,
    ) -> None:
        values: dict = {"status": status.value}
        if last_error is not None:
            values["last_error"] = last_error
        if status == TelegramOperationStatus.COMPLETED:
            values["completed_at"] = datetime.now(timezone.utc)
        stmt = (
            update(TelegramOperation)
            .where(TelegramOperation.id == operation_id)
            .values(**values)
        )
        await self._session.execute(stmt)

    async def mark_completed(self, operation_id: uuid.UUID) -> None:
        await self.update_operation_status(
            operation_id,
            TelegramOperationStatus.COMPLETED,
        )

    async def mark_failed(
        self,
        operation_id: uuid.UUID,
        error: str | None = None,
    ) -> None:
        await self.update_operation_status(
            operation_id,
            TelegramOperationStatus.FAILED,
            last_error=error,
        )

    async def increment_retry(
        self,
        operation_id: uuid.UUID,
        scheduled_at: datetime,
        error: str | None = None,
    ) -> None:
        values: dict = {
            "status": TelegramOperationStatus.RETRYING.value,
            "retry_count": TelegramOperation.retry_count + 1,
            "scheduled_at": scheduled_at,
        }
        if error:
            values["last_error"] = error
        stmt = (
            update(TelegramOperation)
            .where(TelegramOperation.id == operation_id)
            .values(**values)
        )
        await self._session.execute(stmt)

    async def get_operation(self, operation_id: uuid.UUID) -> TelegramOperation | None:
        result = await self._session.execute(
            select(TelegramOperation).where(TelegramOperation.id == operation_id)
        )
        return result.scalar_one_or_none()

    async def claim_operation(self, operation_id: uuid.UUID, lease_until: datetime) -> None:
        """Mark PROCESSING; if the worker dies, the op is picked up again after lease_until."""
        stmt = (
            update(TelegramOperation)
            .where(TelegramOperation.id == operation_id)
            .values(
                status=TelegramOperationStatus.PROCESSING.value,
                scheduled_at=lease_until,
            )
        )
        await self._session.execute(stmt)

    async def find_pending(self) -> Sequence[TelegramOperation]:
        """Due PENDING / RETRYING ops, plus PROCESSING ops whose lease ran out."""
        now = datetime.now(timezone.utc)
        stmt = (
            select(TelegramOperation)
            .where(
                TelegramOperation.status.in_([
                    TelegramOperationStatus.PENDING.value,
                    TelegramOperationStatus.RETRYING.value,
                    TelegramOperationStatus.PROCESSING.value,
                ]),
                (TelegramOperation.scheduled_at.is_(None))
                | (TelegramOperation.scheduled_at <= now),
            )
            .order_by(TelegramOperation.created_at.asc())
            .limit(50)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_communities_to_verify(self) -> Sequence[Community]:
        """Linked communities the sync worker re-checks, including ones that may recover."""
        stmt = select(Community).where(
            Community.telegram_chat_id.is_not(None),
            Community.telegram_connection_status.in_([
                TelegramConnectionStatus.CONNECTED.value,
                TelegramConnectionStatus.NEEDS_ATTENTION.value,
            ]),
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()
