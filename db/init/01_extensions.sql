-- Runs automatically on the first start of an empty database.
-- Enables pgvector: the "vector" data type and similarity search operators.
CREATE EXTENSION IF NOT EXISTS vector;
