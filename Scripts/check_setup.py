"""
Day 2 - Infrastructure check.

Verifies that every component of the stack works together:
  1. PostgreSQL is reachable and the pgvector extension is enabled
  2. Ollama is reachable and the embedding model returns vectors
  3. pgvector can compare embeddings (semantic similarity sanity check)

Usage:
    pip install -r requirements.txt
    python scripts/check_setup.py
"""

import os
import sys

import ollama
import psycopg
from dotenv import load_dotenv

load_dotenv()

DB_URL = (
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
    f"@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}"
    f"/{os.getenv('POSTGRES_DB')}"
)
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")
client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))

# Two sentences about the same topic, worded differently, and one unrelated sentence.
# A good embedding model puts the first two close together.
SENTENCES = [
    "A jelszónak legalább 12 karakter hosszúnak kell lennie.",
    "Milyen hosszú jelszót kell beállítanom?",
    "A céges parkolóban a látogatók a B szinten parkolhatnak.",
]


def to_pgvector(vec: list[float]) -> str:
    """Convert a Python list to pgvector's text format: [0.1,0.2,...]"""
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


def main():
    # 1. Database
    print("1) PostgreSQL + pgvector ...", end=" ")
    try:
        conn = psycopg.connect(DB_URL)
    except Exception as e:
        print(f"FAILED\n   {e}")
        sys.exit(1)
    with conn:
        row = conn.execute(
            "SELECT extversion FROM pg_extension WHERE extname = 'vector'"
        ).fetchone()
        if not row:
            print("FAILED\n   pgvector extension is not enabled.")
            sys.exit(1)
        print(f"OK (pgvector {row[0]})")

        # 2. Embedding model
        print(f"2) Ollama embedding ({EMBED_MODEL}) ...", end=" ")
        try:
            resp = client.embed(model=EMBED_MODEL, input=SENTENCES)
        except Exception as e:
            print(f"FAILED\n   {e}")
            sys.exit(1)
        vectors = resp.embeddings
        print(f"OK ({len(vectors[0])} dimensions)")

        # 3. Similarity in the database
        print("3) Similarity search in pgvector:")
        query = to_pgvector(vectors[1])  # the question
        for sentence, vec in zip(SENTENCES, vectors):
            # <=> is pgvector's cosine distance; similarity = 1 - distance
            sim = conn.execute(
                "SELECT 1 - (%s::vector <=> %s::vector)", (query, to_pgvector(vec))
            ).fetchone()[0]
            print(f"   {sim:.3f}  {sentence}")

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
