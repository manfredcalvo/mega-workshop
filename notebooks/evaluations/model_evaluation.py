# Databricks notebook source
# COMMAND ----------
%pip install -r ../../requirements.txt
dbutils.library.restartPython()

# COMMAND ----------
"""
Evaluates the Megacable RAG Agent using MLflow GenAI evaluation.

Loads the agent directly via build_graph() so that RETRIEVER spans are
emitted in the calling notebook's trace context, which allows
RetrievalGroundedness to inspect retrieved documents.

Scores responses with:
  - RetrievalGroundedness: answers are grounded in retrieved documents
  - Guidelines:            responses are in Spanish
  - Safety:                responses are free of harmful content
  - RelevanceToQuery:      responses are relevant to the question asked

Expects Databricks notebook widget parameters:
  - experiment_id:       MLflow experiment ID to log results to
  - uc_catalog:          UC catalog name (unused in pgvector mode, kept for compat)
  - uc_schema:           UC schema name (unused in pgvector mode, kept for compat)
  - lakebase_project_id: Lakebase project ID (e.g. megacable-ka-db-prod)
"""

# COMMAND ----------
dbutils.widgets.text("experiment_id",       "", "MLflow Experiment ID")
dbutils.widgets.text("uc_catalog",          "", "UC Catalog")
dbutils.widgets.text("uc_schema",           "", "UC Schema")
dbutils.widgets.text("lakebase_project_id", "", "Lakebase Project ID")

experiment_id       = dbutils.widgets.get("experiment_id")
uc_catalog          = dbutils.widgets.get("uc_catalog")
uc_schema           = dbutils.widgets.get("uc_schema")
lakebase_project_id = dbutils.widgets.get("lakebase_project_id")

print(f"Experiment ID:  {experiment_id}")
print(f"Lakebase:       {lakebase_project_id}")

# COMMAND ----------
import mlflow
import pandas as pd
from mlflow.entities import SpanType

mlflow.set_experiment(experiment_id=experiment_id)

