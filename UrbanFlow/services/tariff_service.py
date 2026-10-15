"""
Service: Dynamic Surge Pricing & Tariff Settlement Engine.
"""
from datetime import datetime, timezone
from decimal import Decimal
from bson.decimal128 import Decimal128
from config.db_config import DatabaseManager

class TariffEngine:
    def __init__(self):
        self.db = DatabaseManager.get_database()

    def calculate_current_occupancy_pct(self, facility_id: str = "CYBER_TOWER_HUB") -> float:
        total_slots = self.db.parking_slots.count_documents({"facility_id": facility_id})
        if total_slots == 0:
            return 0.0
        occupied_slots = self.db.parking_slots.count_documents({
            "facility_id": facility_id,
            "status": {"$in": ["OCCUPIED", "RESERVED"]}
        })
        return round((occupied_slots / total_slots) * 100, 2)

    def determine_surge_multiplier(self, vehicle_category: str, current_occ_pct: float) -> Decimal:
        policy = self.db.tariff_policies.find_one({"vehicle_category": vehicle_category})
        if not policy:
            return Decimal("1.0")

        multiplier = Decimal("1.0")
        # Check thresholds in ascending order (70% -> 1.5, 90% -> 2.5)
        for threshold in sorted(policy.get("occupancy_thresholds", []), key=lambda x: x["occupancy_pct"]):
            if current_occ_pct >= threshold["occupancy_pct"]:
                multiplier = Decimal(str(threshold["multiplier"]))
        return multiplier

    def compute_session_bill(self, session_id):
        session = self.db.parking_sessions.find_one({"_id": session_id})
        if not session:
            raise ValueError("Session document not found")

        policy = self.db.tariff_policies.find_one({"vehicle_category": session["vehicle_type"]})
        base_rate = policy["base_rate_per_hour"].to_decimal()
        ev_rate = policy["ev_unit_rate_kwh"].to_decimal()

        end_time = session.get("egress_time") or datetime.now(timezone.utc)
        start_time = session.get("ingress_time") or session.get("created_at")
        duration_hours = Decimal(str(max(0.5, (end_time - start_time).total_seconds() / 3600.0)))

        # Evaluate real-time occupancy and surge
        occ_pct = self.calculate_current_occupancy_pct()
        surge_mult = self.determine_surge_multiplier(session["vehicle_type"], occ_pct)
        parking_cost = round(base_rate * duration_hours * surge_mult, 2)

        total_kwh = Decimal("0.0")
        if session.get("ev_charging_telemetry"):
            max_reading = max([t["cumulative_kwh"] for t in session["ev_charging_telemetry"]])
            total_kwh = Decimal(str(max_reading))
        charging_cost = round(total_kwh * ev_rate, 2)

        total_amount = parking_cost + charging_cost

        return {
            "base_rate": Decimal128(str(base_rate)),
            "surge_multiplier": Decimal128(str(surge_mult)),
            "charging_cost": Decimal128(str(charging_cost)),
            "total_amount": Decimal128(str(total_amount))
        }