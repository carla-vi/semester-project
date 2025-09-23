import threading
from capsule_db import init_db, bootstrap_capsule
from sync_listener import run_sync_listener
from update_server import run_update_server
from agent_server import run_agent_server

if __name__ == "__main__":
    # Init DB + capsule
    init_db()
    bootstrap_capsule()

    # Start background threads
    threading.Thread(target=run_sync_listener, daemon=True).start()
    threading.Thread(target=run_update_server, daemon=True).start()

    # Blocking: run Agent B main server
    run_agent_server()