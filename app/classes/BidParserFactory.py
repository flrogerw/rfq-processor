#!/usr/bin/env python3
"""Factory module for bid source parsers.

This module provides a simple interface to select the appropriate parser
for structured or unstructured RFQs based on a string identifier like 'SEWP'.
"""

from parsers.llm_bid_parser import LLMBidParser
from parsers.sewp_bid_parser import SEWPBidParser


class BidParserFactory:
    """Factory class to return the appropriate parser instance based on the bid source type.

    This allows for clean separation of parser logic based on known or unknown formats.
    Example sources: 'SEWP', 'GSA', or fallback to an LLM-based parser.
    """

    @staticmethod
    def get_parser(source_type: str) -> object:
        """Return an instance of the appropriate bid parser based on the source type.

        Args:
            source_type (str): A string identifier for the source type (e.g., 'SEWP').

        Returns:
            object: An instance of a parser class (e.g., SEWPBidParser, LLMBidParser).

        """
        try:
            # Dictionary mapping source types to parser classes
            parsers: dict[str, type] = {
                "SEWP": SEWPBidParser,
                # "GSA": GSABidParser,  Extend this as needed
                # "Unformatted": LLMBidParser,
            }

            # Normalize the input and return the matching parser or the default (LLM)
            parser_class = parsers.get(source_type.upper(), LLMBidParser)
            return parser_class()

        except Exception as e:
            # In case instantiation fails for any reason, fallback to LLM parser
            # Optionally log the error here
            print(f"Error selecting parser for '{source_type}': {e}")
            return LLMBidParser()

