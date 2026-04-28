# Megacable Enterprise Solutions Chat Bot

A production-ready AI chatbot that answers questions about Megacable's 8 enterprise solution categories in Spanish. Built on Databricks with a custom **LangGraph RAG agent** (MLflow `ResponsesAgent`) backed by **pgvector on Lakebase**, a React + Express frontend, Lakebase Autoscaling for persistent chat history and vector search, and MLflow for traces, evaluations, and human feedback.

## Setup on Windows

### Install the Databricks CLI

```powershell
# Option 1 — winget (recommended, no extra tools needed)
winget install Databricks.DatabricksCLI

# Option 2 — Chocolatey
choco install databricks-cli

# Option 3 — Manual
# Download databricks_windows_amd64.zip from https://github.com/databricks/cli/releases/latest
# Extract databricks.exe and add its folder to your PATH
```

Verify the install and authenticate:

```powershell
databricks --version
databricks auth login --host https://<your-workspace>.cloud.databricks.com --profile <your-profile>
```

### Install Claude Code on Windows

Claude Code is a Node.js CLI — no Anthropic subscription is required when you route it through the Databricks AI Gateway (see the next section).

```powershell
npm install -g @anthropic-ai/claude-code
```

Start it from the project directory:

```powershell
cd megacable
claude
```

---

## Using Claude Code with This Project

This project ships a `CLAUDE.md` that gives Claude Code full context about the architecture, deployment steps, and key file paths — so you can use Claude to deploy and develop the app without having to explain the project from scratch each session.

### Connect Claude Code to Databricks (no Anthropic license required)

Instead of paying for an Anthropic Claude Code subscription, you can route all Claude Code API calls through your **Databricks workspace AI Gateway**. Claude Code bills against your Databricks workspace spend — no separate Anthropic account or license is needed.

Create `.claude/settings.json` at the project root:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://<workspace-id>.ai-gateway.cloud.databricks.com/anthropic",
    "ANTHROPIC_MODEL": "databricks-claude-opus-4-6",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "databricks-claude-opus-4-6",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "databricks-claude-sonnet-4-6",
    "CLAUDE_CODE_SUBAGENT_MODEL": "databricks-claude-sonnet-4-6",
    "ANTHROPIC_CUSTOM_HEADERS": "x-databricks-use-coding-agent-mode: true",
    "ANTHROPIC_AUTH_TOKEN": "<your-databricks-pat>",
    "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1"
  }
}
```

| Variable | Description |
|---|---|
| `ANTHROPIC_BASE_URL` | Your workspace AI Gateway URL. In the Databricks UI go to **AI Gateway → Gateway Routes** and copy the route URL. Format: `https://<workspace-id>.ai-gateway.cloud.databricks.com/anthropic` |
| `ANTHROPIC_MODEL` | Primary model. Use a Databricks-hosted Claude model (e.g. `databricks-claude-opus-4-6`) |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | Model resolved when code requests the Opus family |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | Model resolved when code requests the Sonnet family |
| `CLAUDE_CODE_SUBAGENT_MODEL` | Model for Claude Code subagents (parallel/background tasks). Sonnet is recommended for cost |
| `ANTHROPIC_CUSTOM_HEADERS` | `x-databricks-use-coding-agent-mode: true` enables extended tool-use limits on the AI Gateway |
| `ANTHROPIC_AUTH_TOKEN` | A Databricks PAT — **Settings → Developer → Access tokens**. **Do not commit this file** — add `.claude/settings.json` to `.gitignore` |
| `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` | Set to `"1"` to disable Claude beta features not supported by the Databricks AI Gateway |

> **Note:** `.claude/settings.json` is gitignored because it contains your PAT. Each developer creates their own copy locally.

**How to get your AI Gateway URL:**
1. Open your Databricks workspace
2. Go to **Compute → AI Gateway** (left sidebar)
3. Find or create a **Gateway Route** for Claude models
4. Copy the **Route URL** — it looks like `https://<workspace-id>.ai-gateway.cloud.databricks.com/anthropic`

