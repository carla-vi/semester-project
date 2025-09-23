# agent_a_server.py
import socket, ssl, threading, traceback
from capsule_db import allowed_users_for_agent
import json

# Ports
A_HOST, A_PORT = "0.0.0.0", 8002
B_HOST, B_PORT = "agent_b", 8001

CERT = "/certs/agentA.crt"
KEY  = "/certs/agentA.key"
CA   = "/certs/rootCA.crt"


def extract_cn(cert) -> str:
    """Get Common Name (CN) from cert subject"""
    for tup in cert.get("subject", []):
        for key, value in tup:
            if key == "commonName":
                return value
    return None


def forward_to_b(message: str) -> str:
    """Forward message to Agent B using mTLS"""
    print(f"[DEBUG A] Preparing to forward message to B: {message}")
    print(f"[DEBUG A] Target host: {B_HOST}, port: {B_PORT}")

    try:
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=CA)
        context.load_cert_chain(certfile=CERT, keyfile=KEY)

        print("[DEBUG A] Creating raw TCP socket...")
        raw_sock = socket.create_connection((B_HOST, B_PORT), timeout=120)
        print("[DEBUG A] TCP connection established with B")

        print("[DEBUG A] Wrapping socket with TLS...")
        tls_sock = context.wrap_socket(raw_sock, server_hostname="agent_b")
        print("[DEBUG A] TLS handshake complete")

        print(f"[DEBUG A] Sending message: {message}")
        tls_sock.send(message.encode())

        reply = tls_sock.recv(1024).decode()
        print(f"[DEBUG A] Got reply from B: {reply}")

        tls_sock.close()
        return reply

    except Exception as e:
        print("[DEBUG A] Error while forwarding to B:", e)
        traceback.print_exc()
        return f"Error forwarding to B: {e}"


def handle_person(tls_conn):
    try:
        client_cert = tls_conn.getpeercert()
        cn = extract_cn(client_cert)
        cn_norm = cn.lower() if cn else None
        print(f"[DEBUG A] TLS handshake OK. Extracted CN = {cn} (normalized = {cn_norm})")
        print(f"[DEBUG A] Raw client cert: {client_cert}")

        # normalize all allowed users from DB
        allowed_users = [u.lower() for u in allowed_users_for_agent("agent_a")]
        print(f"[DEBUG A] Allowed users for agent_a: {allowed_users}")

        if cn_norm.lower() not in allowed_users:
            print(f"[DEBUG A] Access denied for {cn} (normalized = {cn_norm}).")
            tls_conn.send(f"Access denied for {cn}".encode())
            return

        msg = tls_conn.recv(1024).decode()
        print(f"[DEBUG A] Agent A received from {cn}: {msg}")

        # --- Wrap in JSON before sending to B ---
        payload = {"user": cn, "msg": msg}
        print(f"[DEBUG A] Forwarding payload to B: {payload}")
        reply_from_b = forward_to_b(json.dumps(payload))

        print(f"[DEBUG A] Reply from B for {cn}: {reply_from_b}")
        tls_conn.send(f"A forwarding B’s reply: {reply_from_b}".encode())
    except Exception as e:
        print(f"[ERROR A] Exception in handle_person: {e}")
    finally:
        print(f"[DEBUG A] Closing TLS connection for {cn}")
        tls_conn.close()



def run_server_for_people():
    """Run Agent A’s main server loop"""
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
