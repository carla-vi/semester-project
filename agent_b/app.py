import socket, ssl, requests
import os

HOST, PORT = "0.0.0.0", 8001

CERT = "/certs/agentB.crt"
KEY  = "/certs/agentB.key"
CA   = "/certs/rootCA.crt"

OLLAMA_URL = "http://ollama:11434/api/chat"
MODEL = os.environ.get("OLLAMA_MODEL", "llama3:8b")

def ask_llm(user_message: str) -> str:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are Agent B, a helpful assistant."},
            {"role": "user", "content": user_message}
        ],
        "stream": False,
    }
    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data.get("message", {}).get("content", "")
def main():
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

            data = tls_conn.recv(2048).decode()
            print("Agent B received:", data)

            # send to Ollama
            llm_reply = ask_llm(data)
            print("LLM reply:", llm_reply)

            # send back to Agent A
            tls_conn.send(f"B (LLM): {llm_reply}".encode())

        except ssl.SSLError as e:
            print("TLS handshake failed:", e)
        finally:
            try:
                tls_conn.close()
            except:
                conn.close()

if __name__ == "__main__":
    main()
