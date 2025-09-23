# capsule_db.py
import sqlite3, os, json, time, ssl, socket

DB_FILE = "sync_capsule.db"

CERT = "/certs/agentA.crt"
KEY  = "/certs/agentA.key"
CA   = "/certs/rootCA.crt"


def init_db():
    """Initialize SQLite schema if not exists"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Agents: each agent defines its role, tools, criticity and allowed users
    c.execute("""
        CREATE TABLE IF NOT EXISTS acl_agents (
            agent TEXT PRIMARY KEY,
            role TEXT,
            tools TEXT,
            criticality TEXT,
            allowed_users TEXT
        )
    """)

    # Admins: global override
    c.execute("CREATE TABLE IF NOT EXISTS acl_admins (user TEXT PRIMARY KEY)")

    # Trust levels
    c.execute("CREATE TABLE IF NOT EXISTS trust (entity TEXT PRIMARY KEY, score INTEGER, last_seen TEXT)")

    # Metadata (version, timestamp, signature, author…)
    c.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)")

    # Capsule history
    c.execute("""
        CREATE TABLE IF NOT EXISTS capsule_history (
            version INTEGER,
            timestamp TEXT,
            author TEXT,
            capsule_json TEXT,
            PRIMARY KEY(version)
        )
    """)
    conn.commit()
    conn.close()


def get_metadata(key):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT value FROM metadata WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None


def write_capsule(capsule: dict, author: str = "system"):
    """Write Sync Capsule into SQLite + keep last 2 versions"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # Save current as history
    current = read_capsule()
    if current and current.get("version"):
        c.execute("INSERT OR REPLACE INTO capsule_history VALUES (?,?,?,?)",
                  (int(current["version"]), current["timestamp"], get_metadata("author") or "unknown", json.dumps(current)))

    # Limit to last 2 versions
    c.execute("DELETE FROM capsule_history WHERE version NOT IN (SELECT version FROM capsule_history ORDER BY version DESC LIMIT 2)")

    # Overwrite current tables
    c.execute("DELETE FROM acl_agents")
    c.execute("DELETE FROM acl_admins")
    c.execute("DELETE FROM trust")
    c.execute("DELETE FROM metadata")

    # Agents with allowed users
    for agent, info in capsule["agents"].items():
        c.execute("INSERT INTO acl_agents VALUES (?,?,?,?,?)",
                  (agent, info["role"], ",".join(info["tools"]), info["criticality"], ",".join(info["allowed_users"])))

    # Admins
    for admin in capsule.get("admins", []):
        c.execute("INSERT INTO acl_admins VALUES (?)", (admin,))

    # Trust
    for ent, vals in capsule["trust"].items():
        c.execute("INSERT INTO trust VALUES (?,?,?)",
                  (ent, vals["score"], time.strftime("%Y-%m-%dT%H:%M:%SZ")))

    # Metadata
    for key in ["version", "timestamp", "signature"]:
        c.execute("INSERT INTO metadata VALUES (?,?)", (key, str(capsule[key])))
    c.execute("INSERT INTO metadata VALUES (?,?)", ("author", author))

    conn.commit()
    conn.close()
    print(f"[DEBUG] Capsule v{capsule['version']} stored (by {author})")


def read_capsule():
    """Rebuild capsule from DB"""
    if not os.path.exists(DB_FILE):
        return None

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    capsule = {"agents": {}, "admins": [], "trust": {}, "version": None, "timestamp": None, "signature": None}

    for row in c.execute("SELECT agent, role, tools, criticality, allowed_users FROM acl_agents"):
        capsule["agents"][row[0]] = {
            "role": row[1],
            "tools": row[2].split(",") if row[2] else [],
            "criticality": row[3],
            "allowed_users": row[4].split(",") if row[4] else []
        }

    for row in c.execute("SELECT user FROM acl_admins"):
        capsule["admins"].append(row[0])

    for row in c.execute("SELECT entity, score, last_seen FROM trust"):
        capsule["trust"][row[0]] = {"score": int(row[1]), "last_seen": row[2]}

    for key in ["version", "timestamp", "signature", "author"]:
        val = get_metadata(key)
        capsule[key] = val

    conn.close()
    return capsule


def get_history():
    """Return last 2 capsule versions"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT version, timestamp, author, capsule_json FROM capsule_history ORDER BY version DESC LIMIT 2")
    rows = c.fetchall()
    conn.close()
    return [{"version": v, "timestamp": t, "author": a, "capsule": json.loads(j)} for (v, t, a, j) in rows]


def allowed_users_for_agent(agent: str):
    """Return list of users allowed for a given agent"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT allowed_users FROM acl_agents WHERE agent=?", (agent,))
    row = c.fetchone()
    conn.close()
    return row[0].split(",") if row and row[0] else []


def can_modify_acl(user: str, agent: str) -> bool:
    """Check if a user can modify the ACL for a specific agent"""
    capsule = read_capsule()
    # Admin override
    if user in capsule.get("admins", []):
        return True
    # Local per-agent permission
    allowed = allowed_users_for_agent(agent)
    return user in allowed


def bootstrap_capsule():
    """Initial population from Agent S if DB empty"""
    if os.path.exists(DB_FILE):
        print("[DEBUG] Found existing DB, using stored capsule")
        return

    try:
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=CA)
        context.load_cert_chain(certfile=CERT, keyfile=KEY)

        print("[DEBUG] Connecting to Agent S for bootstrap...")
        raw_sock = socket.create_connection(("agent_s", 8443), timeout=10)
        tls_sock = context.wrap_socket(raw_sock, server_hostname="agent_s")
        tls_sock.send(b"sync_capsule")
        capsule_raw = tls_sock.recv(8192).decode()
        capsule = json.loads(capsule_raw)
        tls_sock.close()

        write_capsule(capsule, author="bootstrap@S")
        print("[DEBUG] Bootstrapped capsule from Agent S")
    except Exception as e:
        print("[WARN] Bootstrap from S failed:", e)



def propagate_capsule(capsule):
    """Send capsule to peers (B and C)"""
    peers = [("agent_b", 8502), ("agent_c", 8501)]
    capsule_json = json.dumps(capsule).encode()

    for host, port in peers:
        try:
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=CA)
            context.load_cert_chain(certfile=CERT, keyfile=KEY)
            raw_sock = socket.create_connection((host, port), timeout=10)
            tls_sock = context.wrap_socket(raw_sock, server_hostname=host)
            tls_sock.send(capsule_json)
            tls_sock.close()
            print(f"[SYNC] Capsule v{capsule['version']} propagated to {host}:{port}")
        except Exception as e:
            print(f"[WARN] Could not propagate to {host}:{port}: {e}")
