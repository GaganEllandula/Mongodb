"""
UrbanFlow Simple Functions:
All functions take plain user names, vehicle plate numbers, or simple numbers.
"""
import sys
import os
from datetime import datetime, timezone
from decimal import Decimal
from bson.decimal128 import Decimal128

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.db_config import DatabaseManager
from services.allocator_service import AllocationEngine
from services.tariff_service import TariffEngine

# Default dimensions per vehicle type to save you from typing them manually
DEFAULT_DIMS = {
    "2W": {"length_m": 2.0, "width_m": 0.8, "height_m": 1.2},
    "COMPACT": {"length_m": 3.8, "width_m": 1.7, "height_m": 1.5},
    "SEDAN": {"length_m": 4.5, "width_m": 1.8, "height_m": 1.5},
    "SUV": {"length_m": 4.8, "width_m": 2.0, "height_m": 1.9},
    "VAN": {"length_m": 5.8, "width_m": 2.4, "height_m": 2.3}
}

# =====================================================================
# FUNCTION 1: Add a User
# =====================================================================
def add_user(username: str, email: str, plate: str, vehicle_type: str, fuel_type: str, initial_wallet: float = 500.0):
    """
    Inputs:
      - username (str): e.g. "rahul_sharma"
      - email (str): e.g. "rahul@gmail.com"
      - plate (str): e.g. "TS09EA5555"
      - vehicle_type (str): "2W", "COMPACT", "SEDAN", "SUV", or "VAN"
      - fuel_type (str): "PETROL", "DIESEL", or "EV"
      - initial_wallet (float): e.g. 500.0 (optional, default 500)
    """
    db = DatabaseManager.get_database()
    v_type = vehicle_type.upper()
    dims = DEFAULT_DIMS.get(v_type, DEFAULT_DIMS["SEDAN"])

    user_doc = {
        "username": username,
        "email": email,
        "subscription_tier": "REGULAR",
        "wallet_balance": Decimal128(f"{initial_wallet:.2f}"),
        "registered_fleet": [
            {
                "license_plate": plate.upper(),
                "vehicle_type": v_type,
                "fuel_type": fuel_type.upper(),
                "dimensions": dims
            }
        ]
    }
    db.users.insert_one(user_doc)
    print(f"[OK] Added user '{username}' with vehicle '{plate.upper()}' and wallet balance INR {initial_wallet:.2f}")


# =====================================================================
# FUNCTION 2: Add a Vehicle to an Existing User
# =====================================================================
def add_vehicle(username: str, plate: str, vehicle_type: str, fuel_type: str):
    """
    Inputs:
      - username (str): Existing user's name e.g. "rahul_sharma"
      - plate (str): New vehicle plate e.g. "AP10BC7777"
      - vehicle_type (str): "2W", "COMPACT", "SEDAN", "SUV", or "VAN"
      - fuel_type (str): "PETROL", "DIESEL", or "EV"
    """
    db = DatabaseManager.get_database()
    user = db.users.find_one({"username": username})
    if not user:
        print(f"[FAIL] User '{username}' does not exist.")
        return

    v_type = vehicle_type.upper()
    new_vehicle = {
        "license_plate": plate.upper(),
        "vehicle_type": v_type,
        "fuel_type": fuel_type.upper(),
        "dimensions": DEFAULT_DIMS.get(v_type, DEFAULT_DIMS["SEDAN"])
    }

    db.users.update_one(
        {"username": username},
        {"$push": {"registered_fleet": new_vehicle}}
    )
    print(f"[OK] Added vehicle '{plate.upper()}' ({v_type}) to user '{username}'.")


# =====================================================================
# FUNCTION 3: Remove a Vehicle from an Existing User
# =====================================================================
def remove_vehicle(username: str, plate: str):
    """
    Inputs:
      - username (str): e.g. "rahul_sharma"
      - plate (str): Vehicle plate to delete e.g. "AP10BC7777"
    """
    db = DatabaseManager.get_database()
    user = db.users.find_one({"username": username})
    if not user:
        print(f"[FAIL] User '{username}' does not exist.")
        return

    if len(user.get("registered_fleet", [])) <= 1:
        print(f"[DENIED] Cannot remove vehicle. User must retain at least one registered vehicle.")
        return

    res = db.users.update_one(
        {"username": username},
        {"$pull": {"registered_fleet": {"license_plate": plate.upper()}}}
    )
    if res.modified_count > 0:
        print(f"[OK] Removed vehicle '{plate.upper()}' from user '{username}'.")
    else:
        print(f"[NOT FOUND] Plate '{plate.upper()}' was not found under user '{username}'.")


