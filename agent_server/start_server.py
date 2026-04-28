from pathlib import Path

from dotenv import load_dotenv
from mlflow.genai.agent_server import AgentServer

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)

import agent_server.agent  # noqa: E402, F401 — registers @invoke/@stream handlers

agent_server_instance = AgentServer("ResponsesAgent", enable_chat_proxy=False)
app = agent_server_instance.app


def main():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
