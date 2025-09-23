import socket, ssl, sys, traceback

A_HOST, A_PORT = "localhost", 8002

# Pick identity from CLI arg
name = sys.argv[1]  # e.g. python person.py Tom
CERT = f"certs/{name.lower()}.crt"
KEY  = f"certs/{name.lower()}.key"
CA   = "certs/rootCA.crt"

def main():
    print(f"[DEBUG PERSON] Starting as {name}")
    print(f"[DEBUG PERSON] Using cert={CERT}, key={KEY}, CA={CA}")

    try:
        # Build TLS context
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=CA)
        context.load_cert_chain(certfile=CERT, keyfile=KEY)
        print("[DEBUG PERSON] TLS context ready")

        # Connect to Agent A
        print(f"[DEBUG PERSON] Connecting to {A_HOST}:{A_PORT} ...")
        raw_sock = socket.create_connection((A_HOST, A_PORT))
        print("[DEBUG PERSON] TCP connection established")

        # Wrap with TLS
        tls_sock = context.wrap_socket(raw_sock, server_hostname="agent_a")
        print("[DEBUG PERSON] TLS handshake successful")

        # Check peer certificate
        server_cert = tls_sock.getpeercert()
        print(f"[DEBUG PERSON] Connected to A. Server CN: {server_cert.get('subject')}")

        # Send message
        msg = f"Hello A, this is {name}, get the average price of the eggs of our entreprise."
        print(f"[DEBUG PERSON] Sending: {msg}")
        tls_sock.send(msg.encode())

        # Receive reply
        reply = tls_sock.recv(1024).decode()
        print(f"[DEBUG PERSON] Reply from A: {reply}")

        tls_sock.close()
        print("[DEBUG PERSON] Connection closed")

    except Exception as e:
        print(f"[ERROR PERSON] Exception: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
