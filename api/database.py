# Handles the SQLite database connection and setup.
#
# This project uses Python's built-in `sqlite3` module, so there is
# nothing extra to install for the database itself.

import sqlite3
from pathlib import Path

# The database file lives in the top-level "data" folder so it's easy
# to find, back up, or delete while you're experimenting.
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "app.db"


def get_connection():
    """Open a new connection to the SQLite database.

    Each request opens and closes its own connection. That's a bit
    less "efficient" than sharing one connection, but it's much
    easier to reason about when you're learning - no shared state,
    no threading surprises.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us read columns by name, e.g. row["user_id"]
    return conn


def init_db():
    """Create the tables the app needs, if they don't already exist.

    Called once when the server starts up (see main.py).
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        """
    )

    conn.commit()
    conn.close()
