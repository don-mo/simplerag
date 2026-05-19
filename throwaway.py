import sqlite3
con = sqlite3.connect(":memory:")  # in-memory DB, no file
cur = con.cursor()
cur.execute("CREATE TABLE users (email TEXT)")
cur.execute("INSERT INTO users VALUES (?)", ("alice@example.com",))

# Try the "attack" with parameterized query
malicious = "' OR '1'='1"
cur.execute("SELECT * FROM users WHERE email = ?", (malicious,))
print(cur.fetchall())  # Empty list! No match.

# Same query with f-string — DON'T DO THIS, just to see
cur.execute(f"SELECT * FROM users WHERE email = '{malicious}'")
print(cur.fetchall())  # Returns alice — the attack worked.