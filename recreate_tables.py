#!/usr/bin/env python3
"""
Script to recreate database tables with updated schema
"""
import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from app.database.connection import engine
from sqlalchemy import text
from sqlmodel import SQLModel
from app.models import *

async def recreate_tables():
    """Drop and recreate all database tables"""
    try:
        async with engine.begin() as conn:
            # Drop all tables
            print("🗑️ Dropping existing tables...")
            await conn.execute(text("DROP SCHEMA public CASCADE;"))
            await conn.execute(text("CREATE SCHEMA public;"))
            await conn.execute(text("GRANT ALL ON SCHEMA public TO postgres;"))
            await conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
            
            # Create all tables
            print("🔧 Creating new tables...")
            await conn.run_sync(SQLModel.metadata.create_all)
            
            print("✅ Database tables recreated successfully!")
            
    except Exception as e:
        print(f"❌ Error recreating tables: {e}")
        raise

if __name__ == "__main__":
    print("🔧 Recreating database tables...")
    asyncio.run(recreate_tables())
