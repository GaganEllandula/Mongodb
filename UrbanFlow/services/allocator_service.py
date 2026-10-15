"""
Service: Intelligent Multi-Tier Constraint Satisfaction Slot Allocator.
Matches clearance boundaries, EV charging, and handicapped accessibility.
"""
from typing import Optional, Dict, Any
from bson import ObjectId
from config.db_config import DatabaseManager

SIZE_HIERARCHY = {
    "2W": ["2W"],
    "COMPACT": ["COMPACT", "SEDAN", "SUV"],
    "SEDAN": ["SEDAN", "SUV"],
    "SUV": ["SUV"],
    "VAN": ["VAN"]
}

class AllocationEngine:
    def __init__(self):
        self.db = DatabaseManager.get_database()

    def allocate_optimal_bay(self, vehicle: Dict[str, Any], needs_handicapped: bool = False) -> Optional[Dict[str, Any]]:
        v_type = vehicle["vehicle_type"]
        dims = vehicle["dimensions"]
        is_ev = (vehicle["fuel_type"] == "EV")
        eligible_sizes = SIZE_HIERARCHY.get(v_type, [v_type])

        allocation_query = {
            "status": "AVAILABLE",
            "size_class": {"$in": eligible_sizes},
            "clearance_dimensions.max_length_m": {"$gte": dims["length_m"]},
            "clearance_dimensions.max_width_m": {"$gte": dims["width_m"]},
            "clearance_dimensions.max_height_m": {"$gte": dims["height_m"]}
        }

        if is_ev:
            allocation_query["features.has_ev_charger"] = True

        if needs_handicapped:
            allocation_query["features.is_handicapped"] = True
        else:
            # Regular users should not take handicapped slots unless necessary
            allocation_query["features.is_handicapped"] = False

        # Sort: 1. Floor Ascending (Ground Floor 0 first), 2. Aisle, 3. Slot Number
        best_slot = self.db.parking_slots.find_one(
            allocation_query,
            sort=[("floor", 1), ("aisle", 1), ("slot_number", 1)]
        )

        # Fallback: If no regular slots are available and top floors are full, allow regular to use non-handicapped anywhere
        if not best_slot and not needs_handicapped:
            del allocation_query["features.is_handicapped"]
            best_slot = self.db.parking_slots.find_one(
                allocation_query,
                sort=[("floor", 1), ("aisle", 1), ("slot_number", 1)]
            )

        return best_slot

    def reserve_slot_transactional(self, slot_id: ObjectId) -> bool:
        result = self.db.parking_slots.update_one(
            {"_id": slot_id, "status": "AVAILABLE"},
            {"$set": {"status": "RESERVED"}}
        )
        return result.modified_count == 1