#!/usr/bin/env python3
"""EmailIngestor module for retrieving, deduplicating, and preprocessing RFQ emails.

Supports ingestion from IMAP mailboxes and local `.eml` files, attachment parsing,
and forwarding content to a preprocessing pipeline.
"""

from __future__ import annotations

import email
import imaplib
import os
from email import policy
from hashlib import md5
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv

from .EmailPreprocessor import EmailPreprocessor
from .MessageLogStore import MessageLogStore

if TYPE_CHECKING:
    from email.message import EmailMessage

# Load environment variables from a .env file
load_dotenv()


class EmailIngestor:
    """Ingests RFQ emails from an IMAP server or local `.eml` files.

    Performs deduplication via Message-ID, processes attachments and bodies, and
    routes normalized content to the next stage of the pipeline.
    """

    def __init__(
        self,
        host: str | None = None,
        user: str | None = None,
        password: str | None = None,
        mailbox: str = "INBOX",
        log_store: MessageLogStore | None = None,
    ) -> None:
        """Initialize the EmailIngestor.

        Args:
            host (str | None): IMAP host. Defaults to IMAP_HOST environment variable.
            user (str | None): IMAP user. Defaults to IMAP_USER environment variable.
            password (str | None): IMAP password. Defaults to IMAP_PASSWORD environment variable.
            mailbox (str): Mailbox folder to select (default: "INBOX").
            log_store (MessageLogStore | None): Optional MessageLogStore instance.

        """
        self.host = host or os.getenv("IMAP_HOST")
        self.user = user or os.getenv("IMAP_USER")
        self.password = password or os.getenv("IMAP_PASSWORD")
        self.mailbox = mailbox
        self.log_store = log_store or MessageLogStore()
        self.preprocessor = EmailPreprocessor()

    def connect(self) -> imaplib.IMAP4_SSL:
        """Establish an IMAP connection and select the mailbox.

        Returns:
            imaplib.IMAP4_SSL: Authenticated IMAP connection.

        Raises:
            Exception: If login or mailbox selection fails.

        """
        try:
            conn = imaplib.IMAP4_SSL(self.host)
            conn.login(self.user, self.password)
            conn.select(self.mailbox)

        except Exception as e:
            print(f"[ERROR] Failed to connect to IMAP: {e}")
            raise

        else:
            return conn

    def fetch_unread_emails(self) -> list[dict]:
        """Fetch unread emails from the configured mailbox.

        Returns:
            list[dict]: A list of preprocessed email dictionaries.

        """
        try:
            conn = self.connect()
            result, data = conn.search(None, 'UNSEEN')
            if result != 'OK':
                print("[ERROR] Failed to search for unread emails.")
                return []

            email_ids = data[0].split()
            results: list[dict] = []

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

        except Exception as e:
            print(f"[ERROR] Fetching unread emails failed: {e}")
            return []

        return results

    def ingest_eml_file(self, file_path: str) -> dict | None:
        """Ingest a single `.eml` file from disk and return preprocessed content.

        Args:
            file_path (str): Path to the `.eml` file.

        Returns:
            dict | None: Preprocessed email content, or None if already seen or failed to process.

        """
        try:
            with Path(file_path).open("rb") as f:
                msg = email.message_from_binary_file(f, policy=policy.default)
                return self._parse_and_preprocess(msg)
        except Exception as e:
            print(f"[ERROR] Failed to ingest EML file {file_path}: {e}")
            return None

    def _parse_and_preprocess(self, msg: EmailMessage) -> dict | None:
        """Parse and preprocess an email message.

        Extracts body and attachments, deduplicates by Message-ID, normalizes content,
        and logs the message as processed.

        Args:
            msg (EmailMessage): Parsed email object.

        Returns:
            dict | None: Normalized email data or None if previously processed.

        """
        try:
            # Use Message-ID if available; otherwise generate a fallback hash
            message_id = msg.get("Message-ID", md5(str(msg).encode()).hexdigest())

            if self.log_store.has_seen(message_id):
                print(f"[SKIP] Already seen: {message_id}")
                return None

            body = ""
            html = ""
            attachments: dict[str, bytes] = {}

            # Walk through each part of the email
            for part in msg.walk():
                content_type = part.get_content_type()
                content_dispo = str(part.get("Content-Disposition", ""))

                # Extract plain text
                if content_type == "text/plain" and "attachment" not in content_dispo:
                    body += part.get_content()

                # Extract HTML content
                elif content_type == "text/html":
                    html += part.get_content()

                # Extract attachments
                elif "attachment" in content_dispo:
                    filename = part.get_filename()
                    payload = part.get_payload(decode=True)
                    if filename and payload:
                        attachments[filename] = payload

            # Clean and normalize the extracted content
            cleaned_body = self.preprocessor.clean_email_body(html or body)

            # Extract text from attachments
            attachment_texts = {
                name: self.preprocessor.extract_attachment_text(content, name)
                for name, content in attachments.items()
            }

            # Combine email and attachment content into one normalized block
            combined_text = self.preprocessor.normalize_text_blocks(cleaned_body, attachment_texts)

            # Log the email as processed
            self.log_store.log(
                message_id=message_id,
                subject=msg.get("Subject", ""),
                email_from=msg.get("From", ""),
                status="processed",
            )

            return {
                "message_id": message_id,
                "subject": msg.get("Subject", ""),
                "from": msg.get("From", ""),
                "to": msg.get("To", ""),
                "date": msg.get("Date", ""),
                "clean_text": combined_text,
                "attachments": attachments,
            }

        except Exception as e:
            print(f"[ERROR] Failed to parse/preprocess email: {e}")
            return None
