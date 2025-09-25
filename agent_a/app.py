import socket, ssl, threading, traceback
import sqlite3, os, json, time
from capsule_db import init_db, bootstrap_capsule
from sync_listener import run_sync_listener
from update_server import run_update_server
from agent_server import run_server_for_people

def main():
    
    init_db()
    bootstrap_capsule()
    threading.Thread(target=run_sync_listener, daemon=True).start()
    threading.Thread(target=run_update_server, daemon=True).start()
    run_server_for_people()

if __name__ == "__main__":
    main()