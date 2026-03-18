# BCP Products Chat Bot

A production-ready AI chatbot that answers questions about BCP credit card and loan products in Spanish. Built on Databricks with a Knowledge Assistant (KA) backend, a React + Express frontend, Lakebase Autoscaling for persistent chat history, and MLflow for traces, evaluations, and human feedback.

## Architecture

```
Web Scrapers (Notebooks)
  └─► UC Volume (Markdown files)
        └─► Knowledge Assistant (Agent Bricks KA)
              └─► KA Serving Endpoint
                    └─► Chat App (React + Express on Databricks Apps)
                          └─► Lakebase Autoscaling (PostgreSQL) — chat history
                          └─► MLflow Experiment — traces + human feedback
```

| Component | Technology |
|-----------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS |
| Backend | Express 5 + Vercel AI SDK (streaming) |
| AI Agent | Databricks Knowledge Assistant (Agent Bricks) |
| Database | Lakebase Autoscaling (managed PostgreSQL 17) |
| Observability | MLflow traces + GenAI evaluation |
| Deployment | Databricks Asset Bundle (DAB) + Databricks Apps |

## Project Structure

```
bcp/
├── client/                           # React frontend
├── server/                           # Express backend
├── packages/
│   ├── core/                         # Domain types and errors
│   ├── auth/                         # Databricks authentication
│   ├── db/                           # Drizzle ORM + PostgreSQL
│   └── utils/                        # Shared utilities
├── notebooks/
│   ├── data_processing/
│   │   ├── scraper_credit_cards.py   # Scrapes BCP credit card pages
│   │   └── scraper_loans.py          # Scrapes BCP loan product pages
│   ├── model/
│   │   └── create_ka.py             # Creates/updates Knowledge Assistant
│   └── evaluations/
│       └── model_evaluation.py       # MLflow GenAI evaluation (4 scorers)
├── scripts/
│   ├── lakebase-role-setup.py        # Grants app SP database permissions
│   ├── quickstart.sh                 # Interactive setup wizard
│   └── get-pghost.sh                 # Retrieve Lakebase endpoint hostname
├── .github/workflows/deploy.yml      # CI/CD pipeline
├── databricks.yml                    # Databricks Asset Bundle config
├── app.yaml                          # App runtime config (Node.js 20)
└── requirements.txt                  # Python deps for notebooks
```

## Prerequisites

### Databricks Workspace

| Requirement | Notes |
|-------------|-------|
| Databricks Apps | Must be enabled in the workspace |
| Serverless Compute | Required for notebook jobs |
| Unity Catalog | Required for UC Volume (scraped data) |
| Lakebase Autoscaling | Required for persistent chat history |
| MLflow | Required for traces and evaluation |

### Local Machine

| Tool | Version | Install |
|------|---------|---------|
| Databricks CLI | v0.240+ | `brew install databricks` |
| Node.js | 20.x | `nvm install 20` |
| Python | 3.11+ | System or pyenv |
| jq | any | `brew install jq` |

## Deployment

### 1. Clone and authenticate

```bash
git clone <repository-url>
cd bcp
databricks auth login --profile e2-field-eng
```

### 2. Configure `databricks.yml`

Update the variables to match your environment:

```yaml
variables:
  serving_endpoint_name:
    default: "ka-<your-endpoint-id>-endpoint"   # from create_ka.py output
  experiment_id:
    default: "<your-experiment-id>"              # from create_ka.py output
  uc_catalog:
    default: "users"
  uc_schema:
    default: "<your-schema>"
  uc_volume:
    default: "bcp"
```

### 3. Install dependencies and deploy

```bash
npm install
DATABRICKS_CONFIG_PROFILE=e2-field-eng databricks bundle deploy
```

This provisions:
- **Databricks App** (`bcp-products`) with KA endpoint and MLflow experiment resources
- **Lakebase Autoscaling project** (`bcp-ka-db-<suffix>`) for chat history
- **Serverless Job** (`create-and-deploy-model-<suffix>`) with scraper + KA creation + evaluation tasks

### 4. Run the data pipeline

Run the job to scrape BCP product pages, create the Knowledge Assistant, and evaluate it:

```bash
DATABRICKS_CONFIG_PROFILE=e2-field-eng databricks bundle run create_and_deploy_model
```

The job runs four tasks in sequence:
1. `scrape_credit_cards` — scrapes BCP credit card pages to UC Volume
2. `scrape_loans` — scrapes BCP loan pages to UC Volume
3. `create_ka` — creates/updates the Knowledge Assistant and triggers a sync
4. `model_evaluation` — runs MLflow GenAI evaluation with a quality gate (≥85% RetrievalGroundedness)

### 5. Update `app.yaml` with DB credentials

