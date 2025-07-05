# RFQ Processor

A Python application for ingesting, parsing, and logging RFQ (Request For Quote) emails from an IMAP mailbox or `.eml` files. It supports attachment extraction (PDF, Excel), text normalization, deduplication using `Message-ID`, and embedding product data into a Postgres + `pgvector` database.

---

## Features
-  IMAP and `.eml` email ingestion
-  Deduplication via `Message-ID` and `MessageLogStore`
-  Attachment parsing: PDF, Excel (`.pdf`, `.xlsx`)
-  HTML + plain text email body cleaning
-  `sentence-transformers` for generating vector embeddings
-  PostgreSQL with `pgvector` extension support
-  Bulk supplier product data ingestion from CSV
-  Modular design with testable classes

## Future Ideas
- NLP entity extraction from RFQs (Good for 'delivery_origin' matching)
- Slack or webhook notifications on RFQ ingestion errors
- Admin dashboard to review activity and logs
- Add a 'history score' for suppliers to boost the better suppliers

## What it Does
- Creates a two server environment (Postgres, Python)
- Creates embeddings for the mock data.
- Populates the database with over 100 records for searching.
- Parses one of the sample SWEP emails.
- Prints the extracted data to stdout.
- Searches the database for relevant matches.
- Prints the line item and the search results to stdout.


## Folder Structure
```
rfq_processor/
│
├── app/
│   ├── main.py
│   ├── Dockerfile
│   ├── classes/
│   │   ├── EmailIngestor.py
│   │   ├── EmailPreprocessor.py
│   │   ├── MessageLogStore.py
│   │   ├── BidParserFactory.py
│   │   ├── SupplierDataLoader.py
│   │   ├── HybridSupplierMatcher.py
│   │   ├── PostgresSingleton.py
│   ├── parsers/
│   │   ├── SEWPBidParser.py
│   │   ├── LLMBidParser.py
│   ├── prompts/
│   │   └── llm_bid_parser_prompt.txt
    ├── samples/
│       ├── supplier_products.csv
│       └── sample_rfq_with_line_items_attachment.eml
├── requirements.txt
├── docker-compose.yml
├── README.md
└── pyproject.toml
```

### Clone and Run the repository

```bash
git clone https://github.com/flrogerw/rfq-processor.git
cd rfq-processor
chmod +x app/entrypoint.sh   # Shouldn't have to do this, but won't work if you don't.
docker-compose up --abort-on-container-exit

# Some systems
docker compose up --abort-on-container-exit
```

