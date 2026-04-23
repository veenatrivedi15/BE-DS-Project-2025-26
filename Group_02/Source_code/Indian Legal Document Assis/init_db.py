import sqlite3

conn = sqlite3.connect("db.sqlite3")
cur = conn.cursor()


cur.execute("UPDATE users SET role='lawyer' WHERE email='gayush@gmail.com'")
conn.commit()



cur.execute("SELECT id, email, role FROM users")
rows = cur.fetchall()

print(rows)


print("Database created successfully!")