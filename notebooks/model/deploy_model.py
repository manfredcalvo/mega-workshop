# Databricks notebook source
# COMMAND ----------
%pip install -r ../../requirements.txt
dbutils.library.restartPython()

# COMMAND ----------
"""
Deploys the registered Megacable RAG Agent model to a serving endpoint
and grants the app service principal CAN_QUERY access.

Runs after model_evaluation has passed the quality gate.

Expects Databricks notebook widget parameters:
  - model_name:      UC model name (catalog.schema.model)
  - model_version:   Registered model version to deploy
  - endpoint_name:   Serving endpoint name (created or updated)
  - app_sp_client_id: App service principal client ID for CAN_QUERY grant
  - experiment_id:   MLflow experiment ID (passed through to monitoring)
"""

# COMMAND ----------
dbutils.widgets.text("model_name",      "", "Model Name (UC path)")
dbutils.widgets.text("model_version",   "", "Model Version")
dbutils.widgets.text("endpoint_name",   "", "Serving Endpoint Name")
dbutils.widgets.text("app_sp_client_id", "", "App Service Principal Client ID")
dbutils.widgets.text("experiment_id",   "", "MLflow Experiment ID")

model_name       = dbutils.widgets.get("model_name")
model_version    = dbutils.widgets.get("model_version")
endpoint_name    = dbutils.widgets.get("endpoint_name")
app_sp_client_id = dbutils.widgets.get("app_sp_client_id")
experiment_id    = dbutils.widgets.get("experiment_id")

print(f"Model:         {model_name} v{model_version}")
print(f"Endpoint:      {endpoint_name}")
print(f"Experiment ID: {experiment_id}")

# COMMAND ----------
# --- Step 1: Wait for endpoint to be stable, then deploy ---
from databricks import agents
from databricks.sdk import WorkspaceClient

_w = WorkspaceClient()
try:
    _w.serving_endpoints.wait_get_serving_endpoint_not_updating(name=endpoint_name)
    print(f"Endpoint {endpoint_name} is stable — proceeding with deployment...")
except Exception:
    print(f"Endpoint {endpoint_name} does not exist yet — will be created.")

deployment = agents.deploy(
    model_name=model_name,
    model_version=int(model_version),
    endpoint_name=endpoint_name,
    scale_to_zero=True,
    workload_size="Small",
)
print(f"Agent deployed:  {endpoint_name}")
print(f"Query endpoint:  {deployment.query_endpoint}")

# COMMAND ----------
# --- Step 2: Grant app service principal CAN_QUERY on the endpoint ---
# agents.set_permissions() only supports users/groups, not service principals.
# Use the SDK directly with service_principal_name (the SP's client ID UUID).
from databricks.sdk.service import iam

if app_sp_client_id:
    endpoint_obj = _w.serving_endpoints.get(name=endpoint_name)
    _w.serving_endpoints.update_permissions(
        serving_endpoint_id=endpoint_obj.id,
        access_control_list=[
            iam.AccessControlRequest(
                service_principal_name=app_sp_client_id,
                permission_level=iam.PermissionLevel.CAN_QUERY,
            )
        ],
    )
    print(f"Granted CAN_QUERY to SP {app_sp_client_id} on {endpoint_name}")
else:
    print("No app_sp_client_id provided — skipping permission grant")

# COMMAND ----------
print("\n" + "=" * 60)
print("Deployment complete!")
print("=" * 60)
print(f"  Endpoint:      {endpoint_name}")
print(f"  Query URL:     {deployment.query_endpoint}")
print(f"  Model:         {model_name} v{model_version}")
print(f"  Experiment ID: {experiment_id}")

dbutils.jobs.taskValues.set(key="endpoint_name", value=endpoint_name)
dbutils.jobs.taskValues.set(key="experiment_id", value=str(experiment_id))

import json
dbutils.notebook.exit(json.dumps({
    "endpoint_name": endpoint_name,
    "experiment_id": experiment_id,
}))
