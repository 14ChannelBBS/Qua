import asyncio
import os

import asyncpg
import dotenv

dotenv.load_dotenv()


class DBService:
    pool: asyncpg.Pool = None

    @classmethod
    async def run(cls):
        cls.pool = await asyncpg.create_pool(os.getenv("dsn"))

    @classmethod
    async def shutdown(cls):
        async with asyncio.timeout(20):
            await cls.pool.close()
