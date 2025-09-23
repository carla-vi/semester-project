# update_server.py
import socket, ssl, threading, json, time
from capsule_db import read_capsule, write_capsule, propagate_capsule, can_modify_acl

HOST, PORT = "0.0.0.0", 8602

CERT = "/certs/agentA.crt"   # replace per agent
KEY  = "/certs/agentA.key"
CA   = "/certs/rootCA.crt"


def extract_cn(cert) -> str:
    for tup in cert.get("subject", []):
        for key, value in tup:
            if key == "commonName":
                return value
    return None


def handle_update(tls_conn):
    try:
        client_cert = tls_conn.getpeercert()
        cn = extract_cn(client_cert)

        data = tls_conn.recv(8192).decode()
        req = json.loads(data)

        capsule = read_capsule()
        action = req.get("action")
        target_agent = req.get("agent")

        # --- Permission check ---
        if action == "add_admin":
            if cn not in capsule.get("admins", []):
                tls_conn.send(b"Access denied: not global admin")
                return
        else:
            if not can_modify_acl(cn, target_agent):
                tls_conn.send(b"Access denied: not allowed for this agent")
                return

        # --- Clone capsule ---
        new_capsule = json.loads(json.dumps(capsule))  # deep copy

        # --- Apply actions ---
        if action == "add_user_to_agent":
            user = req["user"]
            if user not in new_capsule["agents"][target_agent]["allowed_users"]:
                new_capsule["agents"][target_agent]["allowed_users"].append(user)

        elif action == "update_agent":
            tools = req.get("tools")
            crit = req.get("criticality")
            role = req.get("role")
            if tools:
                new_capsule["agents"][target_agent]["tools"] = tools
            if crit:
                new_capsule["agents"][target_agent]["criticality"] = crit
            if role:
                new_capsule["agents"][target_agent]["role"] = role

        elif action == "add_admin":
            new_capsule.setdefault("admins", [])
            if req["user"] not in new_capsule["admins"]:
                new_capsule["admins"].append(req["user"])

        else:
            tls_conn.send(b"Unknown action")
            return

        # --- Update metadata ---
        new_capsule["version"] = int(capsule["version"]) + 1 if capsule["version"] else 1
        new_capsule["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        new_capsule["author"] = cn

        # --- Save + propagate ---
        write_capsule(new_capsule, author=cn)
        propagate_capsule(new_capsule)

        tls_conn.send(b"Update accepted and propagated")

    except Exception as e:
        tls_conn.send(f"Error: {e}".encode())
    finally:
        tls_conn.close()


def run_update_server():
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_cert_chain(certfile=CERT, keyfile=KEY)
    context.load_verify_locations(cafile=CA)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    sock.bind((HOST, PORT))
    sock.listen(5)
    print(f"[UPDATE] Listening for ACL updates on {HOST}:{PORT}")

    while True:
        conn, _ = sock.accept()
        try:
            tls_conn = context.wrap_socket(conn, server_side=True)
            threading.Thread(target=handle_update, args=(tls_conn,)).start()
        except ssl.SSLError as e:
            print("TLS handshake failed:", e)
            conn.close()
