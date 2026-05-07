import asyncio
from sqlalchemy import text
from app.database import engine

async def update_role():
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE users SET role='admin' WHERE username='admin'"))
        print('Updated admin role to admin')

asyncio.run(update_role())
