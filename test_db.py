import os
import sqlite3

print("Current Working Directory:", os.getcwd())
print("---")

# Test 1: Database in current directory
try:
    conn = sqlite3.connect("test.db")
    conn.close()
    print("✓ Success: Created test.db in current folder")
    os.remove("test.db")
except Exception as e:
    print("✗ Failed in current folder:", e)

print("---")

# Test 2: Database in 'database' subdirectory
db_dir = os.path.join(os.getcwd(), "database")
print("Database directory path:", db_dir)

# Check if directory exists and is writable
if not os.path.exists(db_dir):
    print("Directory does not exist. Attempting to create...")
    try:
        os.makedirs(db_dir, exist_ok=True)
        print("✓ Directory created successfully")
    except Exception as e:
        print("✗ Failed to create directory:", e)
else:
    print("Directory exists")
    print("Directory writable?", os.access(db_dir, os.W_OK))

# Try to create a database inside it
db_path = os.path.join(db_dir, "test.db")
try:
    conn = sqlite3.connect(db_path)
    conn.close()
    print("✓ Success: Created test.db in 'database' folder")
    os.remove(db_path)
except Exception as e:
    print("✗ Failed in 'database' folder:", e)