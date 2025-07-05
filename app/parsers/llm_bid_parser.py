#!/usr/bin/env python3
"""LLM-based Bid Parser Module.

This module defines the `LLMBidParser` class, which leverages a large language model (LLM)
to extract structured data—such as due dates and line items—from unstructured RFQ (Request for Quote) content.

The parser reads from a reusable prompt template and communicates with an LLM through a `.chat()` interface.
It includes retry logic, validation of LLM responses, and configurable strictness on failure.

Intended for use in RFQ automation pipelines, especially when incoming data is irregular, informal,
or inconsistent with standard formats.

Dependencies:
    - A compatible LLM client with `.chat(prompt: str) -> str` functionality
    - `prompts/llm_bid_parser_prompt.txt` file (default path)

Example:
    parser = LLMBidParser(llm_client)
    result = parser.parse(cleaned_text)

"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class LLMBidParser:
    """Uses an LLM to extract structured bid line items and deadlines from unstructured email content."""

    def __init__(self, llm_client, prompt_path: str = "prompts/llm_bid_parser_prompt.txt", max_retries: int = 2, strict: bool = True) -> None:
        """Initialize the parser.

        Args:
            llm_client: An LLM interface with a `.chat(prompt: str)` method.
            prompt_path: Path to the static prompt template file.
            max_retries: How many times to retry on invalid response.
            strict: Whether to raise on failure (True) or return empty/default (False).

        """
        self.llm = llm_client
        self.prompt_template = self._load_prompt_template(prompt_path)
        self.max_retries = max_retries
        self.strict = strict

    def parse(self, text: str) -> dict[str, Any]:
        """Parse the cleaned RFQ text using the LLM."""
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
            error_message = "LLM failed to return valid JSON after retries."
            raise RuntimeError(error_message)
        return {
            "due_date": None,
            "items": [],
        }

    @staticmethod
    def _load_prompt_template(path: str) -> str:
        prompt_file = Path(path)
        if not prompt_file.exists():
            error_message = f"Prompt file not found at {path}"
            raise FileNotFoundError(error_message)
        return prompt_file.read_text(encoding="utf-8")

    @staticmethod
    def _validate(data: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(data, dict) or "due_date" not in data or "items" not in data:
            error_message = "Parsed data missing required fields"
            raise ValueError(error_message)

        try:
            if data["due_date"]:
                datetime.fromisoformat(data["due_date"])
        except Exception:
            error_message = "Invalid due_date format"
            raise ValueError(error_message)

        if not isinstance(data["items"], list):
            error_message = "Items should be a list"
            raise TypeError(error_message)

        for item in data["items"]:
            if not all(k in item for k in ("name", "quantity", "part_number")):
                error_message = "Each item must contain name, quantity, and part_number"
                raise ValueError(error_message)

        return data
