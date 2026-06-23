import asyncio
from redis.asyncio import from_url
import json

async def clear_redis():
    client = from_url("redis://localhost:6379/0")
    await client.set("neuroguard:training:status", json.dumps({"status": "idle"}))
    await client.close()
    print("Redis training status cleared!")

if __name__ == "__main__":
    asyncio.run(clear_redis())
