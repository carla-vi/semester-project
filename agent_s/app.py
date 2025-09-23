import threading
import time
from capsule_db import init_db, bootstrap_capsule, read_capsule, propagate_capsule
from sync_listener import run_sync_listener
from update_server import run_update_server
from agent_server import run_agent_server


if __name__ == "__main__":
    print("[AGENT S] Starting up...")

    # --- Initialize DB and bootstrap capsule ---
    init_db()
    bootstrap_capsule()

    capsule = read_capsule()
    if capsule and capsule["agents"]:
        time.sleep(5)
        propagate_capsule(capsule)

    # --- Start background services ---
    threading.Thread(target=run_sync_listener, daemon=True).start()
    threading.Thread(target=run_update_server, daemon=True).start()

    # --- Run Agent S main server (blocking) ---
    run_agent_server()
