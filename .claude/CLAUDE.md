# Megacable Enterprise Solutions Chatbot — Context for Claude

## What This Project Is

A production-ready AI chatbot for **Megacable** that answers questions in Spanish about Megacable's 8 enterprise B2B solution categories. It runs on Databricks and combines:

- A **custom LangGraph RAG agent** running directly inside the Databricks App process (**Agents on Apps** — no separate model serving endpoint), backed by two **pgvector** tables on Lakebase:
  1. Scraped markdown from [mcmtechco.com/soluciones](https://www.mcmtechco.com/soluciones/) (8 solution pages) → `ai_vectorstore.megacable_solutions`
  2. An internal telecom support knowledge base translated to Spanish via `ai_translate()` → `ai_vectorstore.megacable_kb`
- A **React + Express** chat UI deployed as a Databricks App with **MEGA** branding
- **Lakebase Autoscaling (PostgreSQL 17)** for both chat history (`ai_chatbot` schema) and vector search (`ai_vectorstore` schema)
- **MLflow** for traces, human feedback, GenAI evaluation, and production monitoring

The chatbot covers these 8 solution areas: [Hiper] Conectividad, Colaboración | Symphony, Ciberseguridad, Nube | Hiperconvergencia, Megacable Data Center, Seguridad Física, Infraestructura como Servicio, Carriers.

**Architecture (Agents on Apps):**
```
Browser → Node.js Express (PORT, external)
              → /api/chat → AI SDK → API_PROXY=localhost:8080/invocations
                                         → Python FastAPI / uvicorn (port 8080, internal)
                                               → LangGraph RAG agent
                                                     → pgvector on Lakebase × 2 (cosine ANN)
                                                     → ChatDatabricks (GPT-5)
```

---

## Repository Structure

```
megacable/
├── agent_server/                             # Python agent server (Agents on Apps)
│   ├── __init__.py
│   ├── agent.py                              # @invoke/@stream handlers — imports from megacable_agent.core
│   └── start_server.py                       # AgentServer (FastAPI) entry point
├── megacable_agent/                          # Shared LangGraph agent logic
│   ├── __init__.py
│   └── core.py                               # build_graph() — used by agent_server AND evaluation notebooks
├── client/                                   # React 18 + Vite + Tailwind CSS frontend
├── server/                                   # Express 5 backend (streaming, auth, API routes)
├── packages/
│   ├── core/                                 # Domain types, schemas, errors, StreamCache
│   ├── auth/                                 # Databricks OAuth utilities
│   ├── db/                                   # Drizzle ORM + PostgreSQL (schema: ai_chatbot)
│   ├── ai-sdk-providers/                     # Databricks ResponsesAgent provider (Vercel AI SDK)
│   └── utils/                                # Shared utilities
├── knowledge_base_md/                        # English telecom support docs (178 .md files)
├── notebooks/
│   ├── data_processing/
│   │   ├── scraper_solutions.py              # Scrapes 8 Megacable solution pages → output_solutions/
│   │   └── translate_knowledge_base.py       # Batch-translates knowledge_base_md → knowledge_base_md_es/ using ai_translate()
│   ├── model/
│   │   ├── create_vs_indexes.py              # Active pipeline: embeds markdown → pgvector tables on Lakebase
│   │   ├── create_rag_agent.py               # Alternative (model-serving): logs/registers agent to UC
│   │   ├── rag_agent_model.py                # Alternative (model-serving): MLflow ResponsesAgent entry point
│   │   └── deploy_model.py                   # Alternative (model-serving): deploys serving endpoint
│   ├── evaluations/
│   │   └── model_evaluation.py               # MLflow GenAI eval — 10 questions, 4 scorers, ≥80% quality gate
│   ├── monitoring/
│   │   └── model_monitoring.py               # Registers continuous production monitors (100% sample rate)
│   └── setup/
│       └── lakebase_role_setup.py            # Grants app SP access to Lakebase schemas
├── scripts/
│   ├── __init__.py                           # Makes scripts/ a Python package (required for uv entry point)
│   ├── start_app.py                          # App entry point: starts uvicorn (port 8080) then npm start
│   ├── lakebase-role-setup.py                # CLI version of Lakebase role setup
│   ├── migrate.ts                            # DB migration runner
│   ├── get-pghost.sh                         # Get Lakebase endpoint hostname
│   └── quickstart.sh                         # Interactive local dev setup wizard
├── pyproject.toml                            # uv project — packages agent_server, megacable_agent, scripts
├── databricks.yml                            # Databricks Asset Bundle — all resources
├── app.yaml                                  # Databricks App runtime config (uv run start-app)
└── .github/workflows/deploy.yml             # CI/CD pipeline (5 jobs)
```

---

## Databricks Bundle Resources (`databricks.yml`)

| Resource | Type | Name (dev) |
|---|---|---|
| `megacable_rag_experiment` | MLflow Experiment | `/Users/<username>/megacable-rag-agent-dev-<username>` |
| `chatbot_lakebase` | Lakebase Autoscaling | `megacable-ka-db-dev-<username>` |
| `create_and_deploy_model` | Serverless Job | `create-and-deploy-model-dev-<username>` |
| `databricks_chatbot` | Databricks App | `megacable-solutions` |

**App resource bindings (all four must be present before starting the app):**

| Binding name | Type | Permission |
|---|---|---|
| `postgres` | Lakebase Autoscaling | `CAN_CONNECT_AND_CREATE` |
| `experiment` | MLflow Experiment | `CAN_EDIT` |

**Key variables:**

| Variable | Default | Notes |
|---|---|---|
| `uc_catalog` | `workshop_andrea` | UC catalog for all volume data |
| `uc_schema` | `megacable` | UC schema |
| `uc_volume` | `megacable-unstructured` | UC volume holding all data directories |
| `lakebase_database_id` | `db-qp0o-6pmctt6ixa` | Filled in after first deploy |
| `resource_name_suffix` | `dev-<username>` | Disambiguates resource names |

**Volume directories used:**

| Path | Contents |
|---|---|
| `/Volumes/workshop_andrea/megacable/megacable-unstructured/output_solutions/` | 8 scraped Megacable solution pages (markdown) |
| `/Volumes/workshop_andrea/megacable/megacable-unstructured/knowledge_base_md/` | Original English KB docs (uploaded from repo) |
| `/Volumes/workshop_andrea/megacable/megacable-unstructured/knowledge_base_md_es/` | Spanish-translated KB docs (output of translate job) |

---

## Job Pipeline (`create_and_deploy_model`)

Two tasks run **in parallel**, then the rest run **sequentially**:

```
scrape_solutions ────────────────────────┐
                                          ▼
translate_knowledge_base ──────────► create_vs_indexes ──► model_evaluation ──► model_monitoring
```

| Task | Notebook | What it does |
|---|---|---|
| `scrape_solutions` | `notebooks/data_processing/scraper_solutions.py` | Scrapes mcmtechco.com/soluciones (8 pages) → markdown in `output_solutions/` |
| `translate_knowledge_base` | `notebooks/data_processing/translate_knowledge_base.py` | Reads all `.md` from `knowledge_base_md/` via Spark binaryFile, calls `ai_translate()` in batch, writes to `knowledge_base_md_es/` |
| `create_vs_indexes` | `notebooks/model/create_vs_indexes.py` | Embeds markdown from UC Volume using `databricks-gte-large-en`, upserts into two pgvector tables on Lakebase (`ai_vectorstore` schema) |
| `model_evaluation` | `notebooks/evaluations/model_evaluation.py` | Imports `build_graph()` from `megacable_agent.core`, evaluates with 10 questions in Spanish, 4 scorers, quality gate ≥80% `RetrievalGroundedness` |
| `model_monitoring` | `notebooks/monitoring/model_monitoring.py` | Registers same 4 scorers as continuous monitors at 100% sample rate |

---

## CI/CD Pipeline (`.github/workflows/deploy.yml`)

```
build-app → deploy-bundle → scrape-and-deploy-model → setup-db-and-redeploy → start-app
```

| Job | Key steps |
|---|---|
| `build-app` | `npm ci` → lint (Biome) → build client → build server |
| `deploy-bundle` | Strip `valueFrom` refs from `app.yaml` (phase 1 deploy — no resources exist yet), validate, deploy |
| `scrape-and-deploy-model` | Extract UC vars → upload `knowledge_base_md/` → run full job pipeline (scrape → translate → pgvector ingest → evaluate → monitor) |
| `setup-db-and-redeploy` | Get Lakebase DB ID → get app SP → run role setup → inject `lakebase_database_id` into `databricks.yml` → redeploy |
| `start-app` | `databricks bundle run databricks_chatbot` |

**Required GitHub secrets:** `DATABRICKS_HOST`, `DATABRICKS_TOKEN`

---

## How to Deploy — Step by Step (for Claude)

Use profile `andreas_workspace` for this project unless the user specifies otherwise.

### Full fresh deployment

```bash
# 1. Deploy bundle (creates Lakebase project, MLflow experiment, app SP)
databricks bundle deploy --profile andreas_workspace

# 2. Get the Lakebase database ID and update databricks.yml
databricks postgres list-databases \
  "projects/megacable-ka-db-dev-<username>/branches/production" \
  --profile andreas_workspace --output json | jq -r '.[0].name'
# → update lakebase_database_id in databricks.yml, then redeploy:
databricks bundle deploy --profile andreas_workspace

# 3. Upload the local knowledge base to the UC volume
databricks fs cp -r ./knowledge_base_md/ \
  "dbfs:/Volumes/workshop_andrea/megacable/megacable-unstructured/knowledge_base_md/" \
  --profile andreas_workspace --overwrite

# 4. Run the full data pipeline job (scrape → translate → VS indexes → evaluate → monitor)
databricks bundle run create_and_deploy_model --profile andreas_workspace

# 5. Get the app service principal client ID
databricks apps get megacable-solutions --profile andreas_workspace --output json \
  | jq -r '.service_principal_client_id'

# 6. Run Lakebase role setup
python3 scripts/lakebase-role-setup.py \
  --project-id megacable-ka-db-dev-<username> \
  --sp-client-id <sp-client-id>

# 7. Start the app
databricks bundle run databricks_chatbot --profile andreas_workspace
```

### Redeployment after code changes

```bash
databricks bundle deploy --profile andreas_workspace
databricks bundle run databricks_chatbot --profile andreas_workspace
```

### Rerun the data pipeline only (new scrape / retranslate / re-index)

```bash
databricks bundle run create_and_deploy_model --profile andreas_workspace
```

### Validate bundle before deploying

```bash
databricks bundle validate --profile andreas_workspace
```

### Delete all resources (full teardown)

```bash
# 1. Destroy all bundle-managed resources (App, Lakebase project, Jobs, MLflow experiment)
databricks bundle destroy --profile andreas_workspace --auto-approve

# 2. Delete Vector Search indexes (best-effort — safe to ignore "not found")
databricks vector-search-indexes delete-index workshop_andrea.megacable.megacable_solutions_index --profile andreas_workspace
databricks vector-search-indexes delete-index workshop_andrea.megacable.megacable_kb_index --profile andreas_workspace

# 3. Delete the Vector Search endpoint
databricks vector-search-endpoints delete-endpoint megacable-vs-workshop_andrea --profile andreas_workspace
```

---

## Database Connection

The app connects to Lakebase via the **`postgres` resource binding** declared in `databricks.yml` — Databricks injects `LAKEBASE_ENDPOINT` automatically (mapped via `app.yaml` `valueFrom: postgres`). No manual credential management needed.

The app reads `POSTGRES_URL` first (set by the platform), falling back to individual `PG*` env vars for local dev.

**Schema:** `ai_chatbot` (hardcoded in `packages/db/src/schema.ts`)
**Tables:** `User`, `Chat`, `Message`, `Vote`

### Local development DB connection

```bash
# Set in .env:
PGHOST=<lakebase-host>
PGUSER=<your-databricks-username>
PGDATABASE=databricks_postgres
PGPORT=5432
PGSSLMODE=require
DATABRICKS_CONFIG_PROFILE=andreas_workspace
```

### Schema changes

```bash
# 1. Edit packages/db/src/schema.ts
# 2. Generate migration
npm run db:generate
# 3. Apply migration
npm run db:migrate
# 4. Commit both schema.ts and the new migration file
```

**Never use `npm run db:push` in production** — it bypasses migration history and can drop data.

---

## Development Commands

```bash
npm run dev              # Frontend :3000 + Backend :3001 (concurrent)
npm run build            # Full build: DB migrate → client → server
npm run build:client     # Client only
npm run build:server     # Server only
npm run lint             # Biome lint + format (auto-fix)
npm test                 # Playwright E2E tests
npm run db:migrate       # Apply pending migrations
npm run db:studio        # Drizzle Studio (visual DB browser)
```

---

## Key Code Paths

| What | Where |
|---|---|
| Express entry point | `server/src/index.ts` |
| Chat streaming route | `server/src/routes/chat.ts` |
| Auth middleware | `server/src/middleware/auth.ts` |
| DB schema | `packages/db/src/schema.ts` |
| DB queries | `packages/db/src/queries.ts` |
| DB connection | `packages/db/src/connection.ts` — reads `POSTGRES_URL` first, then `PG*` vars |
| RAG agent AI provider | `packages/ai-sdk-providers/` |
| **Shared agent logic** | `megacable_agent/core.py` — `build_graph()` used by app AND notebooks |
| **Agent @invoke/@stream** | `agent_server/agent.py` — wires `build_graph()` to MLflow handlers |
| **Agent FastAPI server** | `agent_server/start_server.py` — `AgentServer("ResponsesAgent")` on port 8080 |
| **App entry point** | `scripts/start_app.py` — starts uvicorn (bg) then `npm run start` |
| pgvector ingestion | `notebooks/model/create_vs_indexes.py` |
| Model evaluation (offline) | `notebooks/evaluations/model_evaluation.py` |
| React root | `client/src/App.tsx` |
| Chat UI | `client/src/components/chat.tsx` |
| Message rendering + citations | `client/src/components/message.tsx` |

---

## Code Style

- **Formatter/Linter:** Biome (NOT ESLint/Prettier) — run `npm run lint`
- **TypeScript:** Strict mode, ES2022 target
- **Imports:** Use workspace aliases — `@chat-template/core`, `@chat-template/db`, `@chat-template/auth`
- **Indentation:** 2 spaces, LF line endings, single quotes, always semicolons

---

## Notebooks — Key Patterns

### Adding a new knowledge source (new pgvector table)

To add a new data source to the RAG agent:
1. Add a new scraper/translation notebook that writes markdown to a new UC Volume directory
2. Add a new table + ingestion loop to `notebooks/model/create_vs_indexes.py`
3. In `megacable_agent/core.py` (`build_graph()`), add a new `_search(table, query)` call and `@tool`-decorated retriever
4. Add the new table name as a parameter to `build_graph()` and wire it through `agent_server/agent.py`
5. Re-run the job and redeploy the app

### Shared agent code (`megacable_agent/core.py`)

`build_graph(pg_conn_fn, table_solutions, table_kb, embedding_endpoint, llm_endpoint, system_prompt)` is the single source of truth for the LangGraph agent.

- **In Databricks Apps** (`agent_server/agent.py`): `_pg_conn_fn()` calls `WorkspaceClient().postgres.generate_database_credential(endpoint=...)` on every retrieval to get a fresh Lakebase OAuth token. The project ID is derived from `LAKEBASE_ENDPOINT` hostname or `LAKEBASE_PROJECT_ID` env var.
- **In notebooks** (`model_evaluation.py`): pass a `pg_conn_fn` closure that calls `w.postgres.generate_database_credential()` with the `lakebase_project_id` widget value. Add repo root to `sys.path` first so the package is importable.

### Lakebase auth for pgvector (Databricks Apps)

Lakebase uses Databricks OAuth tokens as the PostgreSQL password. Since tokens expire (~1hr), `_pg_conn_fn()` in `agent_server/agent.py` generates a fresh credential on **every retrieval call**. The `WorkspaceClient()` is cached; `generate_database_credential` is called each time:

```python
cred = _sdk_client.postgres.generate_database_credential(endpoint=_lakebase_endpoint_name)
return f"postgresql://{client_id}:{cred.token}@{pg_host}:5432/databricks_postgres?sslmode=require"
```

The Lakebase endpoint name is: `projects/{project_id}/branches/production/endpoints/primary`
where `project_id` = first component of `LAKEBASE_ENDPOINT` hostname (or `LAKEBASE_PROJECT_ID` env var).

### Changing the scraper target

Edit `notebooks/data_processing/scraper_solutions.py`:
- Update the `SOLUTIONS` list (name, slug, url)
- Output always goes to `output_solutions/` — the pgvector ingestion notebook reads from there

### RETRIEVER span format — critical for RetrievalGroundedness

`mlflow.genai.evaluate` scorer `RetrievalGroundedness` requires RETRIEVER spans whose **output is `List[mlflow.entities.Document]`**, not plain strings. Always return `MlflowDocument` objects from functions decorated with `@mlflow.trace(span_type=SpanType.RETRIEVER)`:

```python
from mlflow.entities import Document as MlflowDocument, SpanType

@mlflow.trace(span_type=SpanType.RETRIEVER)
def my_retriever(query: str) -> list[MlflowDocument]:
    lc_docs = store.similarity_search(query, k=5)
    return [MlflowDocument(id=str(i), page_content=doc.page_content, metadata=doc.metadata)
            for i, doc in enumerate(lc_docs)]
```

The `@tool` wrapper calls this function and converts the result to a string for the LLM — that is correct. The RETRIEVER span itself must expose `List[MlflowDocument]`.

### Evaluation approach — use shared `build_graph()` (not pyfunc)

`mlflow.pyfunc.load_model().predict()` creates its own internal trace context that isolates RETRIEVER spans from `mlflow.genai.evaluate`'s trace — causing 0% `RetrievalGroundedness`. The evaluation notebook calls `build_graph()` from `megacable_agent.core` directly. Add the repo root to `sys.path` first:

```python
import sys
ctx = dbutils.notebook.entry_point.getDbutils().notebook().getContext()
repo_root = "/Workspace" + "/".join(ctx.notebookPath().get().split("/")[:-3])
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from megacable_agent.core import build_graph
graph = build_graph(pg_conn_fn=pg_conn_fn)  # pg_conn_fn calls generate_database_credential
```

### Translation notebook performance note

`translate_knowledge_base.py` uses Spark's `binaryFile` reader to load all markdown files into a DataFrame, then applies `ai_translate()` across all rows in **one distributed Spark job** before collecting. Do NOT rewrite it to loop file-by-file — that's ~100× slower due to per-call Spark overhead.

---

## MLflow Evaluation & Monitoring

**Scorers (used in both eval and monitoring):**

| Scorer | Threshold |
|---|---|
| `RetrievalGroundedness` | Quality gate ≥ 80% (blocks `model_monitoring` if failed) |
| `response_en_espanol` (Guidelines) | Responses fully in Spanish |
| `Safety` | No harmful content |
| `RelevanceToQuery` | Answers are on-topic |

**Evaluation approach:** `build_graph()` from `megacable_agent.core` is called directly in the notebook so RETRIEVER spans land in the `mlflow.genai.evaluate` trace context. `predict_fn(input)` wraps `graph.invoke()` and is passed directly to `mlflow.genai.evaluate`.

**Evaluation dataset:** 10 questions covering all 8 Megacable solution categories (defined in `model_evaluation.py`).
**Monitoring:** 100% sample rate on every production trace, results visible in MLflow Experiment UI → Monitoring tab.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Bundle deploy fails — `lakebase_database_id` empty path | Get DB ID: `databricks postgres list-databases "projects/megacable-ka-db-dev-<user>/branches/production" --output json \| jq -r '.[0].name'`, update `databricks.yml` |
| App fails to connect to DB | Re-run `lakebase-role-setup.py` with the app's current SP client ID |
| `permission denied for table` after recreating app | App got a new SP — re-run role setup with the new SP ID |
| Bundle deploy fails with "app already exists" | `databricks bundle deployment bind databricks_chatbot megacable-solutions --profile andreas_workspace --auto-approve` |
| Translation job slow | Ensure it uses Spark binaryFile + batch `ai_translate()`. Do NOT use per-file `spark.sql()` loops |
| `valueFrom` resolution error on first deploy | Expected — initial deploy strips all `valueFrom` refs. Run the full pipeline then redeploy with resources |
| `RetrievalGroundedness` 0% in evaluation | RETRIEVER span output must be `List[mlflow.entities.Document]`, not strings. Call `build_graph()` directly — do not use `mlflow.pyfunc.load_model()` |
| pgvector tables empty / retrieval returns nothing | Run the `create_vs_indexes` job task — it populates `ai_vectorstore.megacable_solutions` and `ai_vectorstore.megacable_kb` |
| `psycopg.errors.UndefinedTable: relation "ai_vectorstore.megacable_solutions" does not exist` | pgvector ingestion notebook has not run yet, or ran against a different project ID |
| `permission denied for schema ai_vectorstore` | Re-run `lakebase-role-setup.py` — it now grants permissions on `ai_vectorstore` schema in addition to `ai_chatbot` |
| `generate_database_credential` fails in app | Endpoint name wrong — check `LAKEBASE_PROJECT_ID` env var or verify that the hostname prefix matches the project ID |
| Agent server not starting (ECONNREFUSED 8080) | Check that `scripts/__init__.py` exists — without it `uv run start-app` can't import `scripts.start_app` |
| `PERMISSION_DENIED` on MLflow experiment at startup | Experiment resource binding needs `CAN_EDIT` (not `CAN_READ`) — update in `databricks.yml` |
| pip install exits with code 2 — psycopg conflict | `psycopg[binary]>=3.0` requires Python ≥3.8; ensure the cluster runtime matches |
