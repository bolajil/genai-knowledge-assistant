"""
VaultMind GenAI Knowledge Assistant - Database Configuration
Supports both SQLite (development) and PostgreSQL (production)

Phase 2: Multi-Tenant Foundation
"""

import os
import logging
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from .models import Base

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration with environment-based selection"""
    
    def __init__(self):
        self.database_url = os.getenv("DATABASE_URL", "")
        self.is_production = os.getenv("ENVIRONMENT", "development") == "production"
        
        # Determine database type
        if self.database_url.startswith("postgresql"):
            self.db_type = "postgresql"
        elif self.database_url.startswith("sqlite"):
            self.db_type = "sqlite"
        elif self.database_url:
            self.db_type = "postgresql"  # Assume PostgreSQL for other URLs
        else:
            # Default to SQLite for development
            self.db_type = "sqlite"
            self.database_url = "sqlite:///data/users.db"
        
        logger.info(f"Database configured: {self.db_type}")
    
    @property
    def sync_url(self) -> str:
        """Get synchronous database URL"""
        return self.database_url
    
    @property
    def async_url(self) -> str:
        """Get async database URL"""
        if self.db_type == "postgresql":
            # Convert postgresql:// to postgresql+asyncpg://
            if "asyncpg" not in self.database_url:
                return self.database_url.replace("postgresql://", "postgresql+asyncpg://")
            return self.database_url
        elif self.db_type == "sqlite":
            # Convert sqlite:// to sqlite+aiosqlite://
            if "aiosqlite" not in self.database_url:
                return self.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
            return self.database_url
        return self.database_url


# Global config
db_config = DatabaseConfig()


# Synchronous engine (for Streamlit compatibility)
def get_sync_engine():
    """Get synchronous SQLAlchemy engine"""
    connect_args = {}
    if db_config.db_type == "sqlite":
        connect_args["check_same_thread"] = False
    
    return create_engine(
        db_config.sync_url,
        connect_args=connect_args,
        echo=os.getenv("SQL_DEBUG", "false").lower() == "true"
    )


# Async engine (for FastAPI)
def get_async_engine():
    """Get async SQLAlchemy engine"""
    pool_class = NullPool if db_config.db_type == "sqlite" else None
    
    return create_async_engine(
        db_config.async_url,
        echo=os.getenv("SQL_DEBUG", "false").lower() == "true",
        poolclass=pool_class
    )


# Session factories
sync_engine = None
async_engine = None
SyncSessionLocal = None
AsyncSessionLocal = None


def init_sync_db():
    """Initialize synchronous database"""
    global sync_engine, SyncSessionLocal
    
    sync_engine = get_sync_engine()
    SyncSessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False, expire_on_commit=False)
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=sync_engine)
    logger.info("Synchronous database initialized")
    
    return sync_engine


def init_async_db():
    """Initialize async database"""
    global async_engine, AsyncSessionLocal
    
    async_engine = get_async_engine()
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    logger.info("Async database initialized")
    return async_engine


async def create_async_tables():
    """Create tables using async engine"""
    global async_engine
    if async_engine is None:
        init_async_db()
    
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Async tables created")


# Dependency injection helpers
def get_sync_session() -> Session:
    """Get synchronous database session"""
    global SyncSessionLocal
    if SyncSessionLocal is None:
        init_sync_db()
    
    session = SyncSessionLocal()
    try:
        return session
    except Exception:
        session.close()
        raise


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session (context manager)"""
    global AsyncSessionLocal
    if AsyncSessionLocal is None:
        init_async_db()
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# FastAPI dependency
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session"""
    async with get_async_session() as session:
        yield session


# Compatibility layer for existing SQLite code
class LegacySQLiteCompat:
    """
    Compatibility layer for existing SQLite-based code.
    Allows gradual migration to new models.
    """
    
    def __init__(self, db_path: str = "data/users.db"):
        self.db_path = db_path
        self._sync_session = None
    
    def get_connection(self):
        """Get SQLite connection (legacy compatibility)"""
        import sqlite3
        return sqlite3.connect(self.db_path)
    
    def get_session(self) -> Session:
        """Get SQLAlchemy session"""
        if self._sync_session is None or not self._sync_session.is_active:
            self._sync_session = get_sync_session()
        return self._sync_session
    
    def close(self):
        """Close session"""
        if self._sync_session:
            self._sync_session.close()
            self._sync_session = None


# Initialize on import for backward compatibility
try:
    if db_config.db_type == "sqlite":
        # Only auto-init for SQLite (safe for development)
        init_sync_db()
except Exception as e:
    logger.warning(f"Could not auto-initialize database: {e}")
