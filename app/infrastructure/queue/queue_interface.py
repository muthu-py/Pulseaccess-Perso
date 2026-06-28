from typing import Protocol

class QueueInterface(Protocol):
    async def enqueue(self, task_name: str, payload: dict) -> None:
        ...
