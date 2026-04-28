"""
Shared LangGraph RAG agent for Megacable.

Used by both:
  - agent_server/agent.py   (Databricks Apps — pass pg_conn_fn with SP OAuth auth)
  - notebooks/evaluations/  (Databricks notebooks — pass pg_conn_fn with notebook auth)
"""
from typing import Callable

import mlflow
from databricks_langchain import ChatDatabricks, DatabricksEmbeddings
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from mlflow.entities import Document as MlflowDocument
from mlflow.entities import SpanType

LLM_ENDPOINT = "databricks-gpt-5-1"
EMBEDDING_ENDPOINT = "databricks-gte-large-en"
SYSTEM_PROMPT = (
    "Eres un asistente experto en las soluciones empresariales de Megacable. "
    "Responde siempre en español. Usa las herramientas de búsqueda para encontrar "
    "información relevante antes de responder. Menciona sub-productos y beneficios "
    "cuando el usuario pregunte por una solución específica. "
    "No llames la misma herramienta dos veces en el mismo turno."
)


def build_graph(
    pg_conn_fn: Callable[[], dict],
    table_solutions: str = "megacable_solutions",
    table_kb: str = "megacable_kb",
    embedding_endpoint: str = EMBEDDING_ENDPOINT,
    llm_endpoint: str = LLM_ENDPOINT,
    system_prompt: str = SYSTEM_PROMPT,
):
    """
    Build the Megacable LangGraph ReAct agent backed by pgvector on Lakebase.

    Args:
        pg_conn_fn:         Callable returning a dict of psycopg keyword args (host, user,
                            password, dbname, sslmode). Called on every retrieval so the
                            OAuth token stays current. Using a dict avoids URL-encoding
                            issues with special characters in usernames/tokens.
        table_solutions:    Table name in schema ai_vectorstore for solutions docs.
        table_kb:           Table name in schema ai_vectorstore for KB docs.
        embedding_endpoint: Databricks embedding model endpoint name.
        llm_endpoint:       Databricks LLM model serving endpoint name.
        system_prompt:      System prompt injected into the agent.
    Returns:
        A compiled LangGraph graph.
    """
    import numpy as np
    import psycopg
    from pgvector.psycopg import register_vector

    embeddings = DatabricksEmbeddings(endpoint=embedding_endpoint)

    def _search(table: str, query: str, k: int = 5) -> list[MlflowDocument]:
        # np.array required — register_vector maps ndarray → vector type;
        # a plain Python list is sent as double precision[] and the <=> operator fails.
        query_vec = np.array(embeddings.embed_query(query))
        # Use explicit try/finally — psycopg's __exit__ can raise during rollback
        # on a broken connection, causing "generator didn't stop after throw()"
        # when nested inside an @mlflow.trace-decorated function.
        conn = psycopg.connect(**pg_conn_fn())
        try:
            register_vector(conn)
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id, content, filename"
                    f" FROM ai_vectorstore.{table}"
                    f" ORDER BY embedding <=> %s LIMIT %s",
                    (query_vec, k),
                )
                rows = cur.fetchall()
            conn.commit()
        finally:
            conn.close()
        return [
            MlflowDocument(
                id=row[0],
                page_content=row[1],
                metadata={"filename": row[2]},
            )
            for row in rows
        ]

    @mlflow.trace(span_type=SpanType.RETRIEVER)
    def megacable_solutions_retriever(query: str) -> list[MlflowDocument]:
        return _search(table_solutions, query)

    @mlflow.trace(span_type=SpanType.RETRIEVER)
    def megacable_kb_retriever(query: str) -> list[MlflowDocument]:
        return _search(table_kb, query)

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
