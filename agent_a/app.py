import socket, ssl, threading, traceback
import sqlite3, os, json, time
from capsule_db import init_db, bootstrap_capsule
from sync_listener import run_sync_listener
from update_server import run_update_server
from agent_server import run_server_for_people

def main():
    print("[AGENT A] Starting up...")

    # --- Initialize DB and capsule ---
    print("[AGENT A] Initializing database...")
    init_db()
    print("[AGENT A] DB initialized")

    print("[AGENT A] Bootstrapping capsule...")
    bootstrap_capsule()
    print("[AGENT A] Capsule bootstrapped")

    # --- Start background services ---
    print("[AGENT A] Starting sync listener thread...")
    threading.Thread(target=run_sync_listener, daemon=True).start()

    print("[AGENT A] Starting update server thread...")
    threading.Thread(target=run_update_server, daemon=True).start()

    # --- Run Agent A’s main server (blocking) ---
    print("[AGENT A] Launching main user-facing server...")
    run_server_for_people()

if __name__ == "__main__":
    main()