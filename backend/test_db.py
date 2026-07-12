import sqlite3
db = sqlite3.connect('aegis.db')
print(db.execute('SELECT * FROM alerts').fetchall())
