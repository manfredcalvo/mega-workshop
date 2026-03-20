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
| Observability | MLflow traces + GenAI evaluation + production monitoring |
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
│   ├── evaluations/
│   │   └── model_evaluation.py       # MLflow GenAI evaluation (4 scorers)
│   └── monitoring/
│       └── model_monitoring.py       # MLflow GenAI production monitoring (4 scorers)
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
databricks auth login --profile <your-profile>
```

### 2. Configure `databricks.yml`

Update the variables to match your environment:

```yaml
variables:
  uc_catalog:
    default: "workshop_andrea"
  uc_schema:
    default: "bcp"
  uc_volume:
    default: "bcp-unstructured"
```

The `serving_endpoint_name` and `experiment_id` variables are set automatically by the data pipeline job — you do not need to configure them manually.

### 3. Install dependencies and deploy

```bash
npm install
DATABRICKS_CONFIG_PROFILE=<your-profile> databricks bundle deploy
```

This provisions:
- **Databricks App** (`bcp-products`) — initially with no resource bindings
- **Lakebase Autoscaling project** (`bcp-ka-db-<suffix>`) for chat history
- **Serverless Job** (`create-and-deploy-model-<suffix>`) with scraper + KA creation + evaluation tasks

### 4. Run the data pipeline

Run the job to scrape BCP product pages, create the Knowledge Assistant, and evaluate it:

```bash
DATABRICKS_CONFIG_PROFILE=<your-profile> databricks bundle run create_and_deploy_model
```

The job runs five tasks in sequence:

| Task | What it does |
|------|-------------|
| `scrape_credit_cards` | Scrapes BCP credit card pages → UC Volume |
| `scrape_loans` | Scrapes BCP loan pages → UC Volume |
| `create_ka` | Creates/updates the KA, triggers sync, outputs endpoint name and experiment ID |
| `model_evaluation` | Runs MLflow GenAI evaluation with a quality gate (≥85% RetrievalGroundedness) |
| `model_monitoring` | Registers and starts continuous production monitoring scorers on the MLflow experiment |

### 5. Add app resource bindings

Once the job completes, note the **endpoint name** and **experiment ID** printed by `create_ka`, then redeploy adding the resource bindings:

```bash
DATABRICKS_CONFIG_PROFILE=<your-profile> databricks bundle deploy \
  --var="serving_endpoint_name=<ka-endpoint-name>" \
  --var="experiment_id=<experiment-id>"
```

You can also manually edit `databricks.yml` to add the resources under the app:

```yaml
  apps:
    databricks_chatbot:
      name: bcp-products
      resources:
        - name: serving-endpoint
          serving_endpoint:
            name: <ka-endpoint-name>
            permission: CAN_QUERY
        - name: experiment
          experiment:
            experiment_id: "<experiment-id>"
            permission: CAN_EDIT
```

### 6. Configure DB credentials

Get the Lakebase hostname:

```bash
DATABRICKS_CONFIG_PROFILE=<your-profile> databricks postgres get-endpoint \
  projects/bcp-ka-db-<suffix>/branches/production/endpoints/primary \
  --output json | jq -r '.status.hosts.host'
```

Get the app service principal client ID:

```bash
DATABRICKS_CONFIG_PROFILE=<your-profile> databricks apps get bcp-products \
  --output json | jq -r '.service_principal_client_id'
```

Update `app.yaml`:

```yaml
env:
  - name: PGHOST
    value: "<your-lakebase-host>"
  - name: PGUSER
    value: "<app-service-principal-client-id>"
```

### 7. Grant database permissions

```bash
pip install "databricks-sdk>=0.81.0" "psycopg[binary]>=3.0"

python3 scripts/lakebase-role-setup.py \
  --profile <your-profile> \
  --project-id bcp-ka-db-<suffix> \
  --sp-client-id <service-principal-client-id>
```

### 8. Redeploy and start the app

```bash
DATABRICKS_CONFIG_PROFILE=<your-profile> databricks bundle deploy
DATABRICKS_CONFIG_PROFILE=<your-profile> databricks bundle run databricks_chatbot
```

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/deploy.yml`) fully automates the deployment in two phases.

