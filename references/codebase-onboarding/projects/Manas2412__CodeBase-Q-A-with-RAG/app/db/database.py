# app/db/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

import os
from dotenv import load_dotenv

load_dotenv()

raw_url = os.getenv("DATABASE_URL", "")
db_url = raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
if raw_url.startswith("postgresql://"):
    db_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
db_url = db_url.split("?")[0]
DATABASE_URL = db_url


engine = create_async_engine(
    DATABASE_URL,
    echo=False,          
    pool_size=5,
    max_overflow=10,
    connect_args={"ssl": "require"},   
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

class Base(DeclarativeBase):
    pass