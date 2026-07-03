import sqlite3
db = sqlite3.connect(r'C:\Users\Mani\Desktop\RECEP\backend\api\recep.db')
cur = db.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cur.fetchall()]
print("Tables:", tables)
for t in tables:
    cur.execute("SELECT COUNT(*) FROM [" + t + "]")
    count = cur.fetchone()[0]
    print("  " + t + ": " + str(count) + " rows")
    if count > 0 and count <= 5:
        cur.execute("SELECT * FROM [" + t + "]")
        rows = cur.fetchall()
        cur.execute("PRAGMA table_info([" + t + "])")
        cols = [c[1] for c in cur.fetchall()]
        print("    cols:", cols)
        for row in rows:
            print("   ", row)
db.close()
