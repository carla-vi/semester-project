# agent_s_server.py
import socket, ssl, threading, requests, os, json
from capsule_db import read_capsule

HOST, PORT = "0.0.0.0", 8003   

CERT = "/certs/agentS.crt"   
KEY  = "/certs/agentS.key"
CA   = "/certs/rootCA.crt"

OLLAMA_URL = "http://ollama:11434/api/chat"
MODEL = os.environ.get("OLLAMA_MODEL", "llama3:8b")


def ask_llm_security_check(text: str) -> bool:
    """Check if input is malicious using LLM."""
    system_prompt = """
You are Agent S (security filter).
Decide if the incoming text is malicious.

Reply ONLY with JSON:
- {"malicious": true}
- {"malicious": false}
"""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        "stream": False,
    }

    resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
    resp.raise_for_status()
    reply = resp.json().get("message", {}).get("content", "{}")

    try:
        decision = json.loads(reply)
        return decision.get("malicious", True)  # default = block
    except:
        return True


def handle_connection(tls_conn):
    try:
        data = tls_conn.recv(4096).decode()

        malicious = ask_llm_security_check(data)
        if malicious:
            tls_conn.send(b"Rejected: malicious content")
            print("[S] External input rejected")
        else:
            tls_conn.send(b"Accepted: safe content")
            print("[S] External input passed")

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
    print(f"Agent S listening on {HOST}:{PORT} (bootstrap + security filter)")

    while True:
        conn, _ = sock.accept()
        try:
            tls_conn = context.wrap_socket(conn, server_side=True)
            threading.Thread(target=handle_connection, args=(tls_conn,)).start()
        except ssl.SSLError as e:
            print("[S] TLS handshake failed:", e)
            conn.close()
