import asyncio
from passlib.context import CryptContext
from sqlalchemy import text
from app.database import engine

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
password_hash = pwd_context.hash('123456')
print(f'Hash generated: {password_hash[:30]}...')

async def set_password():
    async with engine.connect() as conn:
        # 先检查当前密码状态
        result = await conn.execute(text("SELECT hashed_password FROM users WHERE username = 'default'"))
        row = result.fetchone()
        print(f'Current hashed_password: {row[0] if row else None}')

        # 设置新密码
        await conn.execute(text("UPDATE users SET hashed_password = :hash WHERE username = 'default'"), {"hash": password_hash})
        await conn.commit()
        print('Password set for default user!')

asyncio.run(set_password())