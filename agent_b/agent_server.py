# agent_b_server.py
import socket, ssl, threading, requests, os, json, time
from tools import TOOL_REGISTRY
from capsule_db import allowed_users_for_agent  # ✅ ACL check
from tools import TOOL_REGISTRY


HOST, PORT = "0.0.0.0", 8001

CERT = "/certs/agentB.crt"
KEY  = "/certs/agentB.key"
CA   = "/certs/rootCA.crt"

OLLAMA_URL = "http://ollama:11434/api/chat"
MODEL = os.environ.get("OLLAMA_MODEL", "llama3:8b")

def ask_llm(user_message: str, max_retries=3) -> dict:
    """Ask Ollama, enforce JSON, decide between answer or tool."""
    tool_list = ", ".join(TOOL_REGISTRY.keys())
    system_prompt = f"""
You are Agent B, a reasoning assistant.

Rules:
- If the user asks for general knowledge (e.g., history, weather concept, math), reply directly with: {{"answer": "..."}}
- If the user asks about enterprise data (e.g., eggs, milk, bread prices), DO NOT guess.
  You MUST use the appropriate tool from this list: {", ".join(TOOL_REGISTRY.keys())}

Respond ONLY with a valid JSON object:
- Direct answer: {{"answer": "..."}}
- Tool request: {{"tool": "tool_name"}}

Never invent values. If unsure, call a tool.
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

    # fallback: treat reply as a plain answer
    return {"answer": reply}




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
            client_cert = tls_conn.getpeercert()
            print("TLS handshake done. Client cert CN:", client_cert.get("subject"))

            raw = tls_conn.recv(2048).decode()
            print("Agent B received:", raw)

            # 🔹 Parse JSON {user, msg}
            try:
                req = json.loads(raw)
                user = req.get("user")
                msg  = req.get("msg")
            except Exception as e:
                print("Invalid JSON from A:", e)
                tls_conn.send(b"Invalid request format")
                continue

            # 🔹 ACL check
            allowed_users = [u.lower() for u in allowed_users_for_agent("agent_b")]
            if user.lower() not in allowed_users:
                print(f"Access denied for {user} on Agent B")
                tls_conn.send(f"Access denied for {user}".encode())
                continue

            # 🔹 Ask LLM
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

            print("Final answer:", final_answer, "the user is:", user)
            tls_conn.send(f"B ({user}): {final_answer}".encode())

        except ssl.SSLError as e:
            print("TLS handshake failed:", e)
        finally:
            try:
                tls_conn.close()
            except:
                conn.close()



if __name__ == "__main__":
    run_agent_server()
