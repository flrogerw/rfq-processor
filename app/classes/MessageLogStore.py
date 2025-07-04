from psycopg2.extras import RealDictCursor
from datetime import datetime
from .PostgresSingleton import PostgresSingleton  # Adjust path as needed

class MessageLogStore:
    """
    Stores RFQ processing logs in a PostgreSQL database to avoid duplicate processing
    and provide an audit trail using a centralized connection from PostgresSingleton.
    """

    def __init__(self):
        """
        Initializes the database connection and ensures the log table exists.
        """
        self.conn = PostgresSingleton()  # Get the shared psycopg2 connection

    def has_seen(self, message_id: str) -> bool:
        """
        Checks if a message with the given Message-ID has already been logged.

        Args:
            message_id (str): The unique Message-ID of the email.

        Returns:
            bool: True if the message has already been seen, False otherwise.
        """
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT 1 FROM rfq_logs WHERE message_id = %s", (message_id,))
                return cur.fetchone() is not None
        except Exception as e:
            print(f"[ERROR] Failed to check message ID {message_id}: {e}")
            return False

    def log(self, message_id: str, subject: str, email_from: str, status: str = "processed") -> None:
        """
        Logs an RFQ message into the database with its metadata.

        Args:
            message_id (str): Unique email Message-ID.
            subject (str): Subject of the email.
            email_from (str): Sender's email address.
            status (str): Processing status (default: 'processed').
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute("""
                INSERT INTO rfq_logs (message_id, subject, email_from, timestamp, status)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (message_id) DO NOTHING
                """, (message_id, subject, email_from, datetime.utcnow(), status))
                self.conn.commit()
        except Exception as e:
            print(f"[ERROR] Failed to log message ID {message_id}: {e}")
            self.conn.rollback()
