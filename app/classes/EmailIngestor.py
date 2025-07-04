import imaplib
import email
from email import policy
from email.message import EmailMessage
from typing import List, Dict, Optional, Union
from hashlib import md5
from dotenv import load_dotenv
import os

from .EmailPreprocessor import EmailPreprocessor
from .MessageLogStore import MessageLogStore

# Load environment variables from .env
load_dotenv()


class EmailIngestor:
    """
    Ingests emails from an IMAP server or local .eml files,
    deduplicates using Message-ID, and routes content to the preprocessor.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        mailbox: str = "INBOX",
        log_store: Optional[MessageLogStore] = None,
    ):
        """
        Initializes the EmailIngestor with optional credentials and dependencies.

        Args:
            host (str): IMAP host (defaults to IMAP_HOST env var)
            user (str): IMAP username (defaults to IMAP_USER env var)
            password (str): IMAP password (defaults to IMAP_PASSWORD env var)
            mailbox (str): Mailbox folder to select
            log_store (MessageLogStore): Optional log storage handler
        """
        self.host = host or os.getenv("IMAP_HOST")
        self.user = user or os.getenv("IMAP_USER")
        self.password = password or os.getenv("IMAP_PASSWORD")
        self.mailbox = mailbox
        self.log_store = log_store or MessageLogStore()
        self.preprocessor = EmailPreprocessor()

    def connect(self) -> imaplib.IMAP4_SSL:
        """
        Connects to the IMAP server and selects the mailbox.

        Returns:
            imaplib.IMAP4_SSL: An active IMAP connection.
        """
        try:
            conn = imaplib.IMAP4_SSL(self.host)
            conn.login(self.user, self.password)
            conn.select(self.mailbox)
            return conn
        except Exception as e:
            print(f"[ERROR] Failed to connect to IMAP: {e}")
            raise

    def fetch_unread_emails(self) -> List[Dict]:
        """
        Fetches unread emails from the configured IMAP mailbox.
        Skips previously processed emails using Message-ID.

        Returns:
            List[Dict]: List of parsed and preprocessed email metadata and content.
        """
        try:
            conn = self.connect()
            result, data = conn.search(None, 'UNSEEN')
            if result != 'OK':
                print("[ERROR] Failed to search for unread emails.")
                return []

            email_ids = data[0].split()
            results = []

            for eid in email_ids:
                try:
                    res, msg_data = conn.fetch(eid, "(RFC822)")
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email, policy=policy.default)
                    parsed = self._parse_and_preprocess(msg)
                    if parsed:
                        results.append(parsed)
                except Exception as e:
                    print(f"[ERROR] Failed to parse email ID {eid}: {e}")

            return results

        except Exception as e:
            print(f"[ERROR] Fetching unread emails failed: {e}")
            return []

    def ingest_eml_file(self, file_path: str) -> Optional[Dict]:
        """
        Ingests a local `.eml` file from disk and processes it.

        Args:
            file_path (str): Path to the .eml file

        Returns:
            Optional[Dict]: Parsed email content or None if already processed or on failure.
        """
        try:
            with open(file_path, "rb") as f:
                msg = email.message_from_binary_file(f, policy=policy.default)
                return self._parse_and_preprocess(msg)
        except Exception as e:
            print(f"[ERROR] Failed to ingest EML file {file_path}: {e}")
            return None

    def _parse_and_preprocess(self, msg: EmailMessage) -> Optional[Dict]:
        """
        Parses an email, extracts relevant content, deduplicates using Message-ID,
        logs processing, and returns structured content.

        Args:
            msg (EmailMessage): Parsed email message object

        Returns:
            Optional[Dict]: Cleaned and structured email content or None if already processed.
        """
        try:
            message_id = msg.get("Message-ID", md5(str(msg).encode()).hexdigest())

            if self.log_store.has_seen(message_id):
                print(f"[SKIP] Already seen: {message_id}")
                return None

            body = ""
            html = ""
            attachments = {}

            # Walk through email parts
            for part in msg.walk():
                content_type = part.get_content_type()
                content_dispo = str(part.get("Content-Disposition", ""))

                # Extract plain text
                if content_type == "text/plain" and "attachment" not in content_dispo:
                    body += part.get_content()

                # Extract HTML body
                elif content_type == "text/html":
                    html += part.get_content()

                # Extract attachments
                elif "attachment" in content_dispo:
                    filename = part.get_filename()
                    payload = part.get_payload(decode=True)
                    if filename and payload:
                        attachments[filename] = payload

            # Clean and normalize content
            cleaned_body = self.preprocessor.clean_email_body(html or body)
            attachment_texts = {
                name: self.preprocessor.extract_attachment_text(content, name)
                for name, content in attachments.items()
            }
            combined_text = self.preprocessor.normalize_text_blocks(cleaned_body, attachment_texts)

            # Log message as processed
            self.log_store.log(
                message_id=message_id,
                subject=msg.get("Subject", ""),
                email_from=msg.get("From", ""),
                status="processed"
            )

            return {
                "message_id": message_id,
                "subject": msg.get("Subject", ""),
                "from": msg.get("From", ""),
                "to": msg.get("To", ""),
                "date": msg.get("Date", ""),
                "clean_text": combined_text,
                "attachments": attachments
            }

        except Exception as e:
            print(f"[ERROR] Failed to parse/preprocess email: {e}")
            return None
