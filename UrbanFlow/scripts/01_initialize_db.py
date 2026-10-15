"""
Schema initialization script applying jsonSchema validators to all collections.
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.db_config import DatabaseManager
from schemas.collection_validators import (
    USERS_VALIDATOR,
    PARKING_SLOTS_VALIDATOR,
    PARKING_SESSIONS_VALIDATOR,
    TARIFF_POLICIES_VALIDATOR
)

COLLECTIONS = {
    "users": USERS_VALIDATOR,
    "parking_slots": PARKING_SLOTS_VALIDATOR,
    "parking_sessions": PARKING_SESSIONS_VALIDATOR,
    "tariff_policies": TARIFF_POLICIES_VALIDATOR
}

def deploy_schemas():
    db = DatabaseManager.get_database()
    existing_collections = db.list_collection_names()

    for col_name, validator in COLLECTIONS.items():
        if col_name in existing_collections:
            print(f"[INFO] Updating validator for existing collection: '{col_name}'...")
            db.command({
                "collMod": col_name,
                "validator": validator,
                "validationLevel": "strict",
                "validationAction": "error"
            })
        else:
            print(f"[INFO] Creating collection with validation: '{col_name}'...")
            db.create_collection(
                col_name,
                validator=validator,
                validationLevel="strict",
                validationAction="error"
            )
    print("[SUCCESS] All database collections and schema validations deployed successfully.")

if __name__ == "__main__":
    try:
        deploy_schemas()
    finally:
        DatabaseManager.close_connection()