from typing import Protocol

class TelegramService(Protocol):
    async def grant_access(self, user_id: str, channel_id: str) -> None:
        ...

    async def revoke_access(self, user_id: str, channel_id: str) -> None:
        ...

    async def send_message(self, user_id: str, message: str) -> None:
        ...

    async def create_invite_link(self, channel_id: str) -> str:
        ...
