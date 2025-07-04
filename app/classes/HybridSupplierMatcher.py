from typing import List, Tuple, Dict, Optional, Any
import psycopg2
from sentence_transformers import SentenceTransformer
from difflib import SequenceMatcher


class HybridSupplierMatcher:
    """
    HybridSupplierMatcher performs supplier matching by combining semantic vector similarity
    (via sentence-transformer embeddings) with part number fuzzy matching. It retrieves potential
    supplier products from a PostgreSQL database that uses the `pgvector` extension for similarity search.

    This class is designed to support Request for Quote (RFQ) workflows where incoming line items
    must be matched against an internal catalog of supplier offerings.

    Parameters:
        db_conn (psycopg2.extensions.connection): Active connection to a PostgreSQL database.
        model_name (str): Name of the sentence-transformers model to use for generating embeddings.
    """

    def __init__(self, db_conn: psycopg2.extensions.connection,
                 model_name: str = "sentence-transformers/paraphrase-mpnet-base-v2"):
        self.db = db_conn
        self.model = SentenceTransformer(model_name)

    def _encode_description(self, description: str) -> List[float]:
        """
        Generates a sentence embedding for a given item description.

        Args:
            description (str): Item name or description to be encoded.

        Returns:
            List[float]: 768-dimensional embedding vector.
        """
        embedding = self.model.encode(description)
        return embedding.tolist()

    @staticmethod
    def _part_number_similarity(item_pn: Optional[str], db_pn: Optional[str]) -> float:
        """
        Computes normalized fuzzy similarity score between part numbers.

        Args:
            item_pn (str): Part number from the incoming RFQ item.
            db_pn (str): Part number from the supplier catalog.

        Returns:
            float: Score between 0.0 and 1.0.
        """
        if not item_pn or not db_pn:
            return 0.0
        return SequenceMatcher(None, item_pn.lower(), db_pn.lower()).ratio()

    def match_suppliers(self,
                        line_item: Dict[str, Any],
                        top_k: int = 5,
                        pn_boost_weight: float = 0.3,
                        vector_weight: float = 0.7,
                        similarity_threshold: float = 0.6) -> List[Tuple[Dict[str, Any], float]]:
        item_name = line_item["name"]
        item_part_number = line_item.get("part_number")
        delivery_region = line_item.get("delivery_region")

        vector = self._encode_description(item_name)

        base_query = f"""
            SELECT
                sp.id,
                sp.name,
                sp.part_number,
                s.name AS supplier_name,
                s.email,
                1 - (sp.embedding <=> %s::vector) AS vector_similarity,
                CASE
                    WHEN %s IS NOT NULL AND sp.part_number = %s THEN 1.0
                    WHEN %s IS NOT NULL THEN similarity(sp.part_number, %s)
                    ELSE 0.0
                END AS pn_score,
                ({vector_weight} * (1 - (sp.embedding <=> %s::vector))) +
                ({pn_boost_weight} * CASE
                    WHEN %s IS NOT NULL AND sp.part_number = %s THEN 1.0
                    WHEN %s IS NOT NULL THEN similarity(sp.part_number, %s)
                    ELSE 0.0
                END) AS hybrid_score
            FROM supplier_products sp
            JOIN suppliers s ON sp.supplier_id = s.id
            WHERE
                ({vector_weight} * (1 - (sp.embedding <=> %s::vector))) +
                ({pn_boost_weight} * CASE
                    WHEN %s IS NOT NULL AND sp.part_number = %s THEN 1.0
                    WHEN %s IS NOT NULL THEN similarity(sp.part_number, %s)
                    ELSE 0.0
                END) >= %s
        """

        params = [
            vector,
            item_part_number, item_part_number,
            item_part_number, item_part_number,
            vector,
            item_part_number, item_part_number,
            item_part_number, item_part_number,
            vector,
            item_part_number, item_part_number,
            item_part_number, item_part_number,
            similarity_threshold
        ]

        # 🔒 Conditionally add origin filter
        if delivery_region:
            base_query += " AND sp.origin = %s"
            params.append(delivery_region)

        base_query += " ORDER BY hybrid_score DESC LIMIT %s"
        params.append(top_k)

        cur = self.db.cursor()
        cur.execute(base_query, params)

        results = []
        for row in cur.fetchall():
            product = {
                "id": row[0],
                "name": row[1],
                "part_number": row[2],
                "supplier_name": row[3],
                "email": row[4]
            }
            score = row[7]  # hybrid_score
            results.append((product, round(score, 4)))

        return results
