"""SQLite configuration and optimization.

This module provides SQLite-specific performance optimizations and
configuration pragmas for production use.
"""

from sqlalchemy import Connection

# SQLite PRAGMA configuration constants
BUSY_TIMEOUT_MS = 5000
MMAP_SIZE_BYTES = 268435456  # 256 MB
CACHE_SIZE_PAGES = -64000  # 64 MB (negative = KB)


def configure_sqlite(conn: Connection) -> None:
    """Apply SQLite performance optimizations.

    Sets critical pragmas for production use:
    - WAL mode for concurrent readers/writers
    - Busy timeout to prevent "database is locked" errors
    - Foreign key enforcement for data integrity
    - Memory mapping for faster reads

    Args:
        conn: SQLAlchemy connection object
    """
    # Only apply to SQLite databases
    dialect = conn.dialect.name
    if dialect != "sqlite":
        return

    # Get the raw DBAPI connection
    dbapi_conn = conn.connection

    # CRITICAL: Enable WAL mode (persistent setting)
    # Allows concurrent readers + one writer (vs blocking default)
    # Impact: 10x-100x higher throughput
    dbapi_conn.execute("PRAGMA journal_mode=WAL")

    # CRITICAL: Set busy timeout (connection setting)
    # Wait up to 5 seconds before giving up on locked database
    # Prevents "database is locked" errors under contention
    dbapi_conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")

    # HIGH: Enable foreign key enforcement (connection setting)
    # By default SQLite parses but doesn't enforce FK constraints
    dbapi_conn.execute("PRAGMA foreign_keys=ON")

    # OPTIONAL: Memory mapping for faster reads (256MB)
    # Reduces I/O by memory-mapping the database file
    dbapi_conn.execute(f"PRAGMA mmap_size={MMAP_SIZE_BYTES}")

    # OPTIONAL: Set synchronous mode to NORMAL (WAL provides safety)
    # WAL mode already provides durability, NORMAL is faster than FULL
    dbapi_conn.execute("PRAGMA synchronous=NORMAL")

    # OPTIONAL: Increase cache size (64MB = -64000 pages)
    # Default is typically 2MB, more cache = fewer disk reads
    dbapi_conn.execute(f"PRAGMA cache_size={CACHE_SIZE_PAGES}")


def run_optimize(conn: Connection) -> None:
    """Run PRAGMA optimize to update query planner statistics.

    This should be called periodically (e.g., on shutdown or every few hours)
    to keep query planner statistics up to date. Unlike ANALYZE which scans
    everything, PRAGMA optimize is lightweight and only analyzes tables that
    have changed significantly.

    Args:
        conn: SQLAlchemy connection object
    """
    if conn.dialect.name == "sqlite":
        conn.connection.execute("PRAGMA optimize")
