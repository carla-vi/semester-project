import socket, ssl, threading

# Ports
A_HOST, A_PORT = "0.0.0.0", 8002
B_HOST, B_PORT = "agent_b", 8001

CERT = "/certs/agentA.crt"
KEY  = "/certs/agentA.key"
CA   = "/certs/rootCA.crt"

# --- AUTHORIZATION POLICY ---
ALLOWED_USERS = {"Tom", "Alice"}  # only these CNs can access

def extract_cn(cert) -> str:
    """Get Common Name (CN) from cert subject"""
    for tup in cert.get("subject", []):
        for key, value in tup:
            if key == "commonName":
                return value
    return None

def forward_to_b(message: str) -> str:
    """Forward message to Agent B using mTLS"""
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=CA)
    context.load_cert_chain(certfile=CERT, keyfile=KEY)

    raw_sock = socket.create_connection((B_HOST, B_PORT))
    tls_sock = context.wrap_socket(raw_sock, server_hostname="agent_b")

    tls_sock.send(message.encode())
    reply = tls_sock.recv(1024).decode()
    tls_sock.close()
    return reply

def handle_person(tls_conn):
    try:
        client_cert = tls_conn.getpeercert()
        cn = extract_cn(client_cert)
        print(f"TLS handshake OK. Client CN = {cn}")

        if cn not in ALLOWED_USERS:
            print(f"Access denied for {cn}")
            tls_conn.send(b"Access denied")
            return

        msg = tls_conn.recv(1024).decode()
        print(f"Agent A received from {cn}: {msg}")

        reply_from_b = forward_to_b(f"{cn} says: {msg}")
        tls_conn.send(f"A forwarding B’s reply: {reply_from_b}".encode())
    finally:
        tls_conn.close()

def run_server_for_people():
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_cert_chain(certfile=CERT, keyfile=KEY)
    context.load_verify_locations(cafile=CA)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    sock.bind((A_HOST, A_PORT))
    sock.listen(5)
    print(f"Agent A listening on {A_HOST}:{A_PORT} with mTLS...")

    while True:
        conn, _ = sock.accept()
        try:
            tls_conn = context.wrap_socket(conn, server_side=True)
            threading.Thread(target=handle_person, args=(tls_conn,)).start()
        except ssl.SSLError as e:
            print("TLS handshake failed:", e)
            conn.close()

if __name__ == "__main__":
    run_server_for_people()
