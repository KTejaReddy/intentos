"""Generated schema tests: every model table exists and has its columns."""
import sqlite3

from database import DATABASE_URL, engine, init_db
from sqlalchemy import inspect


def _conn():
    path = DATABASE_URL.replace("sqlite:///", "")
    return sqlite3.connect(path)


def test_tables_exist():
    init_db()
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
