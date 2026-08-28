"""Seed script: python -m seed"""
from .database import SessionLocal, init_db
from . import models

def seed():
    init_db()
    db = SessionLocal()
    print("seeded")

if __name__ == "__main__":
    seed()