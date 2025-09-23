# sync_listener.py
import socket, ssl, json, threading
from capsule_db import write_capsule, init_db

SYNC_HOST, SYNC_PORT = "0.0.0.0", 8502

CERT = "/certs/agentA.crt"
KEY  = "/certs/agentA.key"
CA   = "/certs/rootCA.crt"


def extract_cn(cert) -> str:
    for tup in cert.get("subject", []):
        for key, value in tup:
            if key == "commonName":
                return value
    return None


def handle_sync(tls_conn):
    try:
        client_cert = tls_conn.getpeercert()
        cn = extract_cn(client_cert)

        capsule_json = tls_conn.recv(16384).decode()
        capsule = json.loads(capsule_json)

        # basic sanity check
        if "version" not in capsule or "agents" not in capsule:
            print(f"[SYNC] Invalid capsule received from {cn}")
            return

        author = capsule.get("author", "unknown")
        write_capsule(capsule, author=author)
        print(f"[SYNC] Capsule v{capsule['version']} applied from {author} (via {cn})")

    except Exception as e:
        print("[SYNC] Error applying capsule:", e)
    finally:
        tls_conn.close()


def run_sync_listener():
    init_db()  # make sure DB is ready

    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_cert_chain(certfile=CERT, keyfile=KEY)
    context.load_verify_locations(cafile=CA)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    sock.bind((SYNC_HOST, SYNC_PORT))
    sock.listen(5)
    print(f"[SYNC] Listening on {SYNC_HOST}:{SYNC_PORT} for capsule updates...")

    while True:
        conn, _ = sock.accept()
        try:
            tls_conn = context.wrap_socket(conn, server_side=True)
            threading.Thread(target=handle_sync, args=(tls_conn,)).start()
        except ssl.SSLError as e:
            print("TLS handshake failed on sync socket:", e)
            conn.close()
