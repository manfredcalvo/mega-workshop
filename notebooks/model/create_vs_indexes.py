# Databricks notebook source
# COMMAND ----------
%pip install -r ../../requirements.txt
dbutils.library.restartPython()

# COMMAND ----------
"""
Ingests documents into pgvector tables on Lakebase for the Megacable RAG agent.

Replaces the previous Databricks Vector Search approach. Uses the existing
Lakebase Autoscaling instance (same one used for chat history) to store
embeddings via the pgvector extension — no separate VS endpoint needed.

Steps:
  1. Connect to Lakebase and enable the vector extension
  2. Create schema ai_vectorstore and two tables (solutions + KB)
  3. Load markdown from UC Volume into Spark DataFrames
  4. Embed documents in batches using databricks-gte-large-en (1024 dims)
  5. Upsert embeddings into pgvector tables
  6. Create HNSW indexes for fast cosine similarity search

Expects Databricks notebook widget parameters:
  - uc_catalog:           Unity Catalog catalog name
  - uc_schema:            Unity Catalog schema name
  - uc_volume:            Unity Catalog volume name
  - resource_name_suffix: Suffix for resource naming (matches var.resource_name_suffix)
  - sample_ratio:         Fraction of KB docs to ingest (1.0 = all, 0.05 = 5%)
"""

# COMMAND ----------
dbutils.widgets.text("uc_catalog",           "", "UC Catalog")
dbutils.widgets.text("uc_schema",            "", "UC Schema")
dbutils.widgets.text("uc_volume",            "", "UC Volume")
dbutils.widgets.text("resource_name_suffix", "", "Resource Name Suffix")
dbutils.widgets.text("sample_ratio",         "1.0", "KB Sample Ratio (0.1 = 10%)")

uc_catalog      = dbutils.widgets.get("uc_catalog")
uc_schema       = dbutils.widgets.get("uc_schema")
uc_volume       = dbutils.widgets.get("uc_volume")
resource_suffix = dbutils.widgets.get("resource_name_suffix")
sample_ratio    = float(dbutils.widgets.get("sample_ratio"))

LAKEBASE_PROJECT_ID  = f"megacable-ka-db-{resource_suffix}"
EMBEDDING_MODEL_NAME = "databricks-gte-large-en"
EMBEDDING_DIM        = 1024  # GTE-Large-EN output dimension
TABLE_SOLUTIONS      = "megacable_solutions"
TABLE_KB             = "megacable_kb"

solutions_path = f"/Volumes/{uc_catalog}/{uc_schema}/{uc_volume}/output_solutions"
kb_path        = f"/Volumes/{uc_catalog}/{uc_schema}/{uc_volume}/knowledge_base_md_es"

print(f"UC:        {uc_catalog}.{uc_schema}.{uc_volume}")
print(f"Lakebase:  {LAKEBASE_PROJECT_ID}")
print(f"KB sample: {sample_ratio}")

# COMMAND ----------
# --- Step 1: Connect to Lakebase ---
from databricks.sdk import WorkspaceClient
import psycopg
from pgvector.psycopg import register_vector

w            = WorkspaceClient()
endpoint_name = f"projects/{LAKEBASE_PROJECT_ID}/branches/production/endpoints/primary"
endpoint      = w.postgres.get_endpoint(name=endpoint_name)
pg_host       = endpoint.status.hosts.host
pg_user       = w.current_user.me().user_name

print(f"Lakebase host: {pg_host}")
print(f"Connecting as: {pg_user}")


def get_conn():
    """Open a fresh Lakebase connection with a current OAuth token."""
    cred = w.postgres.generate_database_credential(endpoint=endpoint_name)
    return psycopg.connect(
        host=pg_host,
        dbname="databricks_postgres",
        user=pg_user,
        password=cred.token,
        sslmode="require",
    )


with get_conn() as conn:
    print("Connection successful!")

# COMMAND ----------
# --- Step 2: Enable vector extension and create schema + tables ---
def init_schema():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cur.execute("CREATE SCHEMA IF NOT EXISTS ai_vectorstore")
            for table in (TABLE_SOLUTIONS, TABLE_KB):
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS ai_vectorstore.{table} (
                        id        TEXT PRIMARY KEY,
                        filename  TEXT,
                        content   TEXT,
                        embedding vector({EMBEDDING_DIM})
                    )
                """)
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS {table}_embedding_idx
                    ON ai_vectorstore.{table}
                    USING hnsw (embedding vector_cosine_ops)
                """)
        # committed on context manager exit


init_schema()
print("Schema and tables ready: ai_vectorstore.{megacable_solutions, megacable_kb}")

# COMMAND ----------
# --- Step 3: Load markdown from UC Volume ---
from pyspark.sql import functions as F


def load_markdown(volume_path, sample_ratio=1.0):
    df = (
        spark.read.format("binaryFile")
        .load(f"{volume_path}/*.md")
        .select(
            F.md5(F.col("path")).alias("id"),
            F.regexp_extract(F.col("path"), r"([^/]+)$", 1).alias("filename"),
            F.col("content").cast("string").alias("content"),
        )
    )
    if sample_ratio < 1.0:
        df = df.sample(fraction=sample_ratio, seed=42)
    rows = df.collect()
    print(f"  {len(rows)} documents from {volume_path}")
    return rows


print("Loading markdown files...")
solutions_rows = load_markdown(solutions_path)
kb_rows        = load_markdown(kb_path, sample_ratio=sample_ratio)
print(f"Total: {len(solutions_rows) + len(kb_rows)} documents")

# COMMAND ----------
# --- Step 4 & 5: Embed and upsert into pgvector tables ---
from databricks_langchain import DatabricksEmbeddings

embeddings = DatabricksEmbeddings(endpoint=EMBEDDING_MODEL_NAME)
BATCH_SIZE = 64


def upsert_batch(table, rows):
    texts = [r.content for r in rows]
    vecs  = embeddings.embed_documents(texts)
    with get_conn() as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            for row, vec in zip(rows, vecs):
                cur.execute(
                    f"INSERT INTO ai_vectorstore.{table}"
                    f" (id, filename, content, embedding)"
                    f" VALUES (%s, %s, %s, %s)"
                    f" ON CONFLICT (id) DO UPDATE"
                    f" SET filename=EXCLUDED.filename,"
                    f"     content=EXCLUDED.content,"
                    f"     embedding=EXCLUDED.embedding",
                    (row.id, row.filename, row.content, vec),
                )
        # committed on context manager exit


def ingest_table(table, rows):
    total = len(rows)
    for i in range(0, total, BATCH_SIZE):
        batch = rows[i:i + BATCH_SIZE]
        upsert_batch(table, batch)
        print(f"  {table}: {min(i + BATCH_SIZE, total)}/{total} upserted")
    print(f"  {table}: DONE ({total} documents)")


print("\nIngesting solutions...")
ingest_table(TABLE_SOLUTIONS, solutions_rows)
print("\nIngesting KB...")
ingest_table(TABLE_KB, kb_rows)

# COMMAND ----------
print("\n" + "=" * 60)
print("pgvector ingestion complete!")
print("=" * 60)
print(f"  Schema:    ai_vectorstore")
print(f"  Solutions: {len(solutions_rows)} documents → {TABLE_SOLUTIONS}")
print(f"  KB:        {len(kb_rows)} documents → {TABLE_KB}")
print(f"  Lakebase:  {pg_host}")
print("\nThe RAG agent will query these tables via pgvector cosine similarity.")