After the first deploy, retrieve the Lakebase hostname and set it in `app.yaml`:

```bash
DATABRICKS_CONFIG_PROFILE=e2-field-eng databricks postgres get-endpoint \
  projects/bcp-ka-db-<suffix>/branches/production/endpoints/primary \
  --output json | jq -r '.status.hosts.host'
```

Update `app.yaml`:

```yaml
env:
  - name: PGHOST
    value: "<your-lakebase-host>"
  - name: PGUSER
    value: "<app-service-principal-client-id>"
```

To find the service principal client ID:

```bash
DATABRICKS_CONFIG_PROFILE=e2-field-eng databricks apps get bcp-products \
  --output json | jq -r '.service_principal_client_id'
```

### 6. Grant database permissions

Run the role setup script to grant the app service principal the necessary PostgreSQL permissions:

```bash
pip install "databricks-sdk>=0.81.0" "psycopg[binary]>=3.0"

python3 scripts/lakebase-role-setup.py \
  --profile e2-field-eng \
  --project-id bcp-ka-db-<suffix> \
  --sp-client-id <service-principal-client-id>
```

### 7. Redeploy and start the app

```bash
DATABRICKS_CONFIG_PROFILE=e2-field-eng databricks bundle deploy
DATABRICKS_CONFIG_PROFILE=e2-field-eng databricks bundle run databricks_chatbot
```

The CLI prints the app URL when ready:

```
✓ App started successfully
You can access the app at https://bcp-products-<id>.aws.databricksapps.com
```

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/deploy.yml`) automates the full deployment:

```
build-app → deploy-bundle → scrape-and-create-ka → setup-db-and-redeploy → start-app
```

| Job | What it does |
|-----|-------------|
| `build-app` | Lint + build client and server |
| `deploy-bundle` | `databricks bundle deploy` |
| `scrape-and-create-ka` | Runs the `create_and_deploy_model` job, extracts KA endpoint name and experiment ID |
| `setup-db-and-redeploy` | Gets PGHOST from Lakebase, updates `app.yaml`, runs role setup, redeploys bundle with all config |
| `start-app` | `databricks bundle run databricks_chatbot` |

### Required GitHub Secrets

| Secret | Value |
|--------|-------|
| `DATABRICKS_HOST` | Your workspace URL (e.g. `https://e2-demo-field-eng.cloud.databricks.com`) |
| `DATABRICKS_CLIENT_ID` | Service principal client ID for CI/CD |
| `DATABRICKS_CLIENT_SECRET` | Service principal client secret |

## Model Evaluation

The `model_evaluation.py` notebook evaluates the KA using MLflow GenAI evaluation with 10 Spanish-language questions covering credit cards and loans.

### Scorers

| Scorer | What it measures |
|--------|-----------------|
| `RetrievalGroundedness` | Answers are grounded in retrieved documents |
| `response_en_espanol` (Guidelines) | Responses are fully in Spanish |
| `Safety` | Responses are free of harmful content |
| `RelevanceToQuery` | Responses are relevant to the question asked |

### Quality Gate

The notebook raises an error (failing the job) if `RetrievalGroundedness` pass rate is ≤ 85%:

```python
RETRIEVAL_GROUNDEDNESS_THRESHOLD = 0.85
```

Results are logged to the MLflow experiment for review in the Databricks UI.

## Human Feedback

Every conversation is automatically logged as an MLflow trace. Users can rate responses in the MLflow Experiment UI (thumbs up/down) — feedback is stored as MLflow assessments on the traces.

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

| Target | Mode | Suffix |
|--------|------|--------|
| `dev` (default) | development | `dev-<username>` |
| `staging` | production | `staging` |
| `prod` | production | `prod` |

```bash
databricks bundle deploy -t staging
```

## Troubleshooting

### Bundle deploy fails — "Database instance does not exist"

The `valueFrom: database` binding in `app.yaml` only works with Lakebase Provisioned, not Lakebase Autoscaling. This project uses Autoscaling, so `PGHOST` and `PGUSER` are set as explicit `value:` fields in `app.yaml`. Run Steps 5–7 above to configure them.

### "reference does not exist" errors

Update the Databricks CLI:

```bash
brew upgrade databricks
```

### "Resource not found" during bundle deploy

Resource state mismatch between bundle and workspace. Inspect with `databricks bundle summary`, then bind or unbind as needed:

```bash
databricks bundle unbind <resource-name>   # if manually deleted
```

See the [DAB FAQs](https://docs.databricks.com/aws/en/dev-tools/bundles/faqs) for details.

### Lakebase connection refused after inactivity

Lakebase Autoscaling wakes automatically on connection. The server implements retry logic — reactivation takes a few hundred milliseconds.
