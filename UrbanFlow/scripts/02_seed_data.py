"""
Seeds 5-Floor UrbanFlow Parking Structure (100 bays total) and loads 78% occupancy.
Floor 5: Half 2W, Half COMPACT (No EV)
Floor 4: All SUV (Fast EV 60kW)
Floor 3: All SEDAN (Fast EV 50kW)
Floor 2: Half VAN (No EV), Half COMPACT (EV 22kW)
Floor 0 (Ground): VAN + Overflow, with Aisle B dedicated to Handicapped priority.
"""
import sys
import os
import random
from datetime import datetime, timedelta, timezone
from bson.decimal128 import Decimal128

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.db_config import DatabaseManager

def seed_database():
    db = DatabaseManager.get_database()

    print("[RESET] Purging existing database collections...")
    db.users.delete_many({})
    db.parking_slots.delete_many({})
    db.parking_sessions.delete_many({})
    db.tariff_policies.delete_many({})

    # ---------------------------------------------------------
    # 1. TARIFF POLICIES (With your 70% -> 1.5x, 90% -> 2.5x rule)
    # ---------------------------------------------------------
    print("[SEED] Seeding Dynamic Tariff Policies...")
    surge_thresholds = [
        {"occupancy_pct": 70, "multiplier": 1.5},
        {"occupancy_pct": 90, "multiplier": 2.5}
    ]

    policies = [
        {"vehicle_category": "2W", "base_rate_per_hour": Decimal128("20.00"), "ev_unit_rate_kwh": Decimal128("12.00"), "occupancy_thresholds": surge_thresholds},
        {"vehicle_category": "COMPACT", "base_rate_per_hour": Decimal128("40.00"), "ev_unit_rate_kwh": Decimal128("15.00"), "occupancy_thresholds": surge_thresholds},
        {"vehicle_category": "SEDAN", "base_rate_per_hour": Decimal128("60.00"), "ev_unit_rate_kwh": Decimal128("15.00"), "occupancy_thresholds": surge_thresholds},
        {"vehicle_category": "SUV", "base_rate_per_hour": Decimal128("80.00"), "ev_unit_rate_kwh": Decimal128("16.00"), "occupancy_thresholds": surge_thresholds},
        {"vehicle_category": "VAN", "base_rate_per_hour": Decimal128("100.00"), "ev_unit_rate_kwh": Decimal128("18.00"), "occupancy_thresholds": surge_thresholds}
    ]
    db.tariff_policies.insert_many(policies)

    # ---------------------------------------------------------
    # 2. GENERATE 100 SLOTS ACROSS 5 FLOORS
    # ---------------------------------------------------------
    print("[SEED] Constructing 5-Floor Parking Structure (100 Slots Total)...")
    slots = []

    # Helper function to generate slot document
    def build_slot(floor, aisle, num, size_class, l, w, h, has_ev, kw, handicapped=False):
        return {
            "facility_id": "CYBER_TOWER_HUB",
            "floor": floor,
            "aisle": aisle,
            "slot_number": f"FL{floor}-{aisle}{num:02d}",
            "size_class": size_class,
            "clearance_dimensions": {"max_length_m": l, "max_width_m": w, "max_height_m": h},
            "features": {"has_ev_charger": has_ev, "charger_power_kw": kw, "is_handicapped": handicapped},
            "status": "AVAILABLE"
        }

    # FLOOR 5 (Top Floor): Half 2W, Half COMPACT (No EV)
    for i in range(1, 11):
        slots.append(build_slot(5, "A", i, "2W", 2.2, 1.0, 1.5, False, 0.0))
    for i in range(11, 21):
        slots.append(build_slot(5, "B", i, "COMPACT", 4.0, 2.0, 1.8, False, 0.0))

    # FLOOR 4: All SUV (With Fast EV Charger 60kW)
    for i in range(1, 11):
        slots.append(build_slot(4, "A", i, "SUV", 5.2, 2.4, 2.1, True, 60.0))
    for i in range(11, 21):
        slots.append(build_slot(4, "B", i, "SUV", 5.2, 2.4, 2.1, True, 60.0))

    # FLOOR 3: All SEDAN (With Fast EV Charger 50kW)
    for i in range(1, 11):
        slots.append(build_slot(3, "A", i, "SEDAN", 4.7, 2.2, 1.8, True, 50.0))
    for i in range(11, 21):
        slots.append(build_slot(3, "B", i, "SEDAN", 4.7, 2.2, 1.8, True, 50.0))

    # FLOOR 2: Half VAN (No EV), Half COMPACT (EV 22kW)
    for i in range(1, 11):
        slots.append(build_slot(2, "A", i, "VAN", 6.0, 2.6, 2.5, False, 0.0))
    for i in range(11, 21):
        slots.append(build_slot(2, "B", i, "COMPACT", 4.0, 2.0, 1.8, True, 22.0))

    # GROUND FLOOR (Floor 0): VAN + Overflow mix, Aisle B is Accessible/Handicapped
    for i in range(1, 7):
        slots.append(build_slot(0, "A", i, "VAN", 6.2, 2.8, 2.8, False, 0.0))
    # Overflow slots for standard vehicles on Ground floor
    overflow_classes = [("SEDAN", 4.7, 2.2, 1.8, True, 50.0), ("SUV", 5.2, 2.4, 2.1, True, 60.0), ("COMPACT", 4.0, 2.0, 1.8, False, 0.0), ("2W", 2.2, 1.0, 1.5, False, 0.0)]
    for idx, (sz, l, w, h, ev, kw) in enumerate(overflow_classes, start=7):
        slots.append(build_slot(0, "A", idx, sz, l, w, h, ev, kw))

    # Aisle B (Ground): Dedicated Handicapped/Priority slots
    handicapped_specs = [
        ("2W", 2.5, 1.2, 1.5, False, 0.0),
        ("COMPACT", 4.2, 2.4, 2.0, True, 22.0),
        ("SEDAN", 5.0, 2.4, 2.0, True, 50.0),
        ("SUV", 5.5, 2.6, 2.2, True, 60.0),
        ("VAN", 6.5, 2.8, 2.8, False, 0.0)
    ]
    for i in range(11, 21):
        sz, l, w, h, ev, kw = handicapped_specs[(i - 11) % 5]
        slots.append(build_slot(0, "B", i, sz, l, w, h, ev, kw, handicapped=True))

    slot_insert_res = db.parking_slots.insert_many(slots)
    all_slot_docs = list(db.parking_slots.find({}))
    print(f"[OK] Total Slots Deployed: {len(all_slot_docs)}")

    # ---------------------------------------------------------
    # 3. POPULATE USERS & SESSIONS TO ACHIEVE 78% OCCUPANCY
    # ---------------------------------------------------------
    print("[SEED] Generating Users and Sessions to bring building to 78% capacity...")
    now = datetime.now(timezone.utc)
    target_occupied_count = 78 # 78 out of 100 slots occupied

    users_to_insert = []
    sessions_to_insert = []
    slots_to_occupy = all_slot_docs[:target_occupied_count]

    for idx, slot in enumerate(slots_to_occupy):
        v_type = slot["size_class"]
        fuel = "EV" if slot["features"]["has_ev_charger"] else "PETROL"
        plate = f"TS{random.randint(10, 99):02d}AB{random.randint(1000, 9999):04d}"

        # Dimensions matching slot clearance
        dims = {
            "length_m": slot["clearance_dimensions"]["max_length_m"] - 0.2,
            "width_m": slot["clearance_dimensions"]["max_width_m"] - 0.2,
            "height_m": slot["clearance_dimensions"]["max_height_m"] - 0.1
        }

        user_doc = {
            "username": f"driver_{idx:03d}",
            "email": f"driver_{idx:03d}@urbanflow.in",
            "subscription_tier": random.choice(["REGULAR", "CORPORATE", "VIP"]),
            "wallet_balance": Decimal128(str(random.randint(500, 3000))),
            "registered_fleet": [
                {
                    "license_plate": plate,
                    "vehicle_type": v_type,
                    "fuel_type": fuel,
                    "dimensions": dims
                }
            ]
        }
        users_to_insert.append(user_doc)

    user_insert_res = db.users.insert_many(users_to_insert)
    inserted_user_ids = user_insert_res.inserted_ids

    # Create active sessions and set slots to OCCUPIED
    occupied_slot_ids = []
    for idx, slot in enumerate(slots_to_occupy):
        occupied_slot_ids.append(slot["_id"])
        in_time = now - timedelta(minutes=random.randint(20, 180))

        telemetry = []
        if slot["features"]["has_ev_charger"]:
            telemetry.append({"timestamp": in_time, "power_draw_kw": slot["features"]["charger_power_kw"], "cumulative_kwh": 0.0})
            telemetry.append({"timestamp": now, "power_draw_kw": slot["features"]["charger_power_kw"], "cumulative_kwh": random.uniform(8.0, 35.0)})

        session_doc = {
            "user_id": inserted_user_ids[idx],
            "slot_id": slot["_id"],
            "vehicle_plate": users_to_insert[idx]["registered_fleet"][0]["license_plate"],
            "vehicle_type": slot["size_class"],
            "lifecycle_state": "ACTIVE",
            "created_at": in_time,
            "ingress_time": in_time,
            "egress_time": None,
            "ev_charging_telemetry": telemetry,
            "tariff_breakdown": {}
        }
        sessions_to_insert.append(session_doc)

    db.parking_sessions.insert_many(sessions_to_insert)

    # Mark slots as OCCUPIED
    db.parking_slots.update_many(
        {"_id": {"$in": occupied_slot_ids}},
        {"$set": {"status": "OCCUPIED"}}
    )

    total_slots = db.parking_slots.count_documents({})
    total_occupied = db.parking_slots.count_documents({"status": "OCCUPIED"})
    current_pct = (total_occupied / total_slots) * 100

    print(f"\n[SUMMARY] Total Parking Bays: {total_slots}")
    print(f"[SUMMARY] Occupied Bays     : {total_occupied}")
    print(f"[SUMMARY] Live Occupancy Rate: {current_pct:.1f}% (Meets the >=70% threshold!)")
    print("[SUCCESS] Multi-floor structure & realistic high-density data seeded.")

if __name__ == "__main__":
    try:
        seed_database()
    finally:
        DatabaseManager.close_connection()