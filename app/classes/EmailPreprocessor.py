#!/usr/bin/env python3
"""EmailPreprocessor module for cleaning email bodies and extracting text from attachments.

Supports PDF and Excel files, with placeholders for future DOCX support.
"""

import re
from io import BytesIO

import pandas as pd
import pdfplumber
from bs4 import BeautifulSoup


class EmailPreprocessor:
    """A utility class for cleaning and preprocessing email content.

    Includes support for:
    - HTML body cleaning
    - PDF and Excel attachment parsing
    - Email + attachment text normalization for downstream use (e.g. vector embeddings)
    """

    @staticmethod
    def clean_email_body(raw_email: str) -> str:
        """Clean HTML email content by removing tags, headers, footers, and excess whitespace.

        Args:
            raw_email (str): Raw HTML or plain text from an email body.

        Returns:
            str: Cleaned plain-text version of the email.

        """
        try:
            # Remove HTML tags
            soup = BeautifulSoup(raw_email, 'html.parser')
            text = soup.get_text()

            # Remove forwarded/reply headers
            text = re.sub(r'(?i)^From:.*?$', '', text, flags=re.MULTILINE)
            text = re.sub(r'(?i)^Sent:.*?$', '', text, flags=re.MULTILINE)

            # Remove common signature delimiter
            text = re.sub(r'(?i)--+.*', '', text)

            # Collapse excessive newlines
            text = re.sub(r'\n+', '\n', text)

            return text.strip()

        except Exception as e:
            print(f"[ERROR] Failed to clean email body: {e}")
            return raw_email  # Return original input on failure

    def extract_attachment_text(self, file_bytes: bytes, filename: str) -> str:
        """Extract readable text from PDF or Excel attachments.

        Args:
            file_bytes (bytes): Raw bytes of the file.
            filename (str): File name (used to detect file type).

        Returns:
            str: Extracted text or placeholder if unsupported or failed.

        """
        try:
            if filename.endswith('.pdf'):
                return self._extract_pdf(file_bytes)

            if filename.endswith('.xlsx'):
                return self._extract_excel(file_bytes)

            if filename.endswith('.docx'):
                # Placeholder for future implementation
                return "[DOCX parsing not implemented]"

            print(f"[INFO] Unsupported attachment type: {filename}")
            return ""

        except Exception as e:
            print(f"[ERROR] Failed to extract text from {filename}: {e}")
            return ""

    @staticmethod
    def _extract_pdf(file_bytes: bytes) -> str:
        """Extract text from a PDF file using pdfplumber.

        Args:
            file_bytes (bytes): Raw PDF file content.

        Returns:
            str: Extracted text from all pages, or empty string if failed.

        """
        try:
            text = ""
            with pdfplumber.open(BytesIO(file_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text.strip()

        except Exception as e:
            print(f"[ERROR] Failed to extract PDF text: {e}")
            return ""

    @staticmethod
    def _extract_excel(file_bytes: bytes) -> str:
        """Extract text from an Excel spreadsheet using pandas.

        Args:
            file_bytes (bytes): Raw Excel file content.

        Returns:
            str: Tabular data as a string without row indices.

        """
        try:
            dataframe = pd.read_excel(BytesIO(file_bytes), engine="openpyxl")
            return dataframe.to_string(index=False)

        except Exception as e:
            print(f"[ERROR] Failed to extract Excel content: {e}")
            return ""

    @staticmethod
    def normalize_text_blocks(email_text: str, attachments: dict[str, str]) -> str:
        """Combine email body and attachment texts into one unified string.

        Args:
            email_text (str): Cleaned body of the email.
            attachments (Dict[str, str]): Mapping of filename to extracted text.

        Returns:
            str: Unified text content suitable for embedding or downstream processing.

        """
        try:
            sections = [email_text]

            for name, content in attachments.items():
                section = f"\n--- BEGIN ATTACHMENT: {name} ---\n{content}"
                sections.append(section)

            return "\n\n".join(sections).strip()

        except Exception as e:
            print(f"[ERROR] Failed to normalize email and attachments: {e}")
            return email_text