# =====================================================================
# FUNCTION 4: Start Parking Session
# =====================================================================
def start_session(plate: str, needs_handicapped: bool = False):
    """
    Inputs:
      - plate (str): Just pass the car's plate number e.g. "TS09EA5555"
      - needs_handicapped (bool): True if driver needs Ground Floor accessible bay (default False)
    """
    db = DatabaseManager.get_database()
    plate = plate.upper()

    # 1. Locate which user owns this vehicle
    user = db.users.find_one({"registered_fleet.license_plate": plate})
    if not user:
        print(f"[FAIL] Vehicle plate '{plate}' is not registered with any user. Please add user/vehicle first.")
        return

    # 2. Check if car is already currently parked
    active_check = db.parking_sessions.find_one({
        "vehicle_plate": plate,
        "lifecycle_state": "ACTIVE"
    })
    if active_check:
        print(f"[FAIL] Vehicle '{plate}' is ALREADY parked in an active session.")
        return

    # 3. Extract the vehicle object from user's fleet
    vehicle = next(v for v in user["registered_fleet"] if v["license_plate"] == plate)

    # 4. Check real-time occupancy and allocate bay
    allocator = AllocationEngine()
    slot = allocator.allocate_optimal_bay(vehicle, needs_handicapped=needs_handicapped)
    if not slot:
        print(f"[FULL] No eligible parking bays available for {vehicle['vehicle_type']}!")
        return

    # 5. Lock slot to OCCUPIED atomically
    slot_id = slot["_id"]
    db.parking_slots.update_one({"_id": slot_id}, {"$set": {"status": "OCCUPIED"}})

    # 6. Insert new parking session record
    now = datetime.now(timezone.utc)
    session_doc = {
        "user_id": user["_id"],
        "slot_id": slot_id,
        "vehicle_plate": plate,
        "vehicle_type": vehicle["vehicle_type"],
        "lifecycle_state": "ACTIVE",
        "created_at": now,
        "ingress_time": now,
        "egress_time": None,
        "ev_charging_telemetry": [],
        "tariff_breakdown": {}
    }
    db.parking_sessions.insert_one(session_doc)

    print("-------------------------------------------------------")
    print(f"[BARRIER OPEN] Vehicle '{plate}' has entered!")
    print(f"Driver Name  : {user['username']}")
    print(f"Assigned Bay : {slot['slot_number']} (Floor {slot['floor']}, Aisle {slot['aisle']})")
    print(f"Bay Class    : {slot['size_class']} | EV Charger: {slot['features']['has_ev_charger']}")
    print("-------------------------------------------------------")


# =====================================================================
# FUNCTION 5: End Parking Session (Shows Cost Breakdown)
# =====================================================================
def end_session(plate: str, units_kwh_used: float = 0.0):
    """
    Inputs:
      - plate (str): Just pass the car's plate number e.g. "TS09EA5555"
      - units_kwh_used (float): Electric units consumed if it charged (default 0.0)
    """
    db = DatabaseManager.get_database()
    plate = plate.upper()

    # 1. Find the active session for this car
    session = db.parking_sessions.find_one({
        "vehicle_plate": plate,
        "lifecycle_state": "ACTIVE"
    })
    if not session:
        print(f"[FAIL] No active parked session found for vehicle plate '{plate}'.")
        return

    session_id = session["_id"]
    slot_id = session["slot_id"]
    user_id = session["user_id"]
    now = datetime.now(timezone.utc)

    # 2. Update exit time and attach electric units if used
    update_data = {
        "egress_time": now,
        "lifecycle_state": "CHECKED_OUT"
    }
    if units_kwh_used > 0:
        update_data["ev_charging_telemetry"] = [
            {"timestamp": now, "power_draw_kw": 0.0, "cumulative_kwh": units_kwh_used}
        ]
    db.parking_sessions.update_one({"_id": session_id}, {"$set": update_data})

    # 3. Calculate dynamic surge & total cost
    tariff_engine = TariffEngine()
    bill = tariff_engine.compute_session_bill(session_id)
    total_due = bill["total_amount"].to_decimal()

    # 4. Deduct wallet & mark session SETTLED
    db.users.update_one(
        {"_id": user_id},
        {"$inc": {"wallet_balance": Decimal128(f"{-total_due:.2f}")}}
    )
    db.parking_sessions.update_one(
        {"_id": session_id},
        {"$set": {"lifecycle_state": "SETTLED", "tariff_breakdown": bill}}
    )

    # 5. Free up the slot back to AVAILABLE
    db.parking_slots.update_one(
        {"_id": slot_id},
        {"$set": {"status": "AVAILABLE"}}
    )

    user = db.users.find_one({"_id": user_id})
    slot = db.parking_slots.find_one({"_id": slot_id})

    # Print clean receipt
    print("================== PARKING EXIT RECEIPT ==================")
    print(f"Vehicle Number      : {plate}")
    print(f"Driver Name         : {user['username']}")
    print(f"Freed Up Bay        : {slot['slot_number']}")
    print(f"Base Hourly Rate    : INR {bill['base_rate'].to_decimal()}")
    print(f"Live Surge Applied  : {bill['surge_multiplier'].to_decimal()}x")
    print(f"EV Electricity Cost : INR {bill['charging_cost'].to_decimal()} ({units_kwh_used} kWh)")
    print(f"TOTAL COST BILLED   : INR {total_due}")
    print(f"Remaining Wallet    : INR {user['wallet_balance'].to_decimal()}")
    print("==========================================================")