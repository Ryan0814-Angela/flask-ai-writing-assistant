import sqlite3

conn = sqlite3.connect('users.db')  # 確保這個檔案跟你這個腳本在同一層資料夾
cursor = conn.cursor()

# 顯示資料表有哪些
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("📋 資料表列表:", tables)

# 查看 users 表格的欄位
cursor.execute("PRAGMA table_info(users);")
columns = cursor.fetchall()
print("🧱 users 欄位結構:")
for col in columns:
    print(col)

# 顯示所有使用者帳號
cursor.execute("SELECT * FROM users;")
users = cursor.fetchall()
print("👤 使用者資料:")
for user in users:
    print(user)

conn.close()
