import threading
import psycopg2
from psycopg2.extensions import connection as PGConnection
import os
from typing import Optional, Dict


class PostgresSingleton:
    """
    A thread-safe singleton class that returns a psycopg2 PostgreSQL connection.
    It uses a DSN (Data Source Name) string as the key to ensure only one connection
    per unique database configuration. Also ensures that the `pgvector` extension
    is enabled on the first connection.
    """

    _instances: Dict[str, "PostgresSingleton"] = {}
    _connections: Dict[str, PGConnection] = {}
    _lock = threading.Lock()

    def __new__(cls, dsn: Optional[str] = None) -> PGConnection:
        """
        Returns a singleton psycopg2 connection for the given DSN.
        If the connection does not exist yet, it is created and pgvector is initialized.

        Args:
            dsn (Optional[str]): The database connection string (DSN).
                                 If not provided, it will be built from environment variables.

        Returns:
            PGConnection: A live psycopg2 PostgreSQL connection.
        """
        dsn = dsn or cls._build_dsn_from_env()

        with cls._lock:
            if dsn not in cls._connections:
                try:
                    # Create a new database connection
                    conn = psycopg2.connect(dsn)
                    conn.autocommit = True

                    # Enable pgvector extension (only if it doesn't exist)
                    with conn.cursor() as cur:
                        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

                    print("Connected to PostgreSQL and ensured pgvector is available.")
                    cls._connections[dsn] = conn

                except Exception as e:
                    print(f"[ERROR] Failed to connect to PostgreSQL: {e}")
                    raise  # Let caller handle or crash

            return cls._connections[dsn]

    @staticmethod
    def _build_dsn_from_env() -> str:
        """
        Builds a PostgreSQL DSN (Data Source Name) from environment variables.

        Environment Variables Required:
            - DATABASE: name of the PostgreSQL database
            - DB_USER: username for the database
            - DB_PASSWORD: password for the user
            - DB_HOST: host of the PostgreSQL server
            - DB_PORT: port number (defaults to 5432)

        Returns:
            str: A DSN string in the format used by psycopg2.
        """
        try:
            return (
                f"dbname={os.getenv('DATABASE')} "
                f"user={os.getenv('DB_USER')} "
                f"password={os.getenv('DB_PASSWORD')} "
                f"host={os.getenv('DB_HOST')} "
                f"port={os.getenv('DB_PORT', '5432')}"
            )
        except Exception as e:
            print(f"[ERROR] Failed to build DSN from environment: {e}")
            raise
