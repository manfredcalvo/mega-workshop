# Databricks notebook source
# COMMAND ----------
"""
Translates knowledge base markdown files from English to Spanish
using Databricks AI Functions (ai_translate).

Reads all markdown files at once with Spark's binaryFile reader,
applies ai_translate() across the entire DataFrame in a single
distributed Spark job, then collects and writes each file.

Idempotent: skips files that have already been translated.

Expects Databricks notebook widget parameters:
  - uc_catalog: Unity Catalog catalog name
  - uc_schema: Unity Catalog schema name
  - uc_volume: Unity Catalog volume name
"""

# COMMAND ----------
dbutils.widgets.text("uc_catalog", "", "UC Catalog")
dbutils.widgets.text("uc_schema", "", "UC Schema")
dbutils.widgets.text("uc_volume", "", "UC Volume")

uc_catalog = dbutils.widgets.get("uc_catalog")
uc_schema = dbutils.widgets.get("uc_schema")
uc_volume = dbutils.widgets.get("uc_volume")

INPUT_DIR  = f"/Volumes/{uc_catalog}/{uc_schema}/{uc_volume}/knowledge_base_md"
OUTPUT_DIR = f"/Volumes/{uc_catalog}/{uc_schema}/{uc_volume}/knowledge_base_md_es"

print(f"Input:  {INPUT_DIR}")
print(f"Output: {OUTPUT_DIR}")

# COMMAND ----------
import os
from pyspark.sql import functions as F

os.makedirs(OUTPUT_DIR, exist_ok=True)

# COMMAND ----------
# Discover which files still need translation (idempotent)
already_done = set(os.listdir(OUTPUT_DIR))

all_files_df = (
    spark.read.format("binaryFile")
    .load(f"{INPUT_DIR}/*.md")
    .select(
        F.regexp_extract(F.col("path"), r"([^/]+)$", 1).alias("filename"),
        F.col("content").cast("string").alias("content"),
    )
)

pending_df = all_files_df.filter(~F.col("filename").isin(already_done))

total   = all_files_df.count()
pending = pending_df.count()
print(f"Total files:   {total}")
print(f"Already done:  {total - pending}")
print(f"To translate:  {pending}")

# COMMAND ----------
if pending == 0:
    print("Nothing to translate — all files already exist in output directory.")
else:
    # Apply ai_translate() across all pending rows in a single Spark job
    translated_df = pending_df.withColumn(
        "translated",
        F.expr("ai_translate(content, 'es')"),
    ).select("filename", "translated")

    # Collect and write each file
    rows = translated_df.collect()
    failed = 0
    for row in rows:
        try:
            out_path = os.path.join(OUTPUT_DIR, row["filename"])
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(row["translated"])
        except Exception as e:
            print(f"  ERROR writing {row['filename']}: {e}")
            failed += 1

    print(f"\nWritten: {len(rows) - failed}  |  Failed: {failed}")
    if failed > 0:
        raise RuntimeError(f"{failed} file(s) failed to write. Check logs above.")

# COMMAND ----------
print("\n" + "=" * 60)
print("Translation complete!")
print("=" * 60)
print(f"  Output: {OUTPUT_DIR}")
print(f"  Files:  {len(os.listdir(OUTPUT_DIR))}")