### Pipeline stages

```
build-app → deploy-bundle → scrape-and-create-ka → setup-db-and-redeploy → start-app
```

| Job | What it does |
|-----|-------------|
| `build-app` | Lint + build client and server |
| `deploy-bundle` | Replaces `valueFrom` in `app.yaml` with empty values, then runs `databricks bundle deploy` — no resource bindings yet |
| `scrape-and-create-ka` | Runs the `create_and_deploy_model` job, extracts KA endpoint name and experiment ID from task output |
| `setup-db-and-redeploy` | Gets PGHOST from Lakebase, updates `app.yaml` with DB credentials, runs role setup, injects resource bindings into `databricks.yml`, redeploys |
| `start-app` | `databricks bundle run databricks_chatbot` |

### Two-phase deployment explained

The pipeline uses two deploys to handle the chicken-and-egg problem: the app needs a KA endpoint and MLflow experiment, but those are created by the job that runs after the first deploy.

**Phase 1 (`deploy-bundle`):** Strips all `valueFrom` references from `app.yaml` so the initial deploy succeeds without any resource bindings.

**Phase 2 (`setup-db-and-redeploy`):** Injects the actual resource bindings into `databricks.yml` and correct values into `app.yaml`, then redeploys with everything wired up.

### Required GitHub secrets

| Secret | Value |
|--------|-------|
| `DATABRICKS_HOST` | Your workspace URL (e.g. `https://e2-demo-field-eng.cloud.databricks.com`) |
| `DATABRICKS_TOKEN` | Personal access token — generate in **Settings → Developer → Access tokens** |

## Model Evaluation

The `model_evaluation.py` notebook evaluates the KA using MLflow GenAI evaluation with 10 Spanish-language questions covering credit cards and loans.

### Scorers

| Scorer | What it measures |
|--------|-----------------|
| `RetrievalGroundedness` | Answers are grounded in retrieved documents |
| `response_en_espanol` (Guidelines) | Responses are fully in Spanish |
| `Safety` | Responses are free of harmful content |
| `RelevanceToQuery` | Responses are relevant to the question asked |

### Quality gate

The notebook raises an error (failing the job) if `RetrievalGroundedness` pass rate is ≤ 85%.

Results are logged to the MLflow experiment for review in the Databricks UI.

## Production Monitoring

The `model_monitoring.py` notebook registers continuous MLflow GenAI scorers on the KA experiment so that every production trace is automatically evaluated in the background.

The same four scorers used during offline evaluation are registered as live monitors:

| Scorer | Sample rate |
|--------|-------------|
| `RetrievalGroundedness` | 100% |
| `response_en_espanol` (Guidelines) | 100% |
| `Safety` | 100% |
| `RelevanceToQuery` | 100% |

The notebook is **idempotent** — re-running it skips scorers that are already registered. Monitor results appear in the MLflow Experiment UI under the **Monitoring** tab, typically within 15–20 minutes of a trace being recorded.

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

| Target | Mode | Resource suffix |
|--------|------|-----------------|
| `dev` (default) | development | `dev-<username>` |
| `staging` | production | `staging` |
| `prod` | production | `prod` |

```bash
databricks bundle deploy -t staging
```

## Troubleshooting

### "Node ID does not exist" on bundle deploy

The `experiment_id` variable points to an experiment that doesn't exist in the workspace. Leave the default empty — the experiment ID is set automatically by the `create_ka` job. Use `--var="experiment_id=<id>"` only after the job has run.

### Bundle deploy fails with "valueFrom" resolution error

The app resource bindings reference a KA endpoint or MLflow experiment that doesn't exist yet. Deploy first without resources (Phase 1), run the data pipeline to create the KA, then redeploy with resource bindings (Phase 2).

### Lakebase DB credentials not working

The `valueFrom: database` binding in `app.yaml` only works with Lakebase Provisioned, not Lakebase Autoscaling. This project uses Autoscaling, so `PGHOST` and `PGUSER` are set as explicit `value:` fields. Run Steps 6–8 above to configure them.

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