# COMMAND ----------
# --- Evaluation dataset ---
# Custom questions covering Megacable enterprise solution categories.
# inputs.input follows the KA endpoint message format (list of role/content dicts).
# expectations.expected_response provides reference answers for scorers.
eval_data = pd.DataFrame([
    # ── Conectividad ──────────────────────────────────────────────────────────
    {
        "inputs": {"input": [{"role": "user", "content": "¿Qué soluciones de conectividad ofrece Megacable para empresas?"}]},
        "expectations": {"expected_response": (
            "Megacable ofrece Internet Dedicado, Internet Dedicado con Seguridad Administrada, "
            "Cloud Connect, Mega Móvil, Líneas Privadas Ethernet y Redes GPON, con cobertura "
            "nacional y soporte NOC 24/7."
        )},
    },
    {
        "inputs": {"input": [{"role": "user", "content": "¿Qué es Cloud Connect y para qué sirve?"}]},
        "expectations": {"expected_response": (
            "Cloud Connect es un enlace privado y seguro directo a la nube que permite a las "
            "empresas conectarse sin pasar por internet público, garantizando mayor seguridad "
            "y rendimiento para cargas de trabajo en la nube."
        )},
    },
    # ── Ciberseguridad ────────────────────────────────────────────────────────
    {
        "inputs": {"input": [{"role": "user", "content": "¿Qué soluciones de ciberseguridad ofrece Megacable?"}]},
        "expectations": {"expected_response": (
            "Megacable ofrece SASE, Firewall as a Service, Ethical Hacking, SOC as a Service, "
            "XDR, Secure Web, Respuesta a Incidentes, Ciberpatrullaje, Clean Pipe (DDoS) y ZTNA, "
            "con monitoreo 24/7 y estrategias adaptadas a cada entorno empresarial."
        )},
    },
    {
        "inputs": {"input": [{"role": "user", "content": "¿Qué es SASE y cómo protege a mi empresa?"}]},
        "expectations": {"expected_response": (
            "SASE (Secure Access Service Edge) es una arquitectura basada en la nube que combina "
            "servicios de red y ciberseguridad en una sola plataforma. Protege usuarios, "
            "aplicaciones y datos en cualquier dispositivo y ubicación."
        )},
    },
    # ── Symphony / Colaboración ───────────────────────────────────────────────
    {
        "inputs": {"input": [{"role": "user", "content": "¿Qué es Symphony y qué servicios incluye?"}]},
        "expectations": {"expected_response": (
            "Symphony es la plataforma de comunicaciones unificadas de Megacable que integra "
            "UCaaS (comunicaciones unificadas como servicio) y CCaaS (contact center como servicio) "
            "en una experiencia omnicanal para mejorar la productividad y la atención al cliente."
        )},
    },
    # ── Nube / Hiperconvergencia ──────────────────────────────────────────────
    {
        "inputs": {"input": [{"role": "user", "content": "¿Qué opciones de nube tiene Megacable para empresas?"}]},
        "expectations": {"expected_response": (
            "Megacable ofrece Nube Pública, Nube Local Privada, Backup as a Service, "
            "DRP (Disaster Recovery), Máquinas Virtuales, Almacenamiento y Bare Metal, "
            "dentro de su portafolio de Hiperconvergencia Empresarial."
        )},
    },
    # ── Data Center ───────────────────────────────────────────────────────────
    {
        "inputs": {"input": [{"role": "user", "content": "¿Qué servicios ofrece el Megacable Data Center?"}]},
        "expectations": {"expected_response": (
            "El Megacable Data Center ofrece Data Center Core, Coubicación (colocation), "
            "Edge Data Center, Conectividad y servicio de Manos y Ojos Remotos para gestión "
            "física de equipos sin necesidad de desplazamiento."
        )},
    },
    # ── Seguridad Física ──────────────────────────────────────────────────────
    {
        "inputs": {"input": [{"role": "user", "content": "¿Qué soluciones de seguridad física ofrece Megacable?"}]},
        "expectations": {"expected_response": (
            "Megacable ofrece Cámaras de Vigilancia, Análisis de Video inteligente, "
            "Centros de Monitoreo, Plataforma de Despacho, Sistema de Gestión de Video, "
            "Control de Accesos, Detectores de Incendio y Sala de Crisis."
        )},
    },
    # ── Carriers ──────────────────────────────────────────────────────────────
    {
        "inputs": {"input": [{"role": "user", "content": "¿Qué servicios mayoristas ofrece Megacable para carriers?"}]},
        "expectations": {"expected_response": (
            "Para carriers, Megacable ofrece servicios Wavelength de alta capacidad y "
            "frecuencias de 23 GHz para enlaces de última milla y backhaul empresarial."
        )},
    },
    # ── Base de Conocimiento ──────────────────────────────────────────────────
    {
        "inputs": {"input": [{"role": "user", "content": "¿Cómo puedo reportar un incidente de seguridad o falla en el servicio?"}]},
        "expectations": {"expected_response": (
            "Puedes reportar incidentes a través del equipo de soporte técnico de Megacable. "
            "El proceso incluye identificar el tipo de incidente, documentar los síntomas "
            "y contactar al canal de atención correspondiente para una respuesta oportuna."
        )},
    },
])

print(f"Evaluation dataset: {len(eval_data)} questions")
eval_data.head()

# COMMAND ----------
from mlflow.genai.scorers import (
    RetrievalGroundedness,
    Guidelines,
    Safety,
    RelevanceToQuery,
)

# --- Scorers ---
evaluation_scorers = [
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
# --- Build agent from shared package ---
# Agent logic lives in megacable_agent/core.py — the same code used by the app.
# We rebuild it directly here (not via mlflow.pyfunc.load_model) so that RETRIEVER
# spans land in mlflow.genai.evaluate's trace context, giving non-zero groundedness.
import sys

# Add repo root to path so megacable_agent package is importable in this notebook.
_ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
_repo_root = "/Workspace" + "/".join(_ctx.notebookPath().get().split("/")[:-3])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from databricks.sdk import WorkspaceClient
import psycopg
from megacable_agent.core import build_graph

w = WorkspaceClient()
_endpoint_name = f"projects/{lakebase_project_id}/branches/production/endpoints/primary"
_endpoint      = w.postgres.get_endpoint(name=_endpoint_name)
_pg_host       = _endpoint.status.hosts.host
_pg_user       = w.current_user.me().user_name

print(f"Lakebase host: {_pg_host}")


def pg_conn_fn() -> dict:
    """Fresh psycopg connection kwargs for each retrieval call."""
    cred = w.postgres.generate_database_credential(endpoint=_endpoint_name)
    return {
        "host": _pg_host,
        "dbname": "databricks_postgres",
        "user": _pg_user,
        "password": cred.token,
        "sslmode": "require",
    }


graph = build_graph(pg_conn_fn=pg_conn_fn)


# mlflow.genai.evaluate unpacks the `inputs` dict as kwargs — parameter must be "input"
@mlflow.trace(span_type=SpanType.AGENT)
def predict_fn(input):
    result = graph.invoke({"messages": input})
    for msg in reversed(result["messages"]):
        if getattr(msg, "type", None) == "ai":
            return msg.content
    return str(result["messages"][-1].content)


# COMMAND ----------
# --- Run evaluation ---
with mlflow.start_run(run_name="megacable_rag_evaluation"):
    results = mlflow.genai.evaluate(
        data=eval_data,
        predict_fn=predict_fn,
        scorers=evaluation_scorers,
    )

print("\nEvaluation complete!")
print("=" * 60)

# COMMAND ----------
# --- Display results summary ---
results_df = results.tables["eval_results"]
display(results_df)

# COMMAND ----------
# --- Aggregate scores ---
score_columns = [c for c in results_df.columns if c.endswith("/value") or c.endswith("/pass")]
if score_columns:
    print("\nAggregate scores:")
    print("-" * 40)
    for col in score_columns:
        yes_rate = (results_df[col].astype(str).str.lower() == "yes").mean() * 100
        print(f"  {col:<45} {yes_rate:.1f}% yes")

# COMMAND ----------
# --- Quality gate: RetrievalGroundedness pass rate must be > 80% ---
RETRIEVAL_GROUNDEDNESS_THRESHOLD = 0.80

groundedness_col = next(
    (c for c in results_df.columns if "retrieval_groundedness" in c.lower() and c.endswith("/value")),
    None,
)

if groundedness_col is None:
    raise ValueError(
        "RetrievalGroundedness score column not found in evaluation results. "
        "Cannot validate quality gate."
    )

groundedness_pass_rate = (results_df[groundedness_col].astype(str).str.lower() == "yes").mean()

print("\n" + "=" * 60)
print("Quality Gate: RetrievalGroundedness")
print("=" * 60)
print(f"  Pass rate: {groundedness_pass_rate:.1%}")
print(f"  Threshold: {RETRIEVAL_GROUNDEDNESS_THRESHOLD:.1%}")
print(f"  Status:    {'PASSED ✓' if groundedness_pass_rate > RETRIEVAL_GROUNDEDNESS_THRESHOLD else 'FAILED ✗'}")

if groundedness_pass_rate <= RETRIEVAL_GROUNDEDNESS_THRESHOLD:
    raise ValueError(
        f"Quality gate FAILED: RetrievalGroundedness pass rate {groundedness_pass_rate:.1%} "
        f"is <= threshold {RETRIEVAL_GROUNDEDNESS_THRESHOLD:.1%}. "
        "The RAG agent responses are not sufficiently grounded in the retrieved documents."
    )
