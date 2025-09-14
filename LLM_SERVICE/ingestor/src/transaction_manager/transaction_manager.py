from __future__ import annotations
from dataclasses import dataclass, field
from typing import Awaitable, Callable, TypeVar, Optional, List, Any, AsyncIterator
from contextvars import ContextVar
from contextlib import asynccontextmanager
from loguru import logger

T = TypeVar("T")
UndoAction = Callable[[], Awaitable[None]]
DoAction = Callable[[], Awaitable[T]]
UndoWithResult = Callable[[T], Awaitable[None]]

_current_transaction: ContextVar["TransactionRecorder | None"] = ContextVar("_current_transaction", default=None)


@dataclass
class TransactionRecorder:
    rollback_actions: List[UndoAction] = field(default_factory=list)
    completed_steps: int = 0


    def register_rollback(
        self,
        action: UndoAction
    ) -> None:
        self.rollback_actions.append(action)
        self.completed_steps += 1


    async def rollback_all(self) -> None:
        while self.rollback_actions:
            action = self.rollback_actions.pop()
            try:
                await action()

            except Exception as e:
                logger.error(f"Rollback action failed: {e}")


@asynccontextmanager
async def transaction_scope() -> AsyncIterator[None]:
    recorder = TransactionRecorder()
    token = _current_transaction.set(recorder)
    try:
        yield

    except Exception as e:
        logger.warning(f"Transaction failed after {recorder.completed_steps} steps: {e}")
        await recorder.rollback_all()
        raise

    finally:
        _current_transaction.reset(token)


def transactional(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        async with transaction_scope():
            return await func(*args, **kwargs)
    return wrapper


async def execute_atomic_step(
    action: DoAction[T],
    rollback: Optional[UndoWithResult[T]] = None
) -> T:
    recorder = _current_transaction.get()
    if recorder is None:
        raise RuntimeError("execute_atomic_step must be used within @transactional function")

    result = await action()

    if rollback is not None:
        async def rollback_action() -> None:
            try:
                await rollback(result)

            except Exception as e:
                logger.error(f"Rollback failed: {e}")
                raise
                
        recorder.register_rollback(rollback_action)

    return result


