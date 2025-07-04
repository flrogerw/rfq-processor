from bs4 import BeautifulSoup
import re
import pdfplumber
import pandas as pd
from io import BytesIO
from typing import Dict


class EmailPreprocessor:
    """
    A utility class for preprocessing email content and extracting readable text
    from supported attachments such as PDFs and Excel files.
    """

    @staticmethod
    def clean_email_body(raw_email: str) -> str:
        """
        Cleans HTML email content by removing markup, forwarded/reply headers,
        footers, and extra whitespace.

        Args:
            raw_email (str): The raw HTML email body as a string.

        Returns:
            str: Cleaned plain-text email body.
        """
        try:
            # Strip HTML tags and decode entities
            soup = BeautifulSoup(raw_email, 'html.parser')
            text = soup.get_text()

            # Remove common reply/forward headers
            text = re.sub(r'(?i)^From:.*?$', '', text, flags=re.MULTILINE)
            text = re.sub(r'(?i)^Sent:.*?$', '', text, flags=re.MULTILINE)

            # Remove footers or signature separators
            text = re.sub(r'(?i)--+.*', '', text)

            # Collapse multiple newlines into one
            text = re.sub(r'\n+', '\n', text)

            return text.strip()
        except Exception as e:
            print(f"[ERROR] Failed to clean email body: {e}")
            return raw_email  # Return original in case of failure

    def extract_attachment_text(self, file_bytes: bytes, filename: str) -> str:
        """
        Extracts readable text from supported attachment formats.

        Args:
            file_bytes (bytes): Raw file content.
            filename (str): Original filename for extension detection.

        Returns:
            str: Extracted text, or an empty string if unsupported or failed.
        """
        try:
            if filename.endswith('.pdf'):
                return self._extract_pdf(file_bytes)
            elif filename.endswith('.xlsx'):
                return self._extract_excel(file_bytes)
            elif filename.endswith('.docx'):
                return "[DOCX parsing not implemented]"  # Stub
            else:
                print(f"[INFO] Unsupported attachment type: {filename}")
                return ""
        except Exception as e:
            print(f"[ERROR] Failed to extract text from {filename}: {e}")
            return ""

    @staticmethod
    def _extract_pdf(file_bytes: bytes) -> str:
        """
        Extracts text from a PDF file using pdfplumber.

        Args:
            file_bytes (bytes): Raw PDF file content.

        Returns:
            str: All extracted text from PDF pages.
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
        """
        Extracts text from an Excel spreadsheet using pandas.

        Args:
            file_bytes (bytes): Raw Excel file content.

        Returns:
            str: Table content as string with no row index.
        """
        try:
            df = pd.read_excel(BytesIO(file_bytes), engine="openpyxl")
            return df.to_string(index=False)
        except Exception as e:
            print(f"[ERROR] Failed to extract Excel content: {e}")
            return ""

    @staticmethod
    def normalize_text_blocks(email_text: str, attachments: Dict[str, str]) -> str:
        """
        Combines email body and attachments into a single normalized string.

        Args:
            email_text (str): Cleaned email body.
            attachments (Dict[str, str]): Mapping of filename to extracted text.

        Returns:
            str: Unified text content for downstream NLP or vector embedding.
        """
        try:
            sections = [email_text]
            for name, content in attachments.items():
                sections.append(f"\n--- BEGIN ATTACHMENT: {name} ---\n{content}")
            return "\n\n".join(sections).strip()
        except Exception as e:
            print(f"[ERROR] Failed to normalize email and attachments: {e}")
            return email_text
