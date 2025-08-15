import sqlite3

connection = sqlite3.connect('sqlite.db')
cursor = connection.cursor()

cursor.execute(('''
    CREATE TABLE dislike (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL );
    '''))

connection.commit()
connection.close()
