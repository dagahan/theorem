from __future__ import annotations
from dataclasses import dataclass, field
from typing import Awaitable, Callable, TypeVar, Optional, List, Any, AsyncIterator, Dict
from contextvars import ContextVar
from contextlib import asynccontextmanager
import time
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
    step_times: Dict[str, float] = field(default_factory=dict)
    step_starts: Dict[str, float] = field(default_factory=dict)


    def register_rollback(
        self,
        action: UndoAction
    ) -> None:
        self.rollback_actions.append(action)
        self.completed_steps += 1


    def start_step_timer(
        self,
        step_name: str
    ) -> None:
        self.step_starts[step_name] = time.time()


    def end_step_timer(
        self,
        step_name: str
    ) -> None:
        if step_name in self.step_starts:
            duration_ms = (time.time() - self.step_starts[step_name]) * 1000
            self.step_times[step_name] = duration_ms
            logger.info(f"Step '{step_name}' completed in {duration_ms:.2f} ms")
            del self.step_starts[step_name]


    async def rollback_all(self) -> None:
        while self.rollback_actions:
            action = self.rollback_actions.pop()
            try:
                await action()

            except Exception as e:
                logger.error(f"<red>Rollback action failed:</red> <red><bg red><white>{str(e)}</white></bg red></red>")


@asynccontextmanager
async def transaction_scope() -> AsyncIterator[None]:
    recorder = TransactionRecorder()
    token = _current_transaction.set(recorder)
    try:
        yield

    except Exception as e:
        logger.warning(f"<red>Transaction failed after {recorder.completed_steps} steps:</red> <red><bg red><white>{str(e)}</white></bg red></red>")
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
    rollback: Optional[UndoWithResult[T]] = None,
    step_name: Optional[str] = None
) -> T:
    recorder = _current_transaction.get()
    if recorder is None:
        raise RuntimeError("execute_atomic_step must be used within @transactional function")

    if step_name:
        recorder.start_step_timer(step_name)

    try:
        result = await action()
        
        if step_name:
            recorder.end_step_timer(step_name)

        if rollback is not None:
            async def rollback_action() -> None:
                try:
                    await rollback(result)

                except Exception as e:
                    logger.error(f"<red>Rollback failed:</red> <red><bg red><white>{str(e)}</white></bg red></red>")
                    raise
                    
            recorder.register_rollback(rollback_action)

        return result
        
    except Exception as ex:
        if step_name:
            recorder.end_step_timer(step_name)
        raise


        


        