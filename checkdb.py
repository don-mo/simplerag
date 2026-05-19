import sqlite3

conn = sqlite3.connect("opdecision.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("USERS:")
for row in cursor.execute("SELECT * FROM users"):
    print(dict(row))

print()
print("MESSAGES:")
for row in cursor.execute("SELECT * FROM messages"):
    print(dict(row))

conn.close()