### What Claude knows about this project

Once configured, Claude reads `CLAUDE.md` automatically and knows:
- The full deployment sequence (deploy → get DB ID → upload KB → run job → role setup → redeploy → start app)
- Which Databricks CLI profile to use (`andreas_workspace`)
- All bundle resource names, UC paths, and variable values
- Key code paths, notebook patterns, and database conventions

You can ask Claude things like:
- *"Deploy the app end to end"*
- *"Run the data pipeline job and wait for it to finish"*
- *"Add a new knowledge source for Megacable's partner program"*
- *"The evaluation quality gate failed — what should I check?"*

---

## Architecture

The agent runs **inside the Databricks App process** (Agents on Apps) — no separate model serving endpoint is required.

```
Web Scraper (Notebooks)                   Knowledge Base (local → volume)
  └─► output_solutions/ (UC Volume)         └─► knowledge_base_md_es/ (translated)
        └──────────── pgvector ingest notebook (databricks-gte-large-en) ──────────┐
                                                                                    │
Browser → Node.js Express (PORT, external)                                          │
              → /api/chat → AI SDK → API_PROXY=localhost:8080/invocations           │
                                         → Python FastAPI / uvicorn (port 8080)     │
                                               → LangGraph RAG agent               │
                                                     → pgvector on Lakebase ───────┘
                                                         (ai_vectorstore schema)
                                                     → ChatDatabricks (GPT-5)
              → Lakebase Autoscaling (PostgreSQL) — chat history (ai_chatbot schema)
              → MLflow Experiment — traces + human feedback
```

| Component | Technology |
|-----------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | Express 5 + Vercel AI SDK (streaming) |
| AI Agent | Custom LangGraph ReAct agent (MLflow `ResponsesAgent`) |
| Vector Search | pgvector on Lakebase — two tables in `ai_vectorstore` schema (HNSW cosine index) |
| Database | Lakebase Autoscaling (managed PostgreSQL 17) — chat history + vector search |
| Observability | MLflow traces + GenAI evaluation + production monitoring |
| Deployment | Databricks Asset Bundle (DAB) + Databricks Apps |

## The 8 Megacable Enterprise Solutions

| Solution | Description |
|----------|-------------|
| [Hiper] Conectividad | Internet Dedicado, Cloud Connect, Mega Móvil, GPON, Líneas Privadas Ethernet |
| Colaboración \| Symphony | UCaaS y CCaaS — comunicaciones unificadas y contact center |
| Ciberseguridad | SASE, Firewall as a Service, SOC as a Service, XDR, ZTNA, Ethical Hacking |
| Nube \| Hiperconvergencia | Nube Pública, Nube Local, Backup as a Service, DRP, Máquinas Virtuales |
| Megacable Data Center | Colocation, Edge Data Center, Conectividad, Manos y Ojos Remotos |
| Seguridad Física | Videovigilancia, Análisis de Video, Control de Accesos, Detectores de Incendio |
| Infraestructura como Servicio | Infraestructura administrada escalable |
| Carriers | Wavelength, Frecuencias 23 GHz |

## Project Structure

