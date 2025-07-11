#!/usr/bin/env python3
"""HybridSupplierMatcher module.

Performs hybrid product matching using vector similarity and part number fuzzy matching.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import TYPE_CHECKING, Any

from sentence_transformers import SentenceTransformer

if TYPE_CHECKING:
    import psycopg2


class HybridSupplierMatcher:
    """HybridSupplierMatcher performs supplier matching for RFQ items.

    It combines semantic vector similarity (via sentence-transformer embeddings)
    with fuzzy part number matching using trigram similarity in PostgreSQL.

    Attributes:
        db (psycopg2.extensions.connection): A connection to the PostgreSQL database.
        model (SentenceTransformer): Model used to compute vector embeddings.

    """

    def __init__(
        self,
        db_conn: psycopg2.extensions.connection,
        model_name: str = "sentence-transformers/paraphrase-mpnet-base-v2",
    ) -> None:
        """Initialize the matcher with a database connection and embedding model.

        Args:
            db_conn (psycopg2.extensions.connection): PostgreSQL database connection.
            model_name (str): Name of the sentence-transformers model to use.

        """
        self.db = db_conn
        self.model = SentenceTransformer(model_name)

    def _encode_description(self, description: str) -> list[float]:
        """Generate an embedding for a given item description.

        Args:
            description (str): Item name or description.

        Returns:
            list[float]: Embedding vector as a list of floats.

        """
        try:
            embedding = self.model.encode(description)
            return embedding.tolist()
        except Exception as e:
            print(f"[ERROR] Failed to encode description: {e}")
            return []

    @staticmethod
    def _part_number_similarity(item_pn: str | None, db_pn: str | None) -> float:
        """Compute fuzzy similarity score between part numbers.

        Args:
            item_pn (str | None): Part number from RFQ item.
            db_pn (str | None): Part number from supplier catalog.

        Returns:
            float: Score between 0.0 and 1.0 using sequence matching.

        """
        if not item_pn or not db_pn:
            return 0.0
        return SequenceMatcher(None, item_pn.lower(), db_pn.lower()).ratio()

    def match_suppliers(
        self,
        line_item: dict[str, Any],
        top_k: int = 5,
        pn_boost_weight: float = 0.3,
        vector_weight: float = 0.7,
        similarity_threshold: float = 0.6,
    ) -> list[tuple[dict[str, Any], float]]:
        """Match an RFQ line item against supplier products using hybrid similarity.

        Args:
            line_item (dict): Contains name, part_number, and optionally delivery_region.
            top_k (int): Number of top results to return.
            pn_boost_weight (float): Weight given to part number similarity.
            vector_weight (float): Weight given to vector similarity.
            similarity_threshold (float): Minimum hybrid score to include a result.

        Returns:
            list[tuple[dict, float]]: List of matching products with hybrid score.

        """
        item_name = line_item["name"]
        item_part_number = line_item.get("part_number")
        delivery_region = line_item.get("delivery_region")

        # Generate embedding vector
        vector = self._encode_description(item_name)

        if not vector:
            return []

        # Define the base query string (with format placeholders for weights)
        base_query = f"""
        WITH base_scores AS (
            SELECT 
                sp.id,
                sp.name,
                sp.part_number,
                sp.origin,
                s.name AS supplier_name,
                s.email,
                1 - (sp.embedding <=> %s::vector) AS vector_similarity,
                CASE
                    WHEN %s IS NOT NULL THEN similarity(sp.part_number, %s)
                    ELSE 0.0
                END AS pn_score
            FROM supplier_products sp
            JOIN suppliers s ON sp.supplier_id = s.id
            WHERE 1=1
        """

        # Initialize query params
        params = [
            vector,
            item_part_number, item_part_number
        ]

        # Conditionally add delivery_region filter
        if delivery_region:
            base_query += " AND sp.origin = %s"
            params.append(delivery_region)

        # Append hybrid_score computation and final selection
        base_query += f"""
        ),
        ranked AS (
            SELECT *,
                ({vector_weight} * vector_similarity) + ({pn_boost_weight} * pn_score) AS hybrid_score
            FROM base_scores
        )
        SELECT * FROM ranked
        WHERE hybrid_score >= %s
        """
        params.append(similarity_threshold)
        base_query += " ORDER BY hybrid_score DESC LIMIT %s"
        params.append(top_k)

        results = []

        try:
            cur = self.db.cursor()
            cur.execute(base_query, params)

            for row in cur.fetchall():
                product = {
                    "id": row[0],
                    "name": row[1],
                    "part_number": row[2],
                    "supplier_name": row[3],
                    "email": row[4],
                }
                score = row[7]  # hybrid_score
                results.append((product, round(score, 4)))

        except Exception as e:
            print(f"[ERROR] Failed to execute hybrid match query: {e}")

        return results
