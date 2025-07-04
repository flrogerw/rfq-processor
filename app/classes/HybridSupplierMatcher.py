from typing import List, Tuple, Dict, Optional, Any
import psycopg2
import numpy as np
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

    def __init__(self, db_conn: psycopg2.extensions.connection, model_name: str = "sentence-transformers/paraphrase-mpnet-base-v2"):
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
                        item_name: str,
                        item_part_number: Optional[str] = None,
                        top_k: int = 5,
                        pn_boost_weight: float = 0.3,
                        vector_weight: float = 0.7,
                        similarity_threshold: float = 0.6) -> List[Tuple[Dict[str, Any], float]]:
        """
        Matches a single RFQ line item to supplier products using a hybrid score based on
        vector similarity and part number similarity.

        Args:
            item_name (str): Description of the product to be matched.
            item_part_number (Optional[str]): Part number to boost matching accuracy.
            top_k (int): Maximum number of matches to return.
            pn_boost_weight (float): Weight assigned to part number similarity.
            vector_weight (float): Weight assigned to vector similarity.
            similarity_threshold (float): Minimum score required for inclusion in results.

        Returns:
            List[Tuple[Dict[str, Any], float]]: List of matching supplier products with scores.
        """
        vector = self._encode_description(item_name)

        cur = self.db.cursor()
        query = """
            SELECT sp.id, sp.name, sp.part_number, sp.embedding, s.name AS supplier_name, s.email
            FROM supplier_products sp
            JOIN suppliers s ON sp.supplier_id = s.id
            ORDER BY sp.embedding <=> %s
            LIMIT %s
        """
        cur.execute(query, (vector, top_k * 3))  # Overfetch to allow better scoring

        results = []
        for row in cur.fetchall():
            product = {
                "id": row[0],
                "name": row[1],
                "part_number": row[2],
                "supplier_name": row[4],
                "email": row[5]
            }

            # Compute cosine similarity (1 - cosine distance)
            vector_score = np.dot(vector, row[3]) / (np.linalg.norm(vector) * np.linalg.norm(row[3]))
            vector_score = max(0.0, min(1.0, vector_score))

            # Compute part number match score
            pn_score = self._part_number_similarity(item_part_number, product["part_number"])
            if item_part_number and item_part_number == product["part_number"]:
                pn_score += 0.1  # Exact match boost

            # Final hybrid score
            hybrid_score = (vector_weight * vector_score) + (pn_boost_weight * pn_score)

            if hybrid_score >= similarity_threshold:
                results.append((product, round(hybrid_score, 4)))

        # Sort by final score
        return sorted(results, key=lambda x: x[1], reverse=True)[:top_k]
