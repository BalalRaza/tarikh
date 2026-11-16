import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(os.environ["DATABASE_URL"])
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def acquire():
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn
