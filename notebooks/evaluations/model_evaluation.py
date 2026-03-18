# Databricks notebook source
# COMMAND ----------
%pip install -r ../../requirements.txt
dbutils.library.restartPython()

# COMMAND ----------
"""
Evaluates the BCP Knowledge Assistant using MLflow GenAI evaluation.

Runs a custom set of questions about BCP credit cards and loans through
the KA serving endpoint and scores responses with:
  - RetrievalGroundedness: answers are grounded in retrieved documents
  - Guidelines:            responses are in Spanish
  - Safety:                responses are free of harmful content
  - RelevanceToQuery:      responses are relevant to the question asked

Expects Databricks notebook widget parameters:
  - endpoint_name:   KA serving endpoint name
  - experiment_id:   MLflow experiment ID to log results to
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
import pandas as pd

mlflow.set_experiment(experiment_id=experiment_id)

# COMMAND ----------
# --- Evaluation dataset ---
# Custom questions covering credit cards and loans product categories.
# inputs.input follows the KA endpoint message format (list of role/content dicts).
# expectations.expected_response provides reference answers for scorers.
eval_data = pd.DataFrame([
    # ── Credit cards ──────────────────────────────────────────────────────────
    {
        "inputs": {"input": [{"role": "user", "content": "¿Cuáles son las tarjetas de crédito que ofrece el BCP?"}]},
        "expectations": {"expected_response": (
            "BCP ofrece tarjetas de crédito Visa y Mastercard en distintas categorías: "
            "clásica, gold, platinum y world, entre otras, con beneficios diferenciados "
            "como acumulación de puntos, seguros y acceso a salas VIP."
        )},
    },
    {
        "inputs": {"input": [{"role": "user", "content": "¿Qué beneficios tiene la tarjeta de crédito Platinum del BCP?"}]},
        "expectations": {"expected_response": (
            "La tarjeta Platinum ofrece acumulación de puntos en compras, acceso a salas "
            "VIP en aeropuertos, seguro de viaje, protección de compras y tasas preferenciales."
        )},
    },
    {
        "inputs": {"input": [{"role": "user", "content": "¿Cuál es la tasa de interés de la tarjeta de crédito clásica del BCP?"}]},
        "expectations": {"expected_response": (
            "La tasa de interés de la tarjeta clásica varía según el perfil del cliente; "
            "consulta el tarifario vigente en la web del BCP para los valores exactos."
        )},
    },
    {
        "inputs": {"input": [{"role": "user", "content": "¿Qué documentos necesito para solicitar una tarjeta de crédito BCP?"}]},
        "expectations": {"expected_response": (
            "Generalmente se requiere DNI vigente, recibo de servicios o documento de "
            "domicilio, y sustento de ingresos (boleta de pago, declaración de renta, etc.)."
        )},
    },
    {
        "inputs": {"input": [{"role": "user", "content": "¿Cómo puedo acumular puntos con mi tarjeta BCP?"}]},
        "expectations": {"expected_response": (
            "Los puntos se acumulan automáticamente en cada compra realizada con la tarjeta; "
            "las tarjetas premium acumulan más puntos por sol gastado."
        )},
    },
    # ── Loans ─────────────────────────────────────────────────────────────────
    {
        "inputs": {"input": [{"role": "user", "content": "¿Qué tipos de préstamos ofrece el BCP?"}]},
        "expectations": {"expected_response": (
            "BCP ofrece préstamos personales, préstamos para libre disponibilidad, "
            "créditos hipotecarios, préstamos vehiculares y créditos de consumo."
        )},
    },
    {
        "inputs": {"input": [{"role": "user", "content": "¿Cuáles son los requisitos para solicitar un préstamo personal en el BCP?"}]},
        "expectations": {"expected_response": (
            "Se requiere ser cliente BCP, presentar DNI vigente, tener ingresos demostrables "
            "y cumplir con el perfil crediticio mínimo exigido por el banco."
        )},
    },
    {
        "inputs": {"input": [{"role": "user", "content": "¿Cuánto tiempo tarda el BCP en aprobar un préstamo?"}]},
        "expectations": {"expected_response": (
            "El tiempo de aprobación varía; los préstamos en línea para clientes BCP pueden "
            "aprobarse en minutos, mientras que los créditos hipotecarios pueden tomar varios días."
        )},
    },
    {
        "inputs": {"input": [{"role": "user", "content": "¿Puedo prepagar mi préstamo BCP sin penalidad?"}]},
        "expectations": {"expected_response": (
            "El BCP permite el prepago total o parcial de préstamos; las condiciones de "
            "penalidad dependen del tipo de crédito y del contrato suscrito."
        )},
    },
    {
        "inputs": {"input": [{"role": "user", "content": "¿Qué tasa de interés tiene el préstamo hipotecario del BCP?"}]},
        "expectations": {"expected_response": (
            "Las tasas hipotecarias del BCP son competitivas y dependen del monto, plazo "
            "y perfil del solicitante; se ofrecen en soles y dólares."
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
# --- Run evaluation ---
# mlflow.genai.to_predict_fn wraps the KA endpoint for use with mlflow.genai.evaluate
with mlflow.start_run(run_name="bcp_ka_evaluation"):
    results = mlflow.genai.evaluate(
        data=eval_data,
        predict_fn=mlflow.genai.to_predict_fn(f"endpoints:/{endpoint_name}"),
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
# --- Quality gate: RetrievalGroundedness pass rate must be > 85% ---
RETRIEVAL_GROUNDEDNESS_THRESHOLD = 0.85

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
        "The KA responses are not sufficiently grounded in the retrieved documents."
    )
