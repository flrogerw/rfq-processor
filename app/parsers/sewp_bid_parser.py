import re
from typing import Dict

class SEWPBidParser:
    def extract_fields(self, cleaned_text: str, attachments: dict) -> Dict:
        due_date = self._extract_due_date(cleaned_text)
        items = self._extract_items_from_attachments(attachments)
        return {
            "due_date": due_date,
            "items": items
        }

    @staticmethod
    def _extract_due_date(text: str) -> str:
        match = re.search(r"Reply by Date\s*:\s*(\d{2}-[A-Z]{3}-\d{4})", text)
        if match:
            from datetime import datetime
            return datetime.strptime(match.group(1), "%d-%b-%Y").strftime("%Y-%m-%d")
        return ""

    def _extract_items_from_attachments(self, attachments: dict) -> list:
        """Look for a 'line_items.txt' attachment and parse it."""
        for filename, content in attachments.items():
            if "line_items" in filename and content:
                return self._parse_line_items(content.decode("utf-8"))
        return []

    @staticmethod
    def _parse_line_items(text: str) -> list:
        lines = text.strip().splitlines()
        items = []
        for line in lines:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                try:
                    quantity = int(parts[-1])
                    name = parts[-2]
                    part_number = parts[-3]

                    # Detect delivery region line
                    is_delivery_region = name.lower() in {
                        "services delivery region", "selected region for services delivery"
                    }

                    if is_delivery_region and items:
                        items[-1]["delivery_region"] = part_number
                    else:
                        items.append({
                            "name": name,
                            "quantity": quantity,
                            "part_number": part_number
                        })

                except Exception:
                    continue
        return items

