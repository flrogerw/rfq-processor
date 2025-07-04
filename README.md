# RFQ Processor

A robust Python application for ingesting, parsing, and logging RFQ (Request For Quote) emails from an IMAP mailbox or `.eml` files. It supports attachment extraction (PDF, Excel), text normalization, deduplication using `Message-ID`, and embedding product data into a Postgres + `pgvector` database.

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

---

## Project Structure
```
├── app/
│ ├── classes/
│ │ ├── EmailIngestor.py
│ │ ├── EmailPreprocessor.py
│ │ ├── MessageLogStore.py
│ │ └── PostgresSingleton.py
│ ├── utils/
│ │ └── SupplierDataLoader.py
│ └── main.py
├── samples/
│ └── supplier_products.csv
├── .env
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone and Run the repository

```bash
git clone https://github.com/flrogerw/rfq-processor.git
cd rfq-processor
docker compose up
```
## Future Ideas
- NLP entity extraction from RFQs
- Slack or webhook notifications on RFQ ingestion errors
- Admin dashboard to review activity

