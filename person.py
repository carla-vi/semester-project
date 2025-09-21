import socket, ssl, sys

A_HOST, A_PORT = "localhost", 8002

# Pick identity from CLI arg
name = sys.argv[1]  # e.g. python person.py Tom
CERT = f"certs/tom.crt"
KEY  = f"certs/tom.key"
CA   = "certs/rootCA.crt"

def main():
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=CA)
    context.load_cert_chain(certfile=CERT, keyfile=KEY)

    raw_sock = socket.create_connection((A_HOST, A_PORT))
    tls_sock = context.wrap_socket(raw_sock, server_hostname="agent_a")

    server_cert = tls_sock.getpeercert()
    print(f"Connected to A. Server CN: {server_cert['subject']}")

    tls_sock.send(f"Hello A, this is {name}".encode())
    reply = tls_sock.recv(1024).decode()
    print(f"{name} received:", reply)
    tls_sock.close()

if __name__ == "__main__":
    main()