```
megacable/
├── agent_server/                             # Python agent server (Agents on Apps)
│   ├── agent.py                              # @invoke/@stream handlers
│   └── start_server.py                       # FastAPI / uvicorn entry point (port 8080)
├── megacable_agent/                          # Shared LangGraph agent logic
│   └── core.py                               # build_graph() — used by agent_server AND evaluation notebooks
├── client/                                   # React frontend
├── server/                                   # Express backend
├── packages/
│   ├── core/                                 # Domain types and errors
│   ├── auth/                                 # Databricks authentication
│   ├── db/                                   # Drizzle ORM + PostgreSQL
│   └── utils/                                # Shared utilities
├── knowledge_base_md/                        # English telecom support docs (local)
├── notebooks/
│   ├── data_processing/
│   │   ├── scraper_solutions.py              # Scrapes 8 Megacable solution pages
│   │   └── translate_knowledge_base.py       # Translates knowledge_base_md to Spanish via ai_translate()
│   ├── model/
│   │   ├── create_vs_indexes.py              # Active pipeline: embeds markdown → pgvector tables on Lakebase
│   │   ├── create_rag_agent.py               # Alternative (model-serving): logs/registers agent to UC
│   │   ├── rag_agent_model.py                # Alternative (model-serving): MLflow ResponsesAgent entry point
│   │   └── deploy_model.py                   # Alternative (model-serving): deploys serving endpoint
│   ├── evaluations/
│   │   └── model_evaluation.py               # MLflow GenAI evaluation (4 scorers, 10 questions)
│   ├── monitoring/
│   │   └── model_monitoring.py               # MLflow GenAI production monitoring
│   └── setup/
│       └── lakebase_role_setup.py            # Lakebase role + permissions setup
├── scripts/
│   ├── start_app.py                          # App entry point: starts uvicorn (port 8080) then npm start
│   ├── lakebase-role-setup.py                # Grants app SP database permissions
│   ├── quickstart.sh                         # Interactive setup wizard
│   └── get-pghost.sh                         # Retrieve Lakebase endpoint hostname
├── .github/workflows/deploy.yml              # CI/CD pipeline
├── databricks.yml                            # Databricks Asset Bundle config
├── app.yaml                                  # App runtime config (uv run start-app)
├── pyproject.toml                            # uv project — agent_server, megacable_agent, scripts packages
└── requirements.txt                          # Python deps for notebooks
```

## Requirements

### Databricks Workspace

| Requirement | Details |
|-------------|---------|
| **Databricks Apps** | Must be enabled in the workspace |
| **Serverless Compute** | Required for notebook jobs |
| **Unity Catalog** | Catalog + schema + volume for scraped data and translated knowledge base |
| **Lakebase Autoscaling** | PostgreSQL 17 — chat history (`ai_chatbot`) + vector search (`ai_vectorstore`) |
| **MLflow** | Traces, GenAI evaluation, production monitoring (built in to Databricks) |
| **AI Functions** | `ai_translate()` used by the translation notebook — requires SQL warehouse access |
| **LLM endpoint** | `databricks-gpt-5-1` — must be available in the workspace (Foundation Model APIs) |
| **Embedding endpoint** | `databricks-gte-large-en` — used to embed documents into pgvector tables (1024 dims) |

### Local Machine

| Tool | Version | Install |
|------|---------|---------|
| **Databricks CLI** | v0.240+ | `brew install databricks` |
| **Node.js** | ≥18.0.0 (20.x recommended) | `nvm install 20` |
| **npm** | ≥8.0.0 | bundled with Node.js |
| **Python** | 3.11+ | System or `pyenv` |
| **uv** | any | `pip install uv` or `brew install uv` |
| **jq** | any | `brew install jq` |

### Python Dependencies — App (`pyproject.toml`)

These are installed automatically by `uv` when the app starts.

| Package | Version |
|---------|---------|
| `mlflow` | ≥3.11.1 |
| `databricks-langchain` | ≥0.19.0 |
| `psycopg[binary]` | ≥3.0 |
| `pgvector` | ≥0.3.0 |
| `langgraph` | ≥1.1.8 |
| `databricks-sdk` | ≥0.105.0 |
| `fastapi` | ≥0.129.0 |
| `uvicorn` | ≥0.41.0 |
| `python-dotenv` | ≥1.2.1 |

### Python Dependencies — Notebooks (`requirements.txt`)

Installed at the top of each notebook with `%pip install -r ../../requirements.txt`.

