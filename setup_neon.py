#!/usr/bin/env python
"""Setup script for Neon PostgreSQL database"""

import sys
import os

sys.path.insert(0, '.')

# Import database setup functions
from database import engine, create_db_and_tables
from sqlmodel import Session, select
from models import User
import crud
from models import UserCreate

def main():
    print("=" * 70)
    print("SETTING UP NEON DATABASE")
    print("=" * 70)

    # Step 1: Create tables
    print("\n[1/3] Creating tables in Neon...")
    try:
        create_db_and_tables()
        print("      Created tables: user, task")
    except Exception as e:
        print(f"      ERROR: {e}")
        return False

    # Step 2: Create test user
    print("\n[2/3] Creating test user...")
    try:
        db = Session(engine)

        # Check if user exists
        existing = db.exec(select(User).where(User.email == "demo@test.com")).first()

        if existing:
            print(f"      User already exists: {existing.email}")
        else:
            user = crud.create_user(db, UserCreate(
                email="demo@test.com",
                password="demo123",
                name="Demo User"
            ))
            print(f"      Created user: {user.email}")

        db.close()
    except Exception as e:
        print(f"      ERROR: {e}")
        return False

    # Step 3: Verify data
    print("\n[3/3] Verifying data in Neon...")
    try:
        db = Session(engine)
        users = db.exec(select(User)).all()
        print(f"      Total users: {len(users)}")
        for user in users:
            print(f"        - {user.email}")
        db.close()
    except Exception as e:
        print(f"      ERROR: {e}")
        return False

    print("\n" + "=" * 70)
    print("SUCCESS: Neon database is ready!")
    print("=" * 70)
    print("\nYou can now:")
    print("1. Sign in with: demo@test.com / demo123")
    print("2. Create tasks")
    print("3. View all data in: https://console.neon.tech")
    print("\n" + "=" * 70)

    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
