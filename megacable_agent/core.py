"""
Shared LangGraph RAG agent for Megacable.

Used by both:
  - agent_server/agent.py   (Databricks Apps — pass vs_client_args for SP auth)
  - notebooks/evaluations/  (Databricks notebooks — omit vs_client_args for auto-auth)
"""
from typing import Optional

import mlflow
from databricks_langchain import ChatDatabricks, DatabricksVectorSearch
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from mlflow.entities import Document as MlflowDocument
from mlflow.entities import SpanType

LLM_ENDPOINT = "databricks-gpt-5-1"
SYSTEM_PROMPT = (
    "Eres un asistente experto en las soluciones empresariales de Megacable. "
    "Responde siempre en español. Usa las herramientas de búsqueda para encontrar "
    "información relevante antes de responder. Menciona sub-productos y beneficios "
    "cuando el usuario pregunte por una solución específica. "
    "No llames la misma herramienta dos veces en el mismo turno."
)


def build_graph(
    index_solutions: str,
    index_kb: str,
    llm_endpoint: str = LLM_ENDPOINT,
    system_prompt: str = SYSTEM_PROMPT,
    vs_client_args: Optional[dict] = None,
):
    """
    Build the Megacable LangGraph ReAct agent.

    Args:
        index_solutions: Full UC path of the solutions Vector Search index.
        index_kb:        Full UC path of the knowledge base Vector Search index.
        llm_endpoint:    Databricks model serving endpoint for the LLM.
        system_prompt:   System prompt for the agent.
        vs_client_args:  kwargs forwarded to VectorSearchClient (workspace_url,
                         service_principal_client_id, service_principal_client_secret).
                         Pass None when running in a Databricks notebook — auth is
                         auto-detected from the notebook context.
    Returns:
        A compiled LangGraph graph ready to call .invoke() or .stream() on.
    """
    client_args = vs_client_args or {}

    solutions_store = DatabricksVectorSearch(
        index_name=index_solutions, **({"client_args": client_args} if client_args else {})
    )
    kb_store = DatabricksVectorSearch(
        index_name=index_kb, **({"client_args": client_args} if client_args else {})
    )

    @mlflow.trace(span_type=SpanType.RETRIEVER)
    def megacable_solutions_retriever(query: str) -> list[MlflowDocument]:
        lc_docs = solutions_store.similarity_search(query, k=5)
        return [
            MlflowDocument(id=str(i), page_content=doc.page_content, metadata=doc.metadata)
            for i, doc in enumerate(lc_docs)
        ]

    @mlflow.trace(span_type=SpanType.RETRIEVER)
    def megacable_kb_retriever(query: str) -> list[MlflowDocument]:
        lc_docs = kb_store.similarity_search(query, k=5)
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

    mlflow.langchain.autolog()
    llm = ChatDatabricks(endpoint=llm_endpoint, temperature=0.1)
    return create_react_agent(llm, tools=[solutions_tool, kb_tool], prompt=system_prompt)
