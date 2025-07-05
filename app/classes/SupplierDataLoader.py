#!/usr/bin/env python3
"""SupplierDataLoader: Load supplier and product data into a PostgreSQL database.

Includes optional generation of dummy suppliers and vector embeddings for
semantic search via sentence-transformers and pgvector.
"""

import csv
from pathlib import Path

from sentence_transformers import SentenceTransformer

from .PostgresSingleton import PostgresSingleton  # Returns a psycopg2 connection


class SupplierDataLoader:
    """Handles ingestion of supplier and product data into a PostgreSQL database.

    Utilizes sentence-transformers to encode product names into vector embeddings
    for use with the pgvector extension.
    """

    def __init__(self, csv_path: str, model_name: str = "sentence-transformers/paraphrase-mpnet-base-v2") -> None:
        """Initialize the loader with a CSV path and model for generating embeddings.

        Args:
            csv_path (str): Path to the product CSV file.
            model_name (str): SentenceTransformer model name (default: paraphrase-mpnet-base-v2).

        """
        self.csv_path = csv_path
        self.model = SentenceTransformer(model_name)
        self.conn = PostgresSingleton()

    def insert_supplier(self, name: str, email: str) -> int:
        """Insert a supplier into the suppliers table.

        Args:
            name (str): Supplier name.
            email (str): Supplier email address.

        Returns:
            int: The ID of the new supplier or -1 if insertion fails.

        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO suppliers (name, email) VALUES (%s, %s) RETURNING id",
                (name, email),
            )
            supplier_id = cursor.fetchone()[0]
            self.conn.commit()

        except Exception as e:
            print(f"[ERROR] Failed to insert supplier '{name}': {e}")
            self.conn.rollback()
            return -1

        else:
            return supplier_id

    def ensure_dummy_suppliers_exist(self, count: int = 5) -> None:
        """Insert dummy supplier records if none exist, useful for testing/demo.

        Args:
            count (int): Number of dummy suppliers to insert if table is empty.

        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM suppliers")
            existing = cursor.fetchone()[0]

            if existing == 0:
                for i in range(1, count + 1):
                    self.insert_supplier(f"Supplier {i}", f"supplier{i}@example.com")
                print(f"[INFO] Inserted {count} dummy suppliers.")
            else:
                print(f"[INFO] {existing} suppliers already exist. Skipping dummy insert.")

        except Exception as e:
            print(f"[ERROR] Failed to check/insert dummy suppliers: {e}")

    def bulk_insert_products(self) -> None:
        """Load product data from CSV, generate embeddings, and insert into supplier_products table.

        CSV file must have the following headers:
        - name, part_number, category, supplier_id, price, [origin]

        """
        if not Path(self.csv_path).exists():
            print(f"[ERROR] CSV file not found: {self.csv_path}")
            return

        try:
            cursor = self.conn.cursor()
            to_insert = []

            # Read CSV file
            with Path(self.csv_path).open(newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    try:
                        name = row['name'].strip()
                        part_number = row['part_number'].strip()
                        category = row['category'].strip()
                        supplier_id = int(row['supplier_id'])
                        price = float(row['price'])
                        origin = row.get('origin', 'United States').strip()

                        # Compute vector embedding for product name
                        embedding = self.model.encode(name).tolist()

                        to_insert.append((
                            name,
                            part_number,
                            category,
                            embedding,
                            supplier_id,
                            price,
                            origin,
                        ))

                    except KeyError as ke:
                        print(f"[WARN] Skipping row with missing field: {ke}")
                    except Exception as e:
                        print(f"[WARN] Failed to process row: {e}")

            if not to_insert:
                print("[WARN] No valid rows to insert.")
                return

            # Bulk insert using psycopg2 mogrify for efficient parameterization
            args_str = ",".join(
                cursor.mogrify("(%s, %s, %s, %s, %s, %s, %s)", row).decode("utf-8")
                for row in to_insert
            )

            cursor.execute(
                f"""
                INSERT INTO supplier_products
                (name, part_number, category, embedding, supplier_id, price, origin)
                VALUES {args_str}
                """,
            )
            self.conn.commit()
            print(f"[INFO] Inserted {len(to_insert)} products from CSV.")

        except Exception as e:
            print(f"[ERROR] Failed to bulk insert products: {e}")
            self.conn.rollback()
