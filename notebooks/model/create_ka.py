# Databricks notebook source
# COMMAND ----------
%pip install -r ../../requirements.txt
dbutils.library.restartPython()

# COMMAND ----------
"""
Creates a Knowledge Assistant (KA) for BCP products using the Databricks SDK.
Configures two data sources: credit cards and loans.

If a KA named "BCP Productos" already exists it is reused — no new KA or
knowledge sources are created. The knowledge sources are always synced at
the end so the latest scraped files are indexed.

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

# COMMAND ----------
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.knowledgeassistants import (
    KnowledgeAssistant,
    KnowledgeSource,
    FilesSpec,
)

w = WorkspaceClient()

# COMMAND ----------
# Check if a KA named "BCP Productos" already exists
KA_DISPLAY_NAME = "BCP Productos"

existing_ka = None
for assistant in w.knowledge_assistants.list_knowledge_assistants():
    if assistant.display_name == KA_DISPLAY_NAME:
        existing_ka = assistant
        break

# COMMAND ----------
if existing_ka:
    ka = existing_ka
    print("Knowledge Assistant already exists — skipping creation.")
    print(f"  Display name: {ka.display_name}")
    print(f"  ID:           {ka.name}")
    print(f"  Endpoint:     {ka.endpoint_name}")
else:
    # Create the Knowledge Assistant
    ka = w.knowledge_assistants.create_knowledge_assistant(
        knowledge_assistant=KnowledgeAssistant(
            display_name=KA_DISPLAY_NAME,
            description=(
                "Este agente se encarga de contestar preguntas relacionadas a las distintas "
                "tarjetas de crédito y préstamos que ofrece BCP a sus clientes. Cada producto "
                "contiene detalles acerca de los beneficios, tasas, tarifas, requisitos, "
                "consideraciones y documentación."
            ),
            instructions=(
                "Siempre responde en español.\n"
                "Asegúrate de utilizar las referencias a páginas que vienen en la documentación."
            ),
        )
    )
    print(f"Knowledge Assistant created: {ka.name}")
    print(f"  Display name: {ka.display_name}")
    print(f"  Endpoint:     {ka.endpoint_name}")

    # Add credit cards data source
    credit_cards_source = w.knowledge_assistants.create_knowledge_source(
        parent=ka.name,
        knowledge_source=KnowledgeSource(
            display_name="Tarjetas de Crédito",
            description=(
                "Contiene archivos en formato markdown con información de cada una de las "
                "tarjetas de crédito que ofrece el banco."
            ),
            source_type="files",
            files=FilesSpec(
                path=f"/Volumes/{uc_catalog}/{uc_schema}/{uc_volume}/output_credit_cards"
            ),
        ),
    )
    print(f"Credit cards source created: {credit_cards_source.name}")

    # Add loans data source
    loans_source = w.knowledge_assistants.create_knowledge_source(
        parent=ka.name,
        knowledge_source=KnowledgeSource(
            display_name="Préstamos",
            description=(
                "Estos documentos contienen información acerca de préstamos que el banco "
                "provee a sus clientes."
            ),
            source_type="files",
            files=FilesSpec(
                path=f"/Volumes/{uc_catalog}/{uc_schema}/{uc_volume}/output_loans"
            ),
        ),
    )
    print(f"Loans source created: {loans_source.name}")

# COMMAND ----------
# Sync knowledge sources and wait until indexing is complete
import time

POLL_INTERVAL_SEC = 30
TIMEOUT_SEC = 60 * 30  # 30 minutes max

from databricks.sdk.service.knowledgeassistants import KnowledgeSourceState

# KnowledgeSourceState values: UPDATING, UPDATED, FAILED_UPDATE
def _get_state(source):
    return source.state if source.state is not None else KnowledgeSourceState.UPDATED

# Check if a sync is already running before triggering a new one
sources = list(w.knowledge_assistants.list_knowledge_sources(parent=ka.name))
current_states = [_get_state(s) for s in sources]
print(f"Current source states: {current_states}")

if any(s == KnowledgeSourceState.UPDATING for s in current_states):
    print("Sync already in progress — skipping sync trigger, waiting for completion...")
else:
    w.knowledge_assistants.sync_knowledge_sources(name=ka.name)
    print("Knowledge sources sync triggered — waiting for completion...")

elapsed = 0
while elapsed < TIMEOUT_SEC:
    sources = list(w.knowledge_assistants.list_knowledge_sources(parent=ka.name))
    states = [_get_state(s) for s in sources]
    print(f"  [{elapsed}s] Source states: {states}")

    if all(s == KnowledgeSourceState.UPDATED for s in states):
        print("All knowledge sources synced successfully.")
        break
    if any(s == KnowledgeSourceState.FAILED_UPDATE for s in states):
        raise RuntimeError(f"One or more knowledge sources failed to sync: {states}")

    time.sleep(POLL_INTERVAL_SEC)
    elapsed += POLL_INTERVAL_SEC
else:
    raise TimeoutError(f"Knowledge sources did not finish syncing within {TIMEOUT_SEC // 60} minutes.")

# COMMAND ----------
print("\n" + "=" * 60)
print("Knowledge Assistant setup complete!")
print("=" * 60)
print(f"  Name:          {ka.display_name}")
print(f"  ID:            {ka.name}")
print(f"  Endpoint:      {ka.endpoint_name}")
print(f"  Experiment ID: {ka.experiment_id}")
print(f"  Sources:")
print(f"    - Tarjetas de Crédito: /Volumes/{uc_catalog}/{uc_schema}/{uc_volume}/output_credit_cards")
print(f"    - Préstamos:           /Volumes/{uc_catalog}/{uc_schema}/{uc_volume}/output_loans")

# Set task values so downstream job tasks can reference them via
# {{tasks.create_ka.values.endpoint_name}} and {{tasks.create_ka.values.experiment_id}}
dbutils.jobs.taskValues.set(key="endpoint_name", value=ka.endpoint_name)
dbutils.jobs.taskValues.set(key="experiment_id", value=str(ka.experiment_id))

# Also exit with JSON for CI/CD pipelines that call this notebook via dbutils.notebook.run()
import json
dbutils.notebook.exit(json.dumps({
    "endpoint_name": ka.endpoint_name,
    "experiment_id": ka.experiment_id,
}))
