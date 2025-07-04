from parsers.sewp_bid_parser import SEWPBidParser
from parsers.llm_bid_parser import LLMBidParser

class BidParserFactory:
    @staticmethod
    def get_parser(source_type: str):
        """Return the appropriate parser class based on the bid source."""
        parsers = {
            "SEWP": SEWPBidParser,
            # "GSA": GSABidParser,  # Add more as needed
            # "Unformatted": LLMBidParser
        }

        return parsers.get(source_type.upper(), LLMBidParser)()