import psycopg2, sys

# Try all likely credential combos on port 5432
combos = [
    ("localhost", 5432, "postgres", "postgres", "postgres"),
    ("localhost", 5432, "postgres", "root",     "postgres"),
    ("localhost", 5432, "recep",    "recep",    "recep"),
    ("localhost", 5432, "postgres", "",         "postgres"),
]
for host, port, user, pwd, db in combos:
    try:
        conn = psycopg2.connect(host=host, port=port, user=user, password=pwd, database=db, connect_timeout=3)
        cur = conn.cursor()
        cur.execute("SELECT datname FROM pg_database WHERE datname NOT IN ('postgres','template0','template1')")
        dbs = [r[0] for r in cur.fetchall()]
        print(f"Connected {user}@{host}:{port} -> DBs: {dbs}")
        conn.close()
    except Exception as e:
        print(f"Failed {user}:{pwd}@{host}:{port}/{db} -> {e}")
