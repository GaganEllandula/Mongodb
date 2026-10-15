"""
Health-check script to verify local MongoDB instance.
"""
import sys
import os

# Ensure the root directory is in sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.db_config import DatabaseManager

def test_db_connection():
    try:
        db = DatabaseManager.get_database()
        ping_res = db.command('ping')
        print("[SUCCESS] MongoDB ping response:", ping_res)
        print(f"[SUCCESS] Connected to target database: '{db.name}'")
    except Exception as e:
        print(f"[FAIL] Connection test failed: {e}")
    finally:
        DatabaseManager.close_connection()

if __name__ == "__main__":
    test_db_connection()