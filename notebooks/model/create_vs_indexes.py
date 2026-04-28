# Databricks notebook source
# COMMAND ----------
%pip install -r ../../requirements.txt
dbutils.library.restartPython()

# COMMAND ----------
"""
Creates Databricks Vector Search indexes for the Megacable RAG agent.

The RAG agent now runs directly in the Databricks App process (Agents on Apps)
so MLflow model registration and serving endpoint deployment are no longer needed.
This notebook only handles data infrastructure:
  1. Load markdown files from two UC Volume directories into Delta tables
  2. Create DELTA_SYNC Vector Search indexes over both tables

The two knowledge sources:
  - output_solutions/       — 8 scraped Megacable enterprise solution pages
  - knowledge_base_md_es/  — ~178 translated telecom support KB docs

Expects Databricks notebook widget parameters:
  - uc_catalog:           Unity Catalog catalog name
  - uc_schema:            Unity Catalog schema name
  - uc_volume:            Unity Catalog volume name
  - resource_name_suffix: Suffix for resource naming (matches var.resource_name_suffix)
"""

# COMMAND ----------
dbutils.widgets.text("uc_catalog",           "", "UC Catalog")
dbutils.widgets.text("uc_schema",            "", "UC Schema")
dbutils.widgets.text("uc_volume",            "", "UC Volume")
dbutils.widgets.text("resource_name_suffix", "", "Resource Name Suffix")

uc_catalog      = dbutils.widgets.get("uc_catalog")
uc_schema       = dbutils.widgets.get("uc_schema")
uc_volume       = dbutils.widgets.get("uc_volume")
resource_suffix = dbutils.widgets.get("resource_name_suffix")

VS_ENDPOINT          = f"megacable-vs-{uc_catalog}"
INDEX_SOLUTIONS      = f"{uc_catalog}.{uc_schema}.megacable_solutions_index"
INDEX_KB             = f"{uc_catalog}.{uc_schema}.megacable_kb_index"
TABLE_SOLUTIONS      = f"{uc_catalog}.{uc_schema}.megacable_solutions_docs"
TABLE_KB             = f"{uc_catalog}.{uc_schema}.megacable_kb_docs"
EMBEDDING_MODEL_NAME = "databricks-gte-large-en"

print(f"UC:        {uc_catalog}.{uc_schema}.{uc_volume}")
print(f"VS:        {VS_ENDPOINT}")
print(f"Indexes:   {INDEX_SOLUTIONS}, {INDEX_KB}")

# COMMAND ----------
# --- Step 1: Load markdown files from UC Volume into Delta tables ---
# Uses Spark binaryFile reader for efficient batch loading (same pattern as translate notebook).
# CDF (Change Data Feed) is required for DELTA_SYNC Vector Search indexes.
from pyspark.sql import functions as F


def load_markdown_to_delta(volume_path, table_name):
    df = (
        spark.read.format("binaryFile")
        .load(f"{volume_path}/*.md")
        .select(
            F.md5(F.col("path")).alias("id"),
            F.regexp_extract(F.col("path"), r"([^/]+)$", 1).alias("filename"),
            F.col("content").cast("string").alias("content"),
        )
    )
    df.write.format("delta").mode("overwrite").saveAsTable(table_name)
    spark.sql(
        f"ALTER TABLE {table_name} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)"
    )
    count = df.count()
    print(f"  {table_name}: {count} documents")
    return count


solutions_path = f"/Volumes/{uc_catalog}/{uc_schema}/{uc_volume}/output_solutions"
kb_path        = f"/Volumes/{uc_catalog}/{uc_schema}/{uc_volume}/knowledge_base_md_es"

print("Loading markdown files into Delta tables...")
n_solutions = load_markdown_to_delta(solutions_path, TABLE_SOLUTIONS)
n_kb        = load_markdown_to_delta(kb_path, TABLE_KB)
print(f"Total: {n_solutions + n_kb} documents loaded")

# COMMAND ----------
# --- Step 2: Create Vector Search endpoint and two DELTA_SYNC indexes ---
from databricks.vector_search.client import VectorSearchClient

vsc = VectorSearchClient(disable_notice=True)

# Create VS endpoint (idempotent)
try:
    vsc.create_endpoint(name=VS_ENDPOINT, endpoint_type="STANDARD")
    print(f"VS endpoint created: {VS_ENDPOINT}")
    vsc.wait_for_endpoint(name=VS_ENDPOINT, verbose=True)
except Exception as e:
    if "already exists" not in str(e).lower():
        raise
    print(f"VS endpoint already exists: {VS_ENDPOINT}")


def create_or_sync_index(index_name, source_table):
    try:
        idx = vsc.create_delta_sync_index(
            endpoint_name=VS_ENDPOINT,
            source_table_name=source_table,
            index_name=index_name,
            pipeline_type="TRIGGERED",
            primary_key="id",
            embedding_source_column="content",
            embedding_model_endpoint_name=EMBEDDING_MODEL_NAME,
        )
        print(f"VS index created: {index_name}")
    except Exception as e:
        if "already exists" not in str(e).lower():
            raise
        print(f"VS index already exists — triggering sync: {index_name}")
        idx = vsc.get_index(VS_ENDPOINT, index_name)
        idx.sync()
    print(f"Waiting for index ready: {index_name}")
    idx.wait_until_ready()
    return idx


from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=2) as executor:
    futures = {
        executor.submit(create_or_sync_index, INDEX_SOLUTIONS, TABLE_SOLUTIONS): "solutions",
        executor.submit(create_or_sync_index, INDEX_KB, TABLE_KB): "kb",
    }
    for future in as_completed(futures):
        name = futures[future]
        future.result()  # re-raise any exception
        print(f"Index ready: {name}")

# COMMAND ----------
print("\n" + "=" * 60)
print("Vector Search indexes ready!")
print("=" * 60)
print(f"  Solutions index: {INDEX_SOLUTIONS}")
print(f"  KB index:        {INDEX_KB}")
print(f"  VS endpoint:     {VS_ENDPOINT}")
print("\nThe RAG agent in the Databricks App will query these indexes directly.")
