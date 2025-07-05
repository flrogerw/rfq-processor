#!/usr/bin/env python3
"""Module: SEWPBidParser

A module that provides a parser for extracting structured bid data from SEWP (Solutions for Enterprise-Wide Procurement)
email contents and attachments. It focuses on retrieving key fields such as due dates and line items from
both the email body and associated files like 'line_items.txt'.
"""

import re
from typing import Any


class SEWPBidParser:
    """Parser for SEWP (Solutions for Enterprise-Wide Procurement) bid data.

    This parser extracts structured information such as due dates and line items
    from email content and accompanying attachments. It supports detection and parsing
    of standardized attachment files like 'line_items.txt'.
    """

    def extract_fields(self, cleaned_text: str, attachments: dict[str, bytes]) -> dict[str, Any]:
        """Extract due date and items from email content and attachments.

        Args:
            cleaned_text (str): Plain-text email body.
            attachments (dict[str, bytes]): Mapping of filenames to raw file content.

        Returns:
            dict[str, Any]: Dictionary with keys 'due_date' and 'items'.

        """
        try:
            due_date = self._extract_due_date(cleaned_text)
        except Exception:
            due_date = ""
            # Could log this for debugging or alerting purposes

        try:
            items = self._extract_items_from_attachments(attachments)
        except Exception as e:
            items = []
            print(f"Failed to extract items: {e}")

        return {
            "due_date": due_date,
            "items": items,
        }

    @staticmethod
    def _extract_due_date(text: str) -> str:
        """Extract the reply-by due date from email content using regex.

        Args:
            text (str): The plain-text email content.

        Returns:
            str: Due date in 'YYYY-MM-DD' format if found, else empty string.

        """
        try:
            match = re.search(r"Reply by Date\s*:\s*(\d{2}-[A-Z]{3}-\d{4})", text)
            if match:
                from datetime import datetime
                return datetime.strptime(match.group(1), "%d-%b-%Y").strftime("%Y-%m-%d")
        except Exception:
            pass
        return ""

    def _extract_items_from_attachments(self, attachments: dict[str, bytes]) -> list[dict[str, Any]]:
        """Search for 'line_items.txt' attachment and parse its content into structured items.

        Args:
            attachments (dict[str, bytes]): Filenames mapped to their byte contents.

        Returns:
            list[dict[str, Any]]: List of parsed line items with keys such as 'name', 'quantity', etc.

        """
        for filename, content in attachments.items():
            if "line_items" in filename.lower() and content:
                try:
                    decoded = content.decode("utf-8")
                    return self._parse_line_items(decoded)
                except Exception:
                    # Ignore decode or parsing errors
                    continue
        return []

    @staticmethod
    def _parse_line_items(text: str) -> list[dict[str, Any]]:
        """Parse the 'line_items.txt' text content into structured line item dictionaries.

        Args:
            text (str): Text content of the 'line_items.txt' file.

        Returns:
            list[dict[str, Any]]: List of line items with fields 'name', 'part_number', 'quantity', and optionally 'delivery_region'.

        """
        items: list[dict[str, Any]] = []
        lines = text.strip().splitlines()

        for line in lines:
            parts = [p.strip() for p in line.split("|")]

            if len(parts) >= 3:
                try:
                    quantity = int(parts[-1])
                    name = parts[-2]
                    part_number = parts[-3]

                    # Detect if this line specifies a delivery region
                    is_delivery_region = name.lower() in {
                        "services delivery region",
                        "selected region for services delivery",
                    }

                    if is_delivery_region and items:
                        # Attach delivery region info to the last item
                        items[-1]["delivery_region"] = part_number
                    else:
                        # Regular item entry
                        items.append({
                            "name": name,
                            "quantity": quantity,
                            "part_number": part_number,
                        })

                except Exception:
                    # Skip malformed lines without stopping the parse
                    continue

        return items
