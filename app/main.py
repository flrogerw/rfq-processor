#!/usr/bin/env python3
"""Main pipeline runner for processing RFQ emails.

This script ingests an email file (.eml), parses bid data,
and matches line items against supplier data using a hybrid matcher.
It also includes a data loader step to seed the database with mock data.
"""

from __future__ import annotations

from pprint import pprint
from typing import Optional

from classes.BidParserFactory import BidParserFactory
from classes.EmailIngestor import EmailIngestor
from classes.HybridSupplierMatcher import HybridSupplierMatcher
from classes.PostgresSingleton import PostgresSingleton
from classes.SupplierDataLoader import SupplierDataLoader


def run_pipeline(eml_path: str) -> None:
    """Run the entire RFQ processing pipeline on a given .eml file.

    Steps:
    1. Ingest the email file, skipping if already processed.
    2. Parse the email content for bid fields.
    3. Match extracted line items to supplier catalog.

    Args:
        eml_path (str): Path to the .eml email file.

    """
    try:
        db_conn = PostgresSingleton()
        ingestor = EmailIngestor()
        result: Optional[dict] = ingestor.ingest_eml_file(eml_path)

        if result is None:
            print("Email has already been processed or failed to ingest.")
            return

        # Step 2: Use bid parser
        factory = BidParserFactory()
        parser = factory.get_parser("SEWP")  # TODO: Determine email type dynamically

        extracted = parser.extract_fields(result['clean_text'], result['attachments'])

        print("----- Extracted Fields -----")
        pprint(extracted)
        print('-----------------------\n', flush=True)

        # Step 3: Use supplier matcher
        supplier_matcher = HybridSupplierMatcher(db_conn)

        print('\n----- Search Results ----\n', flush=True)

        for line_item in extracted['items']:
            print(f"Line Item: {line_item['part_number']} {line_item['name']}\n")
            matches = supplier_matcher.match_suppliers(line_item)
            pprint(matches)
            print('\n-----------------------\n', flush=True)

    except Exception as e:
        print(f"[ERROR] Pipeline execution failed: {e}")


if __name__ == "__main__":
    try:
        loader = SupplierDataLoader(csv_path="samples/supplier_products.csv")
        print('Creating embeddings and loading DB with mock data...', flush=True)
        loader.ensure_dummy_suppliers_exist()
        loader.bulk_insert_products()

        run_pipeline('samples/sample_rfq_with_line_items_attachment.eml')

    except Exception as e:
        print(f"[ERROR] Main execution failed: {e}")
