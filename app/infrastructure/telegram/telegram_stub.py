from app.infrastructure.telegram.telegram_interface import TelegramService

class TelegramStub(TelegramService):
    async def grant_access(self, user_id: str, channel_id: str) -> None:
        pass

    async def revoke_access(self, user_id: str, channel_id: str) -> None:
        pass

    async def send_message(self, user_id: str, message: str) -> None:
        pass

    async def create_invite_link(self, channel_id: str) -> str:
        return "https://t.me/joinchat/stub"
