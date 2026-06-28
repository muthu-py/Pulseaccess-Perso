from typing import Protocol

class SchedulerInterface(Protocol):
    async def schedule(self, task_name: str, run_at: str, payload: dict) -> None:
        ...
