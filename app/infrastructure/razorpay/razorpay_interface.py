from typing import Protocol

class RazorpayService(Protocol):
    async def process_webhook(self, payload: dict, signature: str) -> bool:
        ...
