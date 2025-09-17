from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from enum import Enum
from typing import TYPE_CHECKING, cast

import colorama  # type: ignore[import-untyped]
from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import (
    DisconnectionError,
    OperationalError,
    TimeoutError as SQLTimeoutError,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.core.utils import EnvTools
from pydantic_schemas import Base

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"
    SHUTTING_DOWN = "shutting_down"


class DataBaseConnector:
    def __init__(self) -> None:
        self.engine: AsyncEngine | None = None
        self.async_session: async_sessionmaker[AsyncSession] | None = None
        self.state: ConnectionState = ConnectionState.DISCONNECTED
        self.connection_start_time: float | None = None
        self.last_health_check: float | None = None
        self.retry_count: int = 0
        self.max_retries: int = 5
        self.base_retry_delay: float = 5.0
        self.max_retry_delay: float = 60.0
        
        self.db_host = EnvTools.get_service_host("postgres")
        self.db_port = EnvTools.get_service_http_port("postgres")
        self.db_user = EnvTools.required_load_env_var("POSTGRES_USER")
        self.db_pwd = EnvTools.required_load_env_var("POSTGRES_PASSWORD")
        self.db_name = EnvTools.required_load_env_var("POSTGRES_DB")
        self.engine_config = (
            f"postgresql+asyncpg://{self.db_user}:{self.db_pwd}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


    async def init_alchemy_engine(self) -> None:
        logger.info("Starting database service..")
        
        logger.info(f"Database connection info:")
        logger.info(f"  ➜ Type: PostgreSQL")
        logger.info(f"  ➜ Host: {self.db_host}:{self.db_port}")
        logger.info(f"  ➜ Database: {self.db_name}")

        await self._connect_with_retry()


    async def _connect_with_retry(self) -> None:
        self.state = ConnectionState.CONNECTING
        self.connection_start_time = time.time()
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.info(f"Connection attempt {attempt + 1}/{self.max_retries + 1}")
                await self._create_engine()
                await self._test_connection_with_timeout()
                
                self.state = ConnectionState.CONNECTED
                self.retry_count = 0
                connection_time = time.time() - self.connection_start_time
                
                logger.success(f"Database connection established successfully!")
                logger.info(f"  ➜ Connection time: {connection_time * 1000:.2f} ms")
                return
                
            except Exception as e:
                self.retry_count = attempt + 1
                error_msg = self._format_error_message(e)
                
                if attempt < self.max_retries:
                    delay = self._calculate_retry_delay(attempt, e)
                    logger.warning(f"Connection attempt {attempt + 1} failed: {error_msg}")
                    logger.info(f"Retrying in {delay:.1f}s... (attempt {attempt + 2}/{self.max_retries + 1})")
                    await asyncio.sleep(delay)
                else:
                    self.state = ConnectionState.FAILED
                    logger.error(f"All connection attempts failed after {self.max_retries + 1} tries")
                    logger.error(f"Final error: {error_msg}")
                    raise RuntimeError(f"Cannot establish database connection: {error_msg}")


    def _calculate_retry_delay(
        self,
        attempt: int,
        error: Exception
    ) -> float:
        base_delay = self.base_retry_delay
        
        if isinstance(error, (DisconnectionError, OperationalError)):
            base_delay *= 1.5
        elif isinstance(error, asyncio.TimeoutError):
            base_delay *= 2.0
            
        exponential_delay = base_delay * (2 ** attempt)
        return float(min(exponential_delay, self.max_retry_delay))


    async def _create_engine(self) -> None:
        self.engine = create_async_engine(
            url=self.engine_config,
            echo=False,
            pool_size=15,          # increased for better performance
            max_overflow=25,       # increased for better performance
            pool_timeout=30,       # increased timeout
            pool_recycle=3600,     # 1 hour recycle
            pool_pre_ping=True,   # verify connections before use
            future=True,
            connect_args={
                "command_timeout": 30,
                "server_settings": {
                    "application_name": "theorem_ingestor",
                    "timezone": "UTC",
                }
            }
        )

        self.async_session = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )


    async def _test_connection_with_timeout(self) -> None:
        if not self.async_session:
            raise RuntimeError("Database session not initialized")
            
        try:
            async with asyncio.timeout(10):
                async with self.async_session() as session:
                    result = await session.execute(text("SELECT 1 as health_check"))
                    value = cast("int | None", result.scalar())
                    if value != 1:
                        raise RuntimeError("Health check query returned unexpected result")
                        
        except asyncio.TimeoutError as e:
            logger.warning("Database connection test timed out after 10 seconds")
            raise RuntimeError("Database connection test timed out after 10 seconds") from e

        except (DisconnectionError, OperationalError, SQLTimeoutError) as e:
            logger.warning(f"Database connection failed during test: {str(e)}")
            raise RuntimeError(f"Database connection failed: {str(e)}") from e

        except Exception as e:
            logger.warning(f"Unexpected error during connection test: {str(e)}")
            raise RuntimeError(f"Database connection test failed: {str(e)}") from e


    def _format_error_message(
        self,
        error: Exception
    ) -> str:
        error_type = type(error).__name__
        error_msg = str(error)
        
        if "connection" in error_msg.lower():
            return f"Connection error ({error_type}): {error_msg}"

        elif "timeout" in error_msg.lower():
            return f"Timeout error ({error_type}): {error_msg}"

        elif "authentication" in error_msg.lower():
            return f"Authentication error ({error_type}): {error_msg}"

        else:
            return f"Database error ({error_type}): {error_msg}"


    async def get_session(self) -> AsyncIterator[AsyncSession]:
        if not self.async_session:
            raise RuntimeError("Database engine is not initialized")
        if self.state != ConnectionState.CONNECTED:
            raise RuntimeError(f"Database is not connected (state: {self.state.value})")
            
        async with self.async_session() as session:
            yield session


    @asynccontextmanager
    async def session_ctx(self) -> AsyncIterator[AsyncSession]:
        if not self.async_session:
            raise RuntimeError("Database engine is not initialized")
        if self.state != ConnectionState.CONNECTED:
            raise RuntimeError(f"Database is not connected (state: {self.state.value})")
            
        async with self.async_session() as session:
            yield session


    async def health_check(self) -> dict[str, str | int | float]:
        if self.state != ConnectionState.CONNECTED:
            return {
                "status": "unhealthy",
                "state": self.state.value,
                "error": "Database not connected"
            }
            
        try:
            start_time = time.time()
            async with asyncio.timeout(5):
                if not self.async_session:
                    raise RuntimeError("Database session not initialized")
                async with self.async_session() as session:
                    result = await session.execute(text("SELECT 1 as health_check"))
                    value = cast("int | None", result.scalar())
                    
            response_time = time.time() - start_time
            self.last_health_check = time.time()
            
            if value == 1:
                return {
                    "status": "healthy",
                    "state": self.state.value,
                    "response_time_ms": round(response_time * 1000, 2),
                    "last_check": self.last_health_check
                }
            else:
                return {
                    "status": "unhealthy",
                    "state": self.state.value,
                    "error": "Health check query returned unexpected result"
                }
                
        except asyncio.TimeoutError:
            return {
                "status": "unhealthy",
                "state": self.state.value,
                "error": "Health check timed out"
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "state": self.state.value,
                "error": str(e)
            }


    async def test_connection(self) -> bool:
        health_result = await self.health_check()
        return health_result["status"] == "healthy"


    async def create_tables(self) -> None:
        if not self.engine:
            raise RuntimeError("Database engine is not initialized")
        if self.state != ConnectionState.CONNECTED:
            raise RuntimeError(f"Cannot create tables: database not connected (state: {self.state.value})")
            
        try:
            start_time = time.time()
            async with self.engine.connect() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.commit()
            
            creation_time_ms = (time.time() - start_time) * 1000
            logger.success(f"All tables created successfully in {creation_time_ms:.2f} ms")

        except Exception as ex:
            error_msg = f"Failed to create tables: {str(ex)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from ex


    async def drop_all_tables(self) -> None:
        if not self.engine:
            raise RuntimeError("Database engine is not initialized")
        if self.state != ConnectionState.CONNECTED:
            raise RuntimeError(f"Cannot drop tables: database not connected (state: {self.state.value})")
            
        try:
            start_time = time.time()
            async with self.engine.connect() as conn:
                await conn.run_sync(Base.metadata.drop_all)

                await conn.execute(
                    text(
                        "DROP TYPE IF EXISTS payment_method_enum, "
                        "deliveries_status_enum, "
                        "delivery_groups_status_enum CASCADE"
                    )
                )

                await conn.commit()
            
            drop_time_ms = (time.time() - start_time) * 1000
            logger.warning(f"All tables dropped successfully in {drop_time_ms:.2f} ms")

        except Exception as ex:
            error_msg = f"Failed to drop tables: {str(ex)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from ex


    async def graceful_shutdown(self) -> None:
        logger.info("Initiating graceful database shutdown...")
        self.state = ConnectionState.SHUTTING_DOWN
        
        if self.engine:
            try:
                await self.engine.dispose()
                logger.info("Database engine disposed successfully")
            except Exception as e:
                logger.error(f"Error during engine disposal: {e}")
        
        self.state = ConnectionState.DISCONNECTED
        logger.info("Database shutdown completed")


    async def reconnect(self) -> bool:
        if self.state == ConnectionState.CONNECTED:
            logger.info("Database is already connected")
            return True
            
        logger.info("Attempting to reconnect to database...")
        try:
            await self._connect_with_retry()
            return True
            
        except Exception as e:
            logger.error(f"Reconnection failed: {str(e)}")
            return False


    def get_connection_info(self) -> dict[str, str | int | float | None]:
        return {
            "state": self.state.value,
            "host": self.db_host,
            "port": self.db_port,
            "database": self.db_name,
            "retry_count": self.retry_count,
            "connection_start_time": self.connection_start_time,
            "last_health_check": self.last_health_check,
            "uptime_seconds": (
                time.time() - self.connection_start_time 
                if self.connection_start_time else None
            )
        }


