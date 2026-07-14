from services.shared.connection import get_connection

conn = get_connection()
print("Connected OK:", conn)
conn.close()