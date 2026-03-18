from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import Users
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.network import Internet
from diagrams.programming.framework import React
from diagrams.programming.language import NodeJS
from diagrams.custom import Custom
import os

ICONS = "/Users/manffred.calvosanchez/.claude/plugins/cache/fe-vibe/fe-workflows/1.4.1/skills/fe-architecture-diagram/resources/icons"

with Diagram(
    "BCP Products - Architecture",
    show=False,
    filename="/Users/manffred.calvosanchez/Documents/databricks/app-templates/bcp/docs/architecture",
    outformat="png",
    direction="LR",
    graph_attr={
        "splines": "ortho",
        "nodesep": "1.2",
        "ranksep": "2.0",
        "pad": "0.8",
        "fontsize": "16",
        "bgcolor": "white",
        "dpi": "150",
    },
    node_attr={"fontsize": "11"},
    edge_attr={"fontsize": "9"},
):

    # External
    users = Users("Users")
    bcp_web = Internet("viabcp.com\n(BCP Website)")

    # CI/CD
    with Cluster("CI/CD Pipeline"):
        github = Custom("GitHub\nActions", f"{ICONS}/cloud/airflow.png")

    # Databricks Platform
    with Cluster("Databricks Workspace"):

        # Asset Bundle
        with Cluster("Databricks Asset Bundle"):

            # Serverless Job
            with Cluster("Serverless Job\n(bcp-web-scrapers)"):
                scrape_cc = Custom("scrape\ncredit_cards", f"{ICONS}/databricks/workspace.png")
                scrape_loans = Custom("scrape\nloans", f"{ICONS}/databricks/workspace.png")
                create_ka = Custom("create\nKA", f"{ICONS}/databricks/workspace.png")

            # UC Volume
            uc_volume = Custom("UC Volume\nusers.manffred_calvosanchez.bcp\n(output_credit_cards/\noutput_loans/)", f"{ICONS}/databricks/unity_catalog.png")

            # Knowledge Assistant
            with Cluster("Knowledge Assistant"):
                ka = Custom("BCP Productos\nKA", f"{ICONS}/databricks/model_serving.png")

            # Lakebase
            lakebase = PostgreSQL("Lakebase\nAutoscaling DB\n(Chat History)")

            # App
            with Cluster("Databricks App\n(bcp-products)"):
                app_server = NodeJS("Express\nBackend")
                app_client = React("React\nFrontend")

    # Flow: CI/CD
    github >> Edge(label="deploy &\norchestrate", style="bold") >> scrape_cc

    # Flow: Scraping
    bcp_web >> Edge(label="scrape") >> scrape_cc
    bcp_web >> Edge(label="scrape") >> scrape_loans

    # Flow: Scraper → Volume
    scrape_cc >> Edge(label="markdown\nfiles") >> uc_volume
    scrape_loans >> Edge(label="markdown\nfiles") >> uc_volume

    # Flow: Scraper → KA creation (depends on both)
    scrape_cc >> Edge(style="dashed") >> create_ka
    scrape_loans >> Edge(style="dashed") >> create_ka

    # Flow: KA uses Volume
    uc_volume >> Edge(label="index\ndata") >> ka
    create_ka >> Edge(label="creates") >> ka

    # Flow: App connections
    ka >> Edge(label="AI\nresponses") >> app_server
    lakebase >> Edge(label="chat\npersistence") >> app_server
    app_server >> Edge() >> app_client

    # Flow: Users
    users >> Edge(label="browser") >> app_client