| Package | Pinned version |
|---------|---------------|
| `mlflow` | 3.11.1 |
| `databricks-langchain` | 0.19.0 |
| `psycopg[binary]` | ≥3.0 |
| `pgvector` | ≥0.3.0 |
| `langgraph` | 1.1.8 |
| `databricks-sdk` | 0.105.0 |
| `databricks-agents` | 1.9.4 |
| `beautifulsoup4` | 4.14.3 |
| `requests` | 2.33.1 |

### Environment Variables

#### Local development (`.env`)

```bash
DATABRICKS_CONFIG_PROFILE=andreas_workspace   # Databricks CLI profile
PGHOST=<lakebase-endpoint-hostname>           # From: scripts/get-pghost.sh
PGUSER=<app-service-principal-client-id>      # From: databricks apps get megacable-solutions | jq .service_principal_client_id
PGDATABASE=databricks_postgres
PGPORT=5432
PGSSLMODE=require
MLFLOW_EXPERIMENT_ID=<experiment-id>          # From: databricks bundle summary
```

#### Production (set by Databricks Apps automatically)

| Variable | Source | Value |
|----------|--------|-------|
| `DATABRICKS_HOST` | Platform | Workspace URL |
| `DATABRICKS_CLIENT_ID` | Platform | App service principal client ID (M2M OAuth) |
| `DATABRICKS_CLIENT_SECRET` | Platform | App service principal secret (M2M OAuth) |
| `API_PROXY` | `app.yaml` | `http://localhost:8080/invocations` — routes Node.js → Python agent |
| `MLFLOW_TRACKING_URI` | `app.yaml` | `databricks` |
| `MLFLOW_REGISTRY_URI` | `app.yaml` | `databricks-uc` |
| `MLFLOW_EXPERIMENT_ID` | Resource binding (`experiment`) | Injected from the bundle-managed MLflow experiment |
| `LAKEBASE_ENDPOINT` | Resource binding (`postgres`) | Injected Lakebase connection string |

### GitHub Actions Secrets (CI/CD)

| Secret | Value |
|--------|-------|
| `DATABRICKS_HOST` | Workspace URL (e.g. `https://my-workspace.cloud.databricks.com`) |
| `DATABRICKS_TOKEN` | Personal access token — **Settings → Developer → Access tokens** |

## Deployment

### 1. Clone and authenticate

```bash
git clone <repository-url>
cd megacable
databricks auth login --profile <your-profile>
```

### 2. Configure `databricks.yml`

Update the variables to match your environment:

```yaml
variables:
  uc_catalog:
    default: "workshop_andrea"
  uc_schema:
    default: "megacable"
  uc_volume:
    default: "megacable-unstructured"
```

The `serving_endpoint_name` and `experiment_id` variables are set automatically by the data pipeline job — you do not need to configure them manually.

### 3. Install dependencies and deploy

```bash
npm install
DATABRICKS_CONFIG_PROFILE=<your-profile> databricks bundle deploy
```

This provisions:
- **Databricks App** (`megacable-solutions`) — initially with no resource bindings
- **Lakebase Autoscaling project** (`megacable-ka-db-<suffix>`) for chat history
- **Serverless Job** (`create-and-deploy-model-<suffix>`) with scraper + translation + KA creation + evaluation tasks

### 4. Upload the knowledge base and run the data pipeline

First upload the local `knowledge_base_md/` folder to the UC volume:

```bash
databricks fs cp -r ./knowledge_base_md/ \
  dbfs:/Volumes/<uc_catalog>/<uc_schema>/<uc_volume>/knowledge_base_md/ \
  --profile <your-profile>
```

Then run the job to scrape Megacable solutions, translate the knowledge base, ingest into pgvector, evaluate the agent, and register production monitors:

```bash
DATABRICKS_CONFIG_PROFILE=<your-profile> databricks bundle run create_and_deploy_model
```

The job runs five tasks:

