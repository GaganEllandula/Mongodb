"""
Unit I & II: CRUD operations, atomic operators ($inc, $push, $set), and BSON types.
"""
import sys
import os
from bson import ObjectId, Decimal128

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.db_config import DatabaseManager

def execute_crud_lifecycle():
    db = DatabaseManager.get_database()

    print("--- 1. INSERTION (Create with BSON Types) ---")
    new_user = {
        "username": "vikram_singh",
        "email": "vikram.s@enterprise.com",
        "subscription_tier": "CORPORATE",
        "wallet_balance": Decimal128("1500.00"),
        "registered_fleet": [
            {
                "license_plate": "TS08EE8888",
                "vehicle_type": "SEDAN",
                "fuel_type": "EV",
                "dimensions": {"length_m": 4.6, "width_m": 1.82, "height_m": 1.48}
            }
        ]
    }
    insert_res = db.users.insert_one(new_user)
    created_user_id = insert_res.inserted_id
    print(f"Created User with BSON ObjectId: {created_user_id}")

    print("\n--- 2. ADVANCED QUERY (Read & Positional Array Projection) ---")
    query_criteria = {
        "subscription_tier": "CORPORATE",
        "registered_fleet.fuel_type": "EV"
    }
    projection = {"username": 1, "registered_fleet.$": 1, "wallet_balance": 1}
    user_doc = db.users.find_one(query_criteria, projection)
    print(f"Queried User: {user_doc['username']}, Balance: INR {user_doc['wallet_balance'].to_decimal()}")

    print("\n--- 3. ATOMIC OPERATORS (Update: $inc, $push) ---")
    db.users.update_one(
        {"_id": created_user_id},
        {
            "$inc": {"wallet_balance": Decimal128("500.00")},
            "$push": {
                "registered_fleet": {
                    "license_plate": "TS08MM1111",
                    "vehicle_type": "2W",
                    "fuel_type": "PETROL",
                    "dimensions": {"length_m": 1.9, "width_m": 0.75, "height_m": 1.1}
                }
            }
        }
    )
    refreshed = db.users.find_one({"_id": created_user_id})
    print(f"Updated Wallet Balance: INR {refreshed['wallet_balance'].to_decimal()}")
    print(f"Updated Fleet Count: {len(refreshed['registered_fleet'])}")

    print("\n--- 4. ATOMIC STATE TRANSITION (Concurrency Control) ---")
    slot = db.parking_slots.find_one({"status": "AVAILABLE", "size_class": "SEDAN"})
    if slot:
        res = db.parking_slots.update_one(
            {"_id": slot["_id"], "status": "AVAILABLE"},
            {"$set": {"status": "RESERVED"}}
        )
        print(f"Slot {slot['slot_number']} reserved atomically (matched={res.matched_count}, modified={res.modified_count})")

if __name__ == "__main__":
    try:
        execute_crud_lifecycle()
    finally:
        DatabaseManager.close_connection()