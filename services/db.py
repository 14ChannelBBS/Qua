import asyncio
import os
from typing import Any

import asyncpg
import dotenv
import orjson
import redis.asyncio as aioredis

dotenv.load_dotenv()


class DBService:
    pool: asyncpg.Pool = None
    redis: aioredis.Redis = None

    @classmethod
    def jsonDumps(cls, obj: Any):
        data = orjson.dumps(obj)
        if not isinstance(obj, bytes):
            data = data.decode()
        return data

    @classmethod
    def jsonLoads(cls, obj: Any):
        if isinstance(obj, str):
            obj = obj.encode()
        return orjson.loads(obj)

    @classmethod
    async def initConnection(cls, conn: asyncpg.Connection):
        await conn.set_type_codec(
            "json", schema="pg_catalog", encoder=cls.jsonDumps, decoder=cls.jsonLoads
        )
        await conn.set_type_codec(
            "jsonb", schema="pg_catalog", encoder=cls.jsonDumps, decoder=cls.jsonLoads
        )

    @classmethod
    async def run(cls):
        cls.pool = await asyncpg.create_pool(os.getenv("dsn"), init=cls.initConnection)
        redisPool = aioredis.ConnectionPool.from_url(os.getenv("redis"))
        cls.redis = aioredis.Redis(connection_pool=redisPool)

    @classmethod
    async def shutdown(cls):
        async with asyncio.timeout(20):
            await cls.pool.close()
