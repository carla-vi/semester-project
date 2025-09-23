# agent_b_server.py
import socket, ssl, threading, requests, os, json, time
from tools import TOOL_REGISTRY
from capsule_db import allowed_users_for_agent  # ✅ ACL check

HOST, PORT = "0.0.0.0", 8001

CERT = "/certs/agentB.crt"
KEY  = "/certs/agentB.key"
CA   = "/certs/rootCA.crt"

OLLAMA_URL = "http://ollama:11434/api/chat"
MODEL = os.environ.get("OLLAMA_MODEL", "gpt-oss:latest")  # e.g., "llama3:8b"


def ask_llm(user_message: str, max_retries=3) -> dict:
    """Ask Ollama, enforce JSON, decide between answer or tool."""
    system_prompt = f"""
You are Agent B, a reasoning assistant.

Rules:
- If the user asks for general knowledge, reply directly with: {{"answer": "..."}}
- If the user asks about enterprise data (e.g., eggs, milk, bread prices), DO NOT guess.
  You MUST use a tool from this list: {", ".join(TOOL_REGISTRY.keys())}

Respond ONLY with valid JSON:
- Direct answer: {{"answer": "..."}}
- Tool request: {{"tool": "tool_name"}}
"""

    for attempt in range(max_retries):
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "stream": False,
        }

        resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
        resp.raise_for_status()
        reply = resp.json().get("message", {}).get("content", "{}")

        print(f"[DEBUG] Raw LLM reply (attempt {attempt+1}): {repr(reply)}")

        try:
            return json.loads(reply)
        except json.JSONDecodeError:
            print("Invalid JSON, retrying...")
            time.sleep(1)

    return {"answer": reply}


def handle_agent_a(tls_conn):
    """Handle a forwarded request from Agent A"""
    try:
        client_cert = tls_conn.getpeercert()
        print("TLS handshake OK. Client CN:", client_cert.get("subject"))

        data = tls_conn.recv(2048).decode()
        print("Agent B received raw:", data)

        # ✅ Expect JSON {user, msg}
        try:
            req = json.loads(data)
            user = req.get("user")
            msg = req.get("msg")
        except Exception:
            tls_conn.send(b"Invalid request format")
            return

        # ✅ ACL check for Agent B
        
        allowed_users = [u.lower() for u in allowed_users_for_agent("agent_b")]
        if user.lower() not in allowed_users:
            print(f"Access denied for {user} on Agent B")
            tls_conn.send(f"Access denied for {user}".encode())
            return

        print(f"Agent B processing message from {user}: {msg}")
        decision = ask_llm(msg)
        print("Parsed LLM decision:", decision)

        if "tool" in decision:
            tool_name = decision["tool"]
            tool = TOOL_REGISTRY.get(tool_name)
            if tool:
                result = tool()
                final_answer = f"Tool {tool_name} result: {result}"
            else:
                final_answer = f"Unknown tool: {tool_name}"
        else:
            final_answer = decision.get("answer", "No answer")

        print("Final answer:", final_answer)
        tls_conn.send(f"B: {final_answer}".encode())

    finally:
        tls_conn.close()


def run_agent_server():
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_cert_chain(certfile=CERT, keyfile=KEY)
    context.load_verify_locations(cafile=CA)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    sock.bind((HOST, PORT))
    sock.listen(5)
    print(f"Agent B listening on {HOST}:{PORT} with mTLS...")

    while True:
        conn, _ = sock.accept()
        try:
            tls_conn = context.wrap_socket(conn, server_side=True)
            threading.Thread(target=handle_agent_a, args=(tls_conn,)).start()
        except ssl.SSLError as e:
            print("TLS handshake failed:", e)
            conn.close()


if __name__ == "__main__":
    run_agent_server()
