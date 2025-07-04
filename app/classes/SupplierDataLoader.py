import csv
import os
from sentence_transformers import SentenceTransformer
from .PostgresSingleton import PostgresSingleton  # Returns a psycopg2 connection


class SupplierDataLoader:
    """
    Handles loading supplier and product data into a PostgreSQL database.
    Uses SentenceTransformer to compute embeddings for product names.
    """

    def __init__(self, csv_path: str, model_name: str = "sentence-transformers/paraphrase-mpnet-base-v2"):
        """
        Initializes the data loader with a CSV path and embedding model.

        Args:
            csv_path (str): Path to the CSV file containing product data.
            model_name (str): Hugging Face model name for generating embeddings.
        """
        self.csv_path = csv_path
        self.model = SentenceTransformer(model_name)
        self.conn = PostgresSingleton()

    def insert_supplier(self, name: str, email: str) -> int:
        """
        Inserts a supplier into the database and returns the new supplier ID.

        Args:
            name (str): Supplier name.
            email (str): Supplier email address.

        Returns:
            int: The ID of the newly inserted supplier.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO suppliers (name, email) VALUES (%s, %s) RETURNING id",
                (name, email)
            )
            supplier_id = cursor.fetchone()[0]
            self.conn.commit()
            return supplier_id
        except Exception as e:
            print(f"[ERROR] Failed to insert supplier '{name}': {e}")
            self.conn.rollback()
            return -1

    def ensure_dummy_suppliers_exist(self, count: int = 5):
        """
        Ensures dummy supplier records exist for testing/demo purposes.

        Args:
            count (int): Number of dummy suppliers to insert if none exist.
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM suppliers")
            existing = cursor.fetchone()[0]

            if existing == 0:
                for i in range(1, count + 1):
                    self.insert_supplier(f"Supplier {i}", f"supplier{i}@example.com")
                print(f"Inserted {count} dummy suppliers.")
            else:
                print(f"{existing} suppliers already exist. Skipping dummy insert.")
        except Exception as e:
            print(f"[ERROR] Failed to check or insert dummy suppliers: {e}")

    def bulk_insert_products(self):
        """
        Loads product data from CSV, generates embeddings, and inserts into the database.
        """
        if not os.path.exists(self.csv_path):
            print(f"[ERROR] CSV file not found: {self.csv_path}")
            return

        try:
            cursor = self.conn.cursor()
            to_insert = []

            with open(self.csv_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                for row in reader:
                    name = row['name'].strip()
                    part_number = row['part_number'].strip()
                    category = row['category'].strip()
                    supplier_id = int(row['supplier_id'])
                    price = float(row['price'])
                    origin = row.get('origin', 'United States').strip()

                    # Generate vector embedding for product name
                    embedding = self.model.encode(name).tolist()
                    to_insert.append((name, part_number, category, embedding, supplier_id, price, origin))

            # Prepare bulk insert SQL
            args_str = ",".join(
                cursor.mogrify("(%s, %s, %s, %s, %s, %s, %s)", row).decode("utf-8")
                for row in to_insert
            )

            cursor.execute(
                f"""
                INSERT INTO supplier_products
                (name, part_number, category, embedding, supplier_id, price, origin)
                VALUES {args_str}
                """
            )
            self.conn.commit()
            print(f"Inserted {len(to_insert)} products from CSV.")

        except Exception as e:
            print(f"[ERROR] Failed to bulk insert products: {e}")
            self.conn.rollback()

