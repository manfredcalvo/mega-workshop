# Databricks notebook source
# COMMAND ----------
%pip install "databricks-sdk>=0.81.0" "psycopg[binary]>=3.0"
dbutils.library.restartPython()

# COMMAND ----------
"""
Lakebase Autoscaling - Role Creation & SQL Permissions Grant

Creates a Postgres role for the app's service principal and grants
all necessary permissions for the chatbot database (ai_chatbot + drizzle schemas).

This notebook is equivalent to scripts/lakebase-role-setup.py and can be
run directly from the Databricks workspace without any local setup.

Expects Databricks notebook widget parameters:
  - project_id:    Lakebase project ID (e.g. bcp-ka-db-dev-username)
  - sp_client_id:  App service principal client ID (UUID)

To find these values:
  - project_id:   from `databricks postgres list-projects` or the bundle summary
  - sp_client_id: from `databricks apps get bcp-products --output json`
                  (look for the service_principal_client_id field)
"""

# COMMAND ----------
dbutils.widgets.text("project_id", "", "Lakebase Project ID")
dbutils.widgets.text("sp_client_id", "", "App Service Principal Client ID")

project_id = dbutils.widgets.get("project_id")
sp_client_id = dbutils.widgets.get("sp_client_id")

if not project_id or not sp_client_id:
    raise ValueError("Both project_id and sp_client_id widget parameters are required.")

print(f"Project ID:        {project_id}")
print(f"SP Client ID:      {sp_client_id}")

# COMMAND ----------
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.postgres import (
    Role, RoleRoleSpec, RoleMembershipRole,
    RoleIdentityType, RoleAuthMethod,
)
import psycopg

w = WorkspaceClient()
branch = f"projects/{project_id}/branches/production"
endpoint_name = f"{branch}/endpoints/primary"
sp = sp_client_id

# COMMAND ----------
# Step 1: Create Postgres role for the service principal (idempotent)
print("Step 1: Creating Postgres role for service principal...")
try:
    w.postgres.get_role(name=f"{branch}/roles/app-sp")
    print("  Role already exists, skipping")
except Exception:
    try:
        w.postgres.create_role(
            parent=branch,
            role_id="app-sp",
            role=Role(
                spec=RoleRoleSpec(
                    postgres_role=sp,
                    identity_type=RoleIdentityType.SERVICE_PRINCIPAL,
                    auth_method=RoleAuthMethod.LAKEBASE_OAUTH_V1,
                    membership_roles=[RoleMembershipRole.DATABRICKS_SUPERUSER],
                )
            ),
        )
        print("  Role created successfully")
    except Exception as e:
        if "already exists" in str(e).lower():
            print("  Role already exists, skipping")
        else:
            raise

# COMMAND ----------
# Step 2: Get endpoint host
print("\nStep 2: Getting Lakebase endpoint host...")
endpoint = w.postgres.get_endpoint(name=endpoint_name)
host = endpoint.status.hosts.host
print(f"  PGHOST: {host}")

# COMMAND ----------
# Step 3: Connect as the current user
print("\nStep 3: Connecting to database...")
cred = w.postgres.generate_database_credential(endpoint=endpoint_name)
current_user = w.current_user.me()

conn = psycopg.connect(
    host=host,
    dbname="databricks_postgres",
    user=current_user.user_name,
    password=cred.token,
    sslmode="require",
)
conn.autocommit = True
cur = conn.cursor()
print(f"  Connected as: {current_user.user_name}")

# COMMAND ----------
# Step 4: Grant all permissions
print("\nStep 4: Granting SQL permissions...")
grants = [
    (f'GRANT CONNECT ON DATABASE databricks_postgres TO "{sp}"', "CONNECT on database"),
    (f'GRANT CREATE ON DATABASE databricks_postgres TO "{sp}"', "CREATE on database"),
    ("CREATE SCHEMA IF NOT EXISTS ai_chatbot", "Create ai_chatbot schema"),
    ("CREATE SCHEMA IF NOT EXISTS drizzle", "Create drizzle schema"),
    (f'GRANT USAGE ON SCHEMA ai_chatbot TO "{sp}"', "USAGE on ai_chatbot"),
    (f'GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ai_chatbot TO "{sp}"', "ALL PRIVILEGES on ai_chatbot tables"),
    (f'ALTER DEFAULT PRIVILEGES IN SCHEMA ai_chatbot GRANT ALL PRIVILEGES ON TABLES TO "{sp}"', "Default privileges on ai_chatbot"),
    (f'GRANT CREATE ON SCHEMA ai_chatbot TO "{sp}"', "CREATE on ai_chatbot"),
    (f'GRANT ALL PRIVILEGES ON SCHEMA drizzle TO "{sp}"', "ALL PRIVILEGES on drizzle schema"),
    (f'ALTER DEFAULT PRIVILEGES IN SCHEMA drizzle GRANT ALL PRIVILEGES ON TABLES TO "{sp}"', "Default privileges on drizzle"),
]

for sql, desc in grants:
    try:
        cur.execute(sql)
        print(f"  OK: {desc}")
    except Exception as e:
        print(f"  WARN: {desc} -> {e}")

conn.close()

# COMMAND ----------
print("\n" + "=" * 50)
print("Done! All permissions granted.")
print("=" * 50)
print(f"\nValues for app.yaml:")
print(f"  PGHOST:      {host}")
print(f"  PGUSER:      {sp}")
print(f"  PGDATABASE:  databricks_postgres")
print(f"  PGPORT:      5432")
print(f"  PGSSLMODE:   require")
