"""Community module service — ALL business logic lives here.

Orchestrates the CommunityRepository to implement community CRUD
with ownership validation, name normalization, duplicate checking,
and pagination.

This service NEVER accesses the database directly — it delegates
to CommunityRepository.
"""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError

from app.core.logging import get_logger
from app.modules.community.exceptions import (
    CommunityNotFoundError,
    CommunityOwnershipError,
    DuplicateCommunityNameError,
    PendingTelegramConnectionError,
)
from app.modules.community.models import Community
from app.modules.community.repositories import CommunityRepository
from app.modules.community.schemas import (
    CommunityListResponse,
    CommunityResponse,
)

logger = get_logger(__name__)

# Sentinel: "field not sent" in a partial update (distinct from None = clear)
_UNSET: object = object()


class CommunityService:
    """Orchestrates all Community business logic."""

    def __init__(self, repository: CommunityRepository) -> None:
        self._repo = repository

    # ══════════════════════════════════════════════════════════════════
    #  Create
    # ══════════════════════════════════════════════════════════════════

    async def create_community(
        self,
        creator_id: uuid.UUID,
        name: str,
        description: str | None = None,
    ) -> CommunityResponse:
        """Create a new community for the authenticated creator."""
        clean_name = name.strip()

        if await self._repo.exists_by_name(creator_id, clean_name):
            raise DuplicateCommunityNameError()

        if await self._repo.has_pending_telegram(creator_id):
            raise PendingTelegramConnectionError()

        community = Community(
            creator_id=creator_id,
            name=clean_name,
            description=description,
            is_active=True,
        )
        try:
            community = await self._repo.create(community)
        except IntegrityError as exc:
            # A concurrent request created the same name after our check
            raise DuplicateCommunityNameError() from exc

        logger.info(
            "Community created: %s (creator=%s)",
            community.id,
            creator_id,
        )
        return self._to_response(community)

    # ══════════════════════════════════════════════════════════════════
    #  Read — Single
    # ══════════════════════════════════════════════════════════════════

    async def get_community(
        self,
        community_id: uuid.UUID,
        creator_id: uuid.UUID,
    ) -> CommunityResponse:
        """Fetch a single community by ID, scoped by creator ownership."""
        community = await self._repo.get_by_id(community_id, creator_id)
        if community is None:
            raise CommunityNotFoundError()
        return self._to_response(community)

    # ══════════════════════════════════════════════════════════════════
    #  Read — Lists (paginated)
    # ══════════════════════════════════════════════════════════════════

    async def list_active(
        self,
        creator_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> CommunityListResponse:
        """Return paginated active communities for a creator."""
        offset = (page - 1) * page_size
        communities = await self._repo.list_active(creator_id, offset, page_size)
        total = await self._repo.count_active(creator_id)
        return CommunityListResponse(
            communities=[self._to_response(c) for c in communities],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def list_inactive(
        self,
        creator_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> CommunityListResponse:
        """Return paginated inactive communities for a creator."""
        offset = (page - 1) * page_size
        communities = await self._repo.list_inactive(creator_id, offset, page_size)
        total = await self._repo.count_inactive(creator_id)
        return CommunityListResponse(
            communities=[self._to_response(c) for c in communities],
            page=page,
            page_size=page_size,
            total=total,
        )

    # ══════════════════════════════════════════════════════════════════
    #  Update
    # ══════════════════════════════════════════════════════════════════

    async def update_community(
        self,
        community_id: uuid.UUID,
        creator_id: uuid.UUID,
        name: str,
        description: str | None | object = _UNSET,
    ) -> CommunityResponse:
        """Update a community's name and, if given, its description."""
        community = await self._repo.get_by_id(community_id, creator_id)
        if community is None:
            raise CommunityNotFoundError()

        clean_name = name.strip()

        if await self._repo.exists_by_name(creator_id, clean_name, exclude_id=community_id):
            raise DuplicateCommunityNameError()

        values: dict = {"name": clean_name}
        if description is not _UNSET:
            values["description"] = description

        try:
            await self._repo.update(community_id, creator_id, values)
        except IntegrityError as exc:
            raise DuplicateCommunityNameError() from exc

        logger.info("Community updated: %s (creator=%s)", community_id, creator_id)

        # Re-fetch to return updated state
        updated = await self._repo.get_by_id(community_id, creator_id)
        return self._to_response(updated)  # type: ignore[arg-type]

    # ══════════════════════════════════════════════════════════════════
    #  Activate / Deactivate
    # ══════════════════════════════════════════════════════════════════

    async def activate_community(
        self,
        community_id: uuid.UUID,
        creator_id: uuid.UUID,
    ) -> CommunityResponse:
        """Activate a community."""
        community = await self._repo.get_by_id(community_id, creator_id)
        if community is None:
            raise CommunityNotFoundError()

        if community.telegram_chat_id is None and await self._repo.has_pending_telegram(
            creator_id, exclude_id=community_id,
        ):
            raise PendingTelegramConnectionError()

        await self._repo.activate(community_id, creator_id)

        logger.info("Community activated: %s (creator=%s)", community_id, creator_id)

        updated = await self._repo.get_by_id(community_id, creator_id)
        return self._to_response(updated)  # type: ignore[arg-type]

    async def deactivate_community(
        self,
        community_id: uuid.UUID,
        creator_id: uuid.UUID,
    ) -> CommunityResponse:
        """Deactivate a community. Telegram connection remains untouched."""
        community = await self._repo.get_by_id(community_id, creator_id)
        if community is None:
            raise CommunityNotFoundError()

        await self._repo.deactivate(community_id, creator_id)

        logger.info("Community deactivated: %s (creator=%s)", community_id, creator_id)

        updated = await self._repo.get_by_id(community_id, creator_id)
        return self._to_response(updated)  # type: ignore[arg-type]

    # ══════════════════════════════════════════════════════════════════
    #  Helpers
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _to_response(community: Community) -> CommunityResponse:
        """Map ORM entity to response schema with derived fields."""
        return CommunityResponse(
            id=community.id,
            name=community.name,
            description=community.description,
            is_active=community.is_active,
            telegram_connected=community.telegram_connected_at is not None,
            created_at=community.created_at,
            updated_at=community.updated_at,
        )
