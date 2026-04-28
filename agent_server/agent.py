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
        "index_solutions": "workshop_andrea.megacable.megacable_solutions_index",
        "index_kb": "workshop_andrea.megacable.megacable_kb_index",
        "llm_endpoint": "databricks-gpt-5-1",
    }
)

INDEX_SOLUTIONS = config.get("index_solutions")
INDEX_KB        = config.get("index_kb")
LLM_ENDPOINT    = config.get("llm_endpoint")

# Graph is lazy-initialized on first request so DatabricksVectorSearch is not
# instantiated at import time (credentials aren't available yet at module load).
_graph = None


def _vs_client_args() -> dict:
    host = os.environ["DATABRICKS_HOST"]
    if not host.startswith("https://"):
        host = f"https://{host}"
    return {
        "workspace_url": host,
        "service_principal_client_id": os.environ["DATABRICKS_CLIENT_ID"],
        "service_principal_client_secret": os.environ["DATABRICKS_CLIENT_SECRET"],
        "disable_notice": True,
    }


def _get_graph():
    global _graph
    if _graph is None:
        from megacable_agent.core import build_graph
        _graph = build_graph(
            index_solutions=INDEX_SOLUTIONS,
            index_kb=INDEX_KB,
            llm_endpoint=LLM_ENDPOINT,
            vs_client_args=_vs_client_args(),
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
