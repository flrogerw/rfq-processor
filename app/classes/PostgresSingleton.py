#!/usr/bin/env python3
"""Singleton PostgreSQL connection handler with pgvector support.

This module defines a thread-safe singleton class `PostgresSingleton` that provides
shared psycopg2 connection instances across the application. It ensures that
the `pgvector` extension is available for use in vector similarity queries.

Environment variables required for connection:
- DATABASE
- DB_USER
- DB_PASSWORD
- DB_HOST
- DB_PORT (optional, defaults to 5432)
"""

from __future__ import annotations

import os
import threading
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from psycopg2.extensions import connection as PGConnection


class PostgresSingleton:
    """Thread-safe singleton for PostgreSQL connections via psycopg2.

    Ensures a single connection instance per unique DSN. Automatically enables
    the `pgvector` extension if not already present.

    Use this class to retrieve shared database connections throughout the application.
    """

    # Class-level shared connection map and thread lock
    _instances: ClassVar[dict[str, PostgresSingleton]] = {}
    _connections: ClassVar[dict[str, PGConnection]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __new__(cls, dsn: str | None = None) -> PGConnection:
        """Get or create a singleton PostgreSQL connection.

        Args:
            dsn (Optional[str]): The database connection string.
                If None, it is built from environment variables.

        Returns:
            PGConnection: A reusable psycopg2 connection instance.

        Raises:
            Exception: If connection or extension setup fails.

        """
        dsn = dsn or cls._build_dsn_from_env()

        with cls._lock:
            if dsn not in cls._connections:
                try:
                    # Establish a new PostgreSQL connection
                    import psycopg2
                    conn = psycopg2.connect(dsn)
                    conn.autocommit = True

                    # Ensure pgvector extension is available
                    with conn.cursor() as cur:
                        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

                    print("[INFO] Connected to PostgreSQL and ensured pgvector is available.")
                    cls._connections[dsn] = conn

                except Exception as e:
                    print(f"[ERROR] Failed to connect to PostgreSQL with DSN {dsn}: {e}")
                    raise

            return cls._connections[dsn]

    @staticmethod
    def _build_dsn_from_env() -> str:
        """Construct a PostgreSQL DSN string using environment variables.

        Expects the following environment variables:
            - DATABASE
            - DB_USER
            - DB_PASSWORD
            - DB_HOST
            - DB_PORT (optional, defaults to 5432)

        Returns:
            str: A psycopg2-compatible DSN string.

        Raises:
            ValueError: If any required environment variable is missing.

        """
        try:
            dbname = os.getenv("DATABASE")
            user = os.getenv("DB_USER")
            password = os.getenv("DB_PASSWORD")
            host = os.getenv("DB_HOST")
            port = os.getenv("DB_PORT", "5432")

            if not all([dbname, user, password, host]):
                error_message = "Missing required environment variables for DSN."
                raise ValueError(error_message)

        except Exception as e:
            print(f"[ERROR] Failed to build DSN from environment: {e}")
            raise

        else:
            return f"dbname={dbname} user={user} password={password} host={host} port={port}"
