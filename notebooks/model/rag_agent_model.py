"""
Megacable RAG Agent — MLflow ResponsesAgent (models-from-code entry point).

MLflow loads this file at inference time. Configuration is injected via
model_config passed to log_model and read here via ModelConfig.
Task type is automatically set to agent/v1/responses by MLflow.
"""
from typing import Generator

import mlflow
from databricks_langchain import ChatDatabricks, DatabricksVectorSearch
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from mlflow.entities import Document as MlflowDocument
from mlflow.entities import SpanType
from mlflow.models import ModelConfig, set_model
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
    output_to_responses_items_stream,
    to_chat_completions_input,
)

# Development defaults — overridden by model_config at log/serve time
config = ModelConfig(
    development_config={
        "index_solutions": "workshop_andrea.megacable.megacable_solutions_index",
        "index_kb": "workshop_andrea.megacable.megacable_kb_index",
        "llm_endpoint": "databricks-gpt-5-1",
        "system_prompt": (
            "Eres un asistente experto en las soluciones empresariales de Megacable. "
            "Responde siempre en español. Usa las herramientas de búsqueda para encontrar "
            "información relevante antes de responder. Menciona sub-productos y beneficios "
            "cuando el usuario pregunte por una solución específica. "
            "No llames la misma herramienta dos veces en el mismo turno."
        ),
    }
)

INDEX_SOLUTIONS = config.get("index_solutions")
INDEX_KB        = config.get("index_kb")
LLM_ENDPOINT    = config.get("llm_endpoint")
SYSTEM_PROMPT   = config.get("system_prompt")

_solutions_store = DatabricksVectorSearch(index_name=INDEX_SOLUTIONS)
_kb_store        = DatabricksVectorSearch(index_name=INDEX_KB)


@mlflow.trace(span_type=SpanType.RETRIEVER)
def megacable_solutions_retriever(query: str) -> list[MlflowDocument]:
    lc_docs = _solutions_store.similarity_search(query, k=5)
    return [
        MlflowDocument(id=str(i), page_content=doc.page_content, metadata=doc.metadata)
        for i, doc in enumerate(lc_docs)
    ]


@mlflow.trace(span_type=SpanType.RETRIEVER)
def megacable_kb_retriever(query: str) -> list[MlflowDocument]:
    lc_docs = _kb_store.similarity_search(query, k=5)
    return [
        MlflowDocument(id=str(i), page_content=doc.page_content, metadata=doc.metadata)
        for i, doc in enumerate(lc_docs)
    ]


@tool(
    "megacable_solutions_retriever",
    description=(
        "Busca en las 8 categorías de soluciones empresariales de Megacable: "
        "conectividad, ciberseguridad, colaboración (Symphony), nube, data center, "
        "seguridad física, infraestructura como servicio y carriers."
    ),
)
def solutions_tool(query: str) -> str:
    docs = megacable_solutions_retriever(query)
    return "\n\n".join(doc.page_content for doc in docs)


@tool(
    "megacable_kb_retriever",
    description=(
        "Busca en la base de conocimiento técnico de soporte: guías de gestión de "
        "cuentas, resolución de incidentes, políticas de conectividad y atención al cliente."
    ),
)
def kb_tool(query: str) -> str:
    docs = megacable_kb_retriever(query)
    return "\n\n".join(doc.page_content for doc in docs)


llm   = ChatDatabricks(endpoint=LLM_ENDPOINT, temperature=0.1)
graph = create_react_agent(llm, tools=[solutions_tool, kb_tool], prompt=SYSTEM_PROMPT)


class MegacableRAGAgent(ResponsesAgent):
    @mlflow.trace(span_type=SpanType.AGENT)
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        outputs = [
            event.item
            for event in self.predict_stream(request)
            if event.type == "response.output_item.done"
        ]
        return ResponsesAgentResponse(output=outputs, custom_outputs=request.custom_inputs)

    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        cc_msgs = to_chat_completions_input([i.model_dump() for i in request.input])
        for _, events in graph.stream({"messages": cc_msgs}, stream_mode=["updates"]):
            for node_data in events.values():
                yield from output_to_responses_items_stream(node_data["messages"])


mlflow.langchain.autolog()
agent = MegacableRAGAgent()
set_model(agent)
