"""
Starts both the Python agent server (port 8080) and the Node.js Express server.

The agent server handles /invocations internally.
The Node.js server is the external entry point (listens on PORT from platform).
API_PROXY=http://localhost:8080/invocations connects the two.
"""
import subprocess
import sys
import time


def main():
    agent_proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "agent_server.start_server:app",
            "--host", "0.0.0.0",
            "--port", "8080",
        ]
    )
    print("Agent server starting on port 8080...")
    time.sleep(8)

    try:
        subprocess.run(["npm", "run", "start"], check=True)
    finally:
        agent_proc.terminate()
        agent_proc.wait()
