#!/usr/bin/env python3

"""MessageLogStore.

Provides utilities for logging processed RFQ messages and checking for duplicates
via a PostgreSQL-backed log table. Ensures deduplication and audit tracking using
a centralized connection from PostgresSingleton.
"""

from datetime import datetime

from psycopg2.extras import RealDictCursor

from .PostgresSingleton import PostgresSingleton  # Shared DB connection instance


class MessageLogStore:
    """Stores and retrieves RFQ email metadata.

    Support deduplication and maintain an audit trail of processed messages.
    """

    def __init__(self) -> None:
        """Initialize the MessageLogStore with a shared PostgreSQL connection.

        Ensures all methods operate against the same DB instance using a singleton pattern.
        """
        self.conn = PostgresSingleton()  # Shared psycopg2 connection instance

    def has_seen(self, message_id: str) -> bool:
        """Check if a given email Message-ID has already been processed.

        Args:
            message_id (str): Unique identifier for the email (RFC 5322 Message-ID).

        Returns:
            bool: True if already processed (exists in logs), False otherwise.

        """
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT 1 FROM rfq_logs WHERE message_id = %s",
                    (message_id,),
                )
                return cur.fetchone() is not None
        except Exception as e:
            print(f"[ERROR] Failed to query message ID {message_id}: {e}")
            return False

    def log(
        self,
        message_id: str,
        subject: str,
        email_from: str,
        status: str = "processed",
    ) -> None:
        """Insert a log entry for the given message into the `rfq_logs` table.

        Args:
            message_id (str): Unique identifier of the email.
            subject (str): Subject line of the email.
            email_from (str): Sender email address.
            status (str): Status of processing (default: 'processed').

        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO rfq_logs (message_id, subject, email_from, timestamp, status)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (message_id) DO NOTHING
                    """,
                    (message_id, subject, email_from, datetime.utcnow(), status),
                )
                self.conn.commit()
        except Exception as e:
            print(f"[ERROR] Failed to log message ID {message_id}: {e}")
            self.conn.rollback()