| Task | Depends on | What it does |
|------|-----------|-------------|
| `scrape_solutions` | — | Scrapes 8 Megacable solution pages → `output_solutions/` in UC Volume |
| `translate_knowledge_base` | — | Translates `knowledge_base_md/` to Spanish via `ai_translate()` → `knowledge_base_md_es/` |
| `create_vs_indexes` | both above | Embeds markdown using `databricks-gte-large-en`, upserts into two pgvector tables on Lakebase (`ai_vectorstore` schema) with HNSW indexes |
| `model_evaluation` | `create_vs_indexes` | Builds the LangGraph agent directly, runs MLflow GenAI evaluation (10 questions, 4 scorers), quality gate ≥80% `RetrievalGroundedness` |
| `model_monitoring` | `model_evaluation` | Registers continuous production monitoring scorers on the MLflow experiment |

`scrape_solutions` and `translate_knowledge_base` run in **parallel**.

### 5. Get the Lakebase database ID and redeploy

After the initial bundle deploy, the Lakebase Autoscaling project is provisioned. Retrieve the database ID and inject it into `databricks.yml`:

```bash
databricks postgres list-databases \
  "projects/megacable-ka-db-<suffix>/branches/production" \
  --profile <your-profile> --output json | jq -r '.[0].name'
```

Update the `lakebase_database_id` variable in `databricks.yml`:

```yaml
variables:
  lakebase_database_id:
    default: "<database-id-from-above>"
```

Then redeploy to wire up the app resource bindings:

```bash
DATABRICKS_CONFIG_PROFILE=<your-profile> databricks bundle deploy
```

The app bindings in `databricks.yml` are:

| Binding | Type | Permission |
|---------|------|-----------|
| `postgres` | Lakebase Autoscaling | `CAN_CONNECT_AND_CREATE` |
| `experiment` | MLflow Experiment | `CAN_EDIT` |

### 6. Grant database permissions

**Option A — Local script:**

```bash
pip install "databricks-sdk>=0.81.0" "psycopg[binary]>=3.0"

python3 scripts/lakebase-role-setup.py \
  --profile <your-profile> \
  --project-id megacable-ka-db-<suffix> \
  --sp-client-id <service-principal-client-id>
```

**Option B — Databricks notebook:**

Open `notebooks/setup/lakebase_role_setup.py` in your workspace and set the two widget parameters:

| Widget | Value |
|--------|-------|
| `project_id` | Lakebase project ID (e.g. `megacable-ka-db-dev-<username>`) |
| `sp_client_id` | App service principal client ID — from `databricks apps get megacable-solutions --output json \| jq -r '.service_principal_client_id'` |

### 7. Redeploy and start the app

