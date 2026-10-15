"""
End-to-End Workflow Simulation:
1. Register a user & recharge wallet.
2. Allocate bay & record ingress (vehicle entry).
3. Simulate EV charging telemetry during the stay.
4. Record egress (vehicle exit) & compute dynamic surge bill.
5. Deduct payment from wallet and release slot.
"""
import sys
import os
import time
from datetime import datetime, timezone, timedelta
from bson import Decimal128

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.db_config import DatabaseManager
from services.allocator_service import AllocationEngine
from services.tariff_service import TariffEngine

def run_simulation():
    db = DatabaseManager.get_database()
    allocator = AllocationEngine()
    tariff_engine = TariffEngine()

    print("=========================================================")
    print("      URBANFLOW: END-TO-END SMART PARKING LIFECYCLE      ")
    print("=========================================================\n")

    # -------------------------------------------------------------------------
    # STEP 1: Register User, Vehicle, and Initial Wallet
    # -------------------------------------------------------------------------
    print(">>> STEP 1: ONBOARDING USER & RECHARGING WALLET")
    test_user = {
        "username": "karthik_v",
        "email": "karthik.v@urbanflow.io",
        "subscription_tier": "REGULAR",
        "wallet_balance": Decimal128("200.00"),  # Initial low balance
        "registered_fleet": [
            {
                "license_plate": "TS09AB1122",
                "vehicle_type": "SUV",
                "fuel_type": "EV",
                "dimensions": {"length_m": 4.8, "width_m": 2.0, "height_m": 1.85}
            }
        ]
    }
    user_id = db.users.insert_one(test_user).inserted_id
    print(f"[OK] Registered user '{test_user['username']}' with Initial Wallet: INR 200.00")

    # Simulate wallet recharge via $inc
    db.users.update_one(
        {"_id": user_id},
        {"$inc": {"wallet_balance": Decimal128("800.00")}}
    )
    user_doc = db.users.find_one({"_id": user_id})
    print(f"[OK] Recharged wallet by INR 800.00. New Balance: INR {user_doc['wallet_balance'].to_decimal()}\n")

    # -------------------------------------------------------------------------
    # STEP 2: Vehicle Arrival & Smart Bay Allocation
    # -------------------------------------------------------------------------
    print(">>> STEP 2: VEHICLE INGRESS & BAY ALLOCATION")
    vehicle = user_doc["registered_fleet"][0]
    assigned_slot = allocator.allocate_optimal_bay(vehicle)

    if not assigned_slot:
        print("[FAIL] No suitable slot found!")
        return

    slot_id = assigned_slot["_id"]
    print(f"[OK] Matched Slot: {assigned_slot['slot_number']} (Floor {assigned_slot['floor']}, Class: {assigned_slot['size_class']})")
    print(f"[OK] Slot EV Capability: {assigned_slot['features']['has_ev_charger']} ({assigned_slot['features']['charger_power_kw']} kW)")

    # Mark slot OCCUPIED atomically
    db.parking_slots.update_one({"_id": slot_id}, {"$set": {"status": "OCCUPIED"}})

    # Create active session
    entry_time = datetime.now(timezone.utc) - timedelta(hours=2) # Simulated 2 hours ago
    session_doc = {
        "user_id": user_id,
        "slot_id": slot_id,
        "vehicle_plate": vehicle["license_plate"],
        "vehicle_type": vehicle["vehicle_type"],
        "lifecycle_state": "ACTIVE",
        "created_at": entry_time,
        "ingress_time": entry_time,
        "egress_time": None,
        "ev_charging_telemetry": [],
        "tariff_breakdown": {}
    }
    session_id = db.parking_sessions.insert_one(session_doc).inserted_id
    print(f"[OK] Boom barrier opened. Session logged (ID: {session_id})\n")

    # -------------------------------------------------------------------------
    # STEP 3: EV Charging Telemetry During Stay ($push)
    # -------------------------------------------------------------------------
    print(">>> STEP 3: TELEMETRY STREAMING (CHARGING CAR)")
    charging_updates = [
        {"timestamp": entry_time + timedelta(minutes=30), "power_draw_kw": 45.0, "cumulative_kwh": 22.5},
        {"timestamp": entry_time + timedelta(minutes=90), "power_draw_kw": 40.0, "cumulative_kwh": 60.0}
    ]
    for reading in charging_updates:
        db.parking_sessions.update_one(
            {"_id": session_id},
            {"$push": {"ev_charging_telemetry": reading}}
        )
    print(f"[OK] Streamed {len(charging_updates)} charging telemetry checkpoints to MongoDB.\n")

    # -------------------------------------------------------------------------
    # STEP 4: Vehicle Departure (Egress) & Dynamic Surge Pricing
    # -------------------------------------------------------------------------
    print(">>> STEP 4: VEHICLE EGRESS & BILL SETTLEMENT")
    exit_time = datetime.now(timezone.utc)
    db.parking_sessions.update_one(
        {"_id": session_id},
        {"$set": {"egress_time": exit_time, "lifecycle_state": "CHECKED_OUT"}}
    )

    # Compute tariff breakdown via tariff engine
    bill = tariff_engine.compute_session_bill(session_id)
    total_due = bill["total_amount"].to_decimal()

    print(f"--- TARIFF SUMMARY ---")
    print(f"Base Hourly Rate : INR {bill['base_rate'].to_decimal()}")
    print(f"Surge Multiplier : {bill['surge_multiplier'].to_decimal()}x")
    print(f"Electricity Cost : INR {bill['charging_cost'].to_decimal()}")
    print(f"Total Amount Due : INR {total_due}")

    # -------------------------------------------------------------------------
    # STEP 5: Payment Deduction & Releasing Bay
    # -------------------------------------------------------------------------
    # Deduct wallet balance ($inc with negative value)
    db.users.update_one(
        {"_id": user_id},
        {"$inc": {"wallet_balance": Decimal128(str(-total_due))}}
    )

    # Finalize session to SETTLED
    db.parking_sessions.update_one(
        {"_id": session_id},
        {"$set": {"lifecycle_state": "SETTLED", "tariff_breakdown": bill}}
    )

    # Release slot back to AVAILABLE
    db.parking_slots.update_one(
        {"_id": slot_id},
        {"$set": {"status": "AVAILABLE"}}
    )

    final_user = db.users.find_one({"_id": user_id})
    final_slot = db.parking_slots.find_one({"_id": slot_id})

    print(f"\n[OK] Wallet debited. Remaining Balance: INR {final_user['wallet_balance'].to_decimal()}")
    print(f"[OK] Slot {final_slot['slot_number']} reset to: {final_slot['status']}")
    print("\n[SUCCESS] Entire lifecycle completed successfully.")

if __name__ == "__main__":
    try:
        run_simulation()
    finally:
        DatabaseManager.close_connection()