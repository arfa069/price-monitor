import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def set_password():
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@localhost:5432/pricemonitor')
    async with engine.connect() as conn:
        await conn.execute(text("UPDATE users SET hashed_password = '$2b$12$tcKawzh9njXffDyjAHDuJeLNgZoAy0xND/pPEWVCibpdEd3IcY0GS' WHERE username = 'default'"))
        await conn.commit()
    print('Password set for default user!')
    await engine.dispose()

asyncio.run(set_password())