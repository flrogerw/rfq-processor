import json
import time
from typing import Dict, Any
from datetime import datetime
from pathlib import Path


class LLMBidParser:
    """
    Uses an LLM to extract structured bid line items and deadlines from
    unstructured email content and attachment text.
    """

    def __init__(self, llm_client, prompt_path: str = "prompts/llm_bid_parser_prompt.txt", max_retries: int = 2, strict: bool = True):
        """
        llm_client: An LLM interface with a `.chat(prompt: str)` method.
        prompt_path: Path to the static prompt template file.
        max_retries: How many times to retry on invalid response.
        strict: Whether to raise on failure (True) or return empty/default (False).
        """
        self.llm = llm_client
        self.prompt_template = self._load_prompt_template(prompt_path)
        self.max_retries = max_retries
        self.strict = strict

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse the cleaned RFQ text using the LLM.
        """
        prompt = self.prompt_template.replace("{{RFQ_TEXT}}", text.strip())

        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.llm.chat(prompt)
                data = json.loads(response)
                return self._validate(data)
            except Exception as e:
                print(f"[LLMBidParser] Attempt {attempt} failed: {e}")
                time.sleep(1)  # Small delay between retries

        if self.strict:
            raise RuntimeError("LLM failed to return valid JSON after retries.")
        else:
            return {
                "due_date": None,
                "items": []
            }

    @staticmethod
    def _load_prompt_template(path: str) -> str:
        prompt_file = Path(path)
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found at {path}")
        return prompt_file.read_text(encoding="utf-8")

    @staticmethod
    def _validate(data: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(data, dict) or "due_date" not in data or "items" not in data:
            raise ValueError("Parsed data missing required fields")

        try:
            if data["due_date"]:
                datetime.fromisoformat(data["due_date"])
        except Exception:
            raise ValueError("Invalid due_date format")

        if not isinstance(data["items"], list):
            raise ValueError("Items should be a list")

        for item in data["items"]:
            if not all(k in item for k in ("name", "quantity", "part_number")):
                raise ValueError("Each item must contain name, quantity, and part_number")

        return data
