import sqlite3

conn = sqlite3.connect('instance/app.db')
cursor = conn.cursor()
try:
    cursor.execute("ALTER TABLE user ADD COLUMN payment_method VARCHAR(20) DEFAULT 'ccp'")
except Exception as e:
    print("user payment_method error:", e)
try:
    cursor.execute("ALTER TABLE withdrawal_request ADD COLUMN payment_method VARCHAR(20) DEFAULT 'ccp'")
except Exception as e:
    print("withdrawal_request payment_method error:", e)
conn.commit()
conn.close()
print("Database updated.")
