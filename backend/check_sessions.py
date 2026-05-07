import asyncio
from sqlalchemy import text
from app.database import engine

async def check_sessions():
    async with engine.connect() as conn:
        result = await conn.execute(text('SELECT id, user_id, token_hash, device, ip_address FROM sessions ORDER BY id DESC LIMIT 10'))
        rows = result.fetchall()
        print("Recent sessions:")
        for row in rows:
            print(f"  id={row[0]}, user_id={row[1]}, device={row[3]}, ip={row[4]}")

asyncio.run(check_sessions())
