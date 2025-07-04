from classes.EmailIngestor import EmailIngestor
from classes.BidParserFactory import BidParserFactory
from classes.HybridSupplierMatcher import HybridSupplierMatcher
from classes.PostgresSingleton import PostgresSingleton
from classes.SupplierDataLoader import SupplierDataLoader


def run_pipeline(eml_path: str):
    db_conn = PostgresSingleton()
    ingestor = EmailIngestor()
    result = ingestor.ingest_eml_file(eml_path)

    if result is None:
        print("Email has already been processed or failed to ingest.")
        return

    # Step 2: Use bid parser
    factory = BidParserFactory()
    parser = factory.get_parser("SEWP")  # for now, hardcode SEWP.  Real world would need some logic to determine email type.

    extracted = parser.extract_fields(result['clean_text'], result['attachments'])

    print("----- Extracted Fields -----")
    print(extracted)

    # Step 3: Use supplier matcher
    supplier_matcher = HybridSupplierMatcher(db_conn)

if __name__ == "__main__":
    loader = SupplierDataLoader(csv_path="samples/supplier_products.csv")
    print('Creating Embeddings and Loading DB with mock data...')
    loader.ensure_dummy_suppliers_exist()
    loader.bulk_insert_products()

    run_pipeline('samples/sample_rfq_with_line_items_attachment.eml')