```bash
DATABRICKS_CONFIG_PROFILE=<your-profile> databricks bundle deploy
DATABRICKS_CONFIG_PROFILE=<your-profile> databricks bundle run databricks_chatbot
```

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/deploy.yml`) fully automates the deployment.

### Pipeline stages

```
build-app → deploy-bundle → scrape-and-deploy-model → setup-db-and-redeploy → start-app
```

| Job | What it does |
|-----|-------------|
| `build-app` | Lint + build client and server |
| `deploy-bundle` | Strips `valueFrom` refs from `app.yaml` (phase 1 — resources don't exist yet), runs `databricks bundle deploy` |
| `scrape-and-deploy-model` | Uploads `knowledge_base_md/` to the UC volume, runs the full `create_and_deploy_model` job (scrape → translate → pgvector ingest → evaluate → monitor) |
| `setup-db-and-redeploy` | Gets Lakebase database ID, injects `lakebase_database_id` into `databricks.yml`, runs role setup for the app SP, redeploys with all resource bindings |
| `start-app` | `databricks bundle run databricks_chatbot` |

### Two-phase deployment explained

**Phase 1 (`deploy-bundle`):** Strips all `valueFrom` references from `app.yaml` so the initial deploy succeeds without any resource bindings.

**Phase 2 (`setup-db-and-redeploy`):** Injects `lakebase_database_id` into `databricks.yml`, runs Lakebase role setup for the app SP, then redeploys with all resource bindings wired up.

See the **GitHub Actions Secrets** table in the Requirements section above.

## Model Evaluation

The `model_evaluation.py` notebook evaluates the RAG agent using MLflow GenAI evaluation with 10 Spanish-language questions covering all 8 Megacable solution categories. The agent is **rebuilt directly in the notebook** (not loaded via `mlflow.pyfunc`) so that RETRIEVER spans are visible to the evaluation scorers.

### Scorers

| Scorer | What it measures |
|--------|-----------------|
| `RetrievalGroundedness` | Answers are grounded in retrieved documents |
| `response_en_espanol` (Guidelines) | Responses are fully in Spanish |
| `Safety` | Responses are free of harmful content |
| `RelevanceToQuery` | Responses are relevant to the question asked |

### Quality gate

The notebook raises an error (failing the job) if `RetrievalGroundedness` pass rate is ≤ 80%.

Results are logged to the MLflow experiment for review in the Databricks UI.

## Production Monitoring

The `model_monitoring.py` notebook registers continuous MLflow GenAI scorers on the RAG agent's MLflow experiment so that every production trace is automatically evaluated in the background.

The same four scorers used during offline evaluation are registered as live monitors at 100% sample rate. Monitor results appear in the MLflow Experiment UI under the **Monitoring** tab, typically within 15–20 minutes of a trace being recorded.

## Human Feedback

Every conversation is automatically logged as an MLflow trace. Users can rate responses in the chat UI (thumbs up/down) — feedback is stored as MLflow assessments on the traces.

## Local Development

```bash
cp .env.example .env
# Fill in DATABRICKS_CONFIG_PROFILE, PGHOST, PGUSER, PGDATABASE, PGPORT,
# DATABRICKS_SERVING_ENDPOINT, MLFLOW_EXPERIMENT_ID

npm install
npm run dev   # Frontend: localhost:3000 — Backend: localhost:3001
```

### Useful commands

```bash
npm run build          # Full build: DB migrate → client → server
npm run lint           # Lint and format with Biome
npm test               # Run Playwright E2E tests
npm run db:migrate     # Run pending DB migrations
npm run db:studio      # Open Drizzle Studio (visual DB editor)
databricks bundle summary   # Check deployed resource state
```

## Deployment Targets

| Target | Mode | Resource suffix |
|--------|------|-----------------|
| `dev` (default) | development | `dev-<username>` |
| `staging` | production | `staging` |
| `prod` | production | `prod` |

```bash
databricks bundle deploy -t staging
```

## Troubleshooting

### Bundle deploy fails with "valueFrom" resolution error

The app resource bindings reference resources (Lakebase database, MLflow experiment) that don't exist yet. This is expected on the first deploy — the CI/CD pipeline strips all `valueFrom` refs for the initial deploy, then reinjects them after the data pipeline runs.

### `lakebase_database_id` not set — bundle deploy fails

After the first `databricks bundle deploy`, retrieve the database ID and update `databricks.yml`:

```bash
databricks postgres list-databases \
  "projects/megacable-ka-db-<suffix>/branches/production" \
  --output json | jq -r '.[0].name'
```

Update `lakebase_database_id` in `databricks.yml`, then redeploy.

### Translation job fails

Ensure AI Functions are enabled in your workspace and that the `ai_translate` function is available in the SQL warehouse used by the serverless job. The `translate_knowledge_base` notebook is idempotent — re-running it skips already-translated files.

### "reference does not exist" errors

Update the Databricks CLI:

```bash
brew upgrade databricks
```

### "Resource not found" during bundle deploy

Resource state mismatch between bundle and workspace. Inspect with `databricks bundle summary`, then bind or unbind as needed:

```bash
databricks bundle unbind <resource-name>
```

See the [DAB FAQs](https://docs.databricks.com/aws/en/dev-tools/bundles/faqs) for details.
