"""
Megacable RAG Agent — runs directly in Databricks Apps via @invoke/@stream.

MLflow loads @invoke and @stream handlers at startup via AgentServer.
Agent logic lives in megacable_agent/core.py (shared with evaluation notebooks).
"""
import os
from typing import Generator

import mlflow
from mlflow.entities import SpanType
from mlflow.genai.agent_server import invoke, stream
from mlflow.models import ModelConfig
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
    output_to_responses_items_stream,
    to_chat_completions_input,
)

config = ModelConfig(
    development_config={
        "table_solutions": "megacable_solutions",
        "table_kb":        "megacable_kb",
        "llm_endpoint":    "databricks-gpt-5-1",
    }
)

TABLE_SOLUTIONS = config.get("table_solutions")
TABLE_KB        = config.get("table_kb")
LLM_ENDPOINT    = config.get("llm_endpoint")

# Graph is lazy-initialized on first request so psycopg/pgvector are not
# imported at module load time (credentials aren't available yet).
_graph = None
_sdk_client = None
_pg_host = None
_lakebase_endpoint_name = None


def _init_pg_config():
    """Initialize Lakebase connection config once (idempotent)."""
    global _sdk_client, _pg_host, _lakebase_endpoint_name
    if _pg_host is not None:
        return
    from databricks.sdk import WorkspaceClient
    _sdk_client = WorkspaceClient()
    _pg_host = os.environ["LAKEBASE_ENDPOINT"]
    # Derive project ID from env var or from hostname first component
    # (Lakebase hostnames follow: <project_id>.postgres.<region>.databricks.com)
    project_id = os.environ.get("LAKEBASE_PROJECT_ID") or _pg_host.split(".")[0]
    _lakebase_endpoint_name = (
        f"projects/{project_id}/branches/production/endpoints/primary"
    )


def _pg_conn_fn() -> str:
    """Return a fresh PostgreSQL connection string with a current OAuth token."""
    _init_pg_config()
    cred = _sdk_client.postgres.generate_database_credential(
        endpoint=_lakebase_endpoint_name
    )
    client_id = os.environ["DATABRICKS_CLIENT_ID"]
    return (
        f"postgresql://{client_id}:{cred.token}"
        f"@{_pg_host}:5432/databricks_postgres?sslmode=require"
    )


def _get_graph():
    global _graph
    if _graph is None:
        from megacable_agent.core import build_graph
        _graph = build_graph(
            pg_conn_fn=_pg_conn_fn,
            table_solutions=TABLE_SOLUTIONS,
            table_kb=TABLE_KB,
            llm_endpoint=LLM_ENDPOINT,
        )
    return _graph


@invoke()
@mlflow.trace(span_type=SpanType.AGENT)
def invoke_handler(request: ResponsesAgentRequest) -> ResponsesAgentResponse:
    outputs = [
        event.item
        for event in stream_handler(request)
        if event.type == "response.output_item.done"
    ]
    return ResponsesAgentResponse(output=outputs, custom_outputs=request.custom_inputs)


@stream()
def stream_handler(
    request: ResponsesAgentRequest,
) -> Generator[ResponsesAgentStreamEvent, None, None]:
    cc_msgs = to_chat_completions_input([i.model_dump() for i in request.input])
    for _, events in _get_graph().stream({"messages": cc_msgs}, stream_mode=["updates"]):
        for node_data in events.values():
            yield from output_to_responses_items_stream(node_data["messages"])
