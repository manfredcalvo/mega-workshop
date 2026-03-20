# Databricks notebook source
# COMMAND ----------
%pip install -r ../../requirements.txt
dbutils.library.restartPython()

# COMMAND ----------
"""
Sets up MLflow GenAI production monitoring for the BCP Knowledge Assistant.

Registers continuous scorers on the KA MLflow experiment so that every
production trace is automatically evaluated with:
  - RetrievalGroundedness: answers are grounded in retrieved documents
  - Guidelines (response_en_espanol): responses are in Spanish
  - Safety:                responses are free of harmful content
  - RelevanceToQuery:      responses are relevant to the question asked

Scorers are idempotent — existing scorers are skipped and only missing ones
are registered and started.

Expects Databricks notebook widget parameters:
  - endpoint_name:   KA serving endpoint name
  - experiment_id:   MLflow experiment ID to attach monitors to
"""

# COMMAND ----------
dbutils.widgets.text("endpoint_name", "", "KA Endpoint Name")
dbutils.widgets.text("experiment_id", "", "MLflow Experiment ID")

endpoint_name = dbutils.widgets.get("endpoint_name")
experiment_id = dbutils.widgets.get("experiment_id")

print(f"Endpoint:      {endpoint_name}")
print(f"Experiment ID: {experiment_id}")

# COMMAND ----------
import mlflow
from mlflow.genai.scorers import (
    RetrievalGroundedness,
    Guidelines,
    Safety,
    RelevanceToQuery,
    ScorerSamplingConfig,
    list_scorers,
)

mlflow.set_experiment(experiment_id=experiment_id)

# COMMAND ----------
# Define the scorers to monitor (same set as model_evaluation.py)
SCORERS_TO_REGISTER = [
    RetrievalGroundedness(),
    Guidelines(
        name="response_en_espanol",
        guidelines=(
            "La respuesta debe estar completamente escrita en español. "
            "No debe contener frases en inglés ni en ningún otro idioma."
        ),
    ),
    Safety(),
    RelevanceToQuery(),
]

# COMMAND ----------
# Get currently registered scorers for idempotency
existing_scorers = {
    s.name
    for s in list_scorers(experiment_id=experiment_id)
}
print(f"Existing monitors: {existing_scorers or '(none)'}")

# COMMAND ----------
# Register and start each scorer that isn't already registered
registered = []
skipped = []

for scorer in SCORERS_TO_REGISTER:
    if scorer.name in existing_scorers:
        print(f"  SKIP (already registered): {scorer.name}")
        skipped.append(scorer.name)
        continue

    (
        scorer
        .register(name=scorer.name, experiment_id=experiment_id)
        .start(sampling_config=ScorerSamplingConfig(sample_rate=1.0))
    )
    print(f"  OK (registered + started): {scorer.name}")
    registered.append(scorer.name)

# COMMAND ----------
print("\n" + "=" * 60)
print("MLflow GenAI Production Monitoring Setup Complete")
print("=" * 60)
print(f"  Experiment ID:   {experiment_id}")
print(f"  Endpoint:        {endpoint_name}")
print(f"  Registered now:  {registered or '(none)'}")
print(f"  Already active:  {skipped or '(none)'}")
print("=" * 60)
print("\nEvery production trace on the KA endpoint will now be")
print("automatically scored. Results appear in the MLflow")
print("Experiment UI under the 'Monitoring' tab.")
