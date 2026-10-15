"""
Strict JSON Schema ($jsonSchema) definitions for collections.
Enforces BSON data types, regular expressions, and enums at storage layer.
"""

USERS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["username", "email", "subscription_tier", "wallet_balance", "registered_fleet"],
        "properties": {
            "username": {"bsonType": "string", "minLength": 3},
            "email": {
                "bsonType": "string",
                "pattern": r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
            },
            "subscription_tier": {
                "enum": ["REGULAR", "CORPORATE", "VIP"]
            },
            "wallet_balance": {"bsonType": ["decimal", "double", "int"]},
            "registered_fleet": {
                "bsonType": "array",
                "minItems": 1,
                "items": {
                    "bsonType": "object",
                    "required": ["license_plate", "vehicle_type", "fuel_type", "dimensions"],
                    "properties": {
                        "license_plate": {
                            "bsonType": "string",
                            "pattern": r"^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$"
                        },
                        "vehicle_type": {
                            "enum": ["2W", "COMPACT", "SEDAN", "SUV", "VAN"]
                        },
                        "fuel_type": {
                            "enum": ["PETROL", "DIESEL", "EV", "HYBRID"]
                        },
                        "dimensions": {
                            "bsonType": "object",
                            "required": ["length_m", "width_m", "height_m"],
                            "properties": {
                                "length_m": {"bsonType": ["double", "int", "decimal"]},
                                "width_m": {"bsonType": ["double", "int", "decimal"]},
                                "height_m": {"bsonType": ["double", "int", "decimal"]}
                            }
                        }
                    }
                }
            }
        }
    }
}

PARKING_SLOTS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "facility_id", "floor", "aisle", "slot_number",
            "size_class", "clearance_dimensions", "features", "status"
        ],
        "properties": {
            "facility_id": {"bsonType": "string"},
            "floor": {"bsonType": "int"},
            "aisle": {"bsonType": "string"},
            "slot_number": {"bsonType": "string"},
            "size_class": {"enum": ["2W", "COMPACT", "SEDAN", "SUV", "VAN"]},
            "clearance_dimensions": {
                "bsonType": "object",
                "required": ["max_length_m", "max_width_m", "max_height_m"],
                "properties": {
                    "max_length_m": {"bsonType": ["double", "int", "decimal"]},
                    "max_width_m": {"bsonType": ["double", "int", "decimal"]},
                    "max_height_m": {"bsonType": ["double", "int", "decimal"]}
                }
            },
            "features": {
                "bsonType": "object",
                "required": ["has_ev_charger", "is_handicapped"],
                "properties": {
                    "has_ev_charger": {"bsonType": "bool"},
                    "charger_power_kw": {"bsonType": ["double", "int", "decimal"]},
                    "is_handicapped": {"bsonType": "bool"}
                }
            },
            "status": {
                "enum": ["AVAILABLE", "OCCUPIED", "MAINTENANCE", "RESERVED"]
            }
        }
    }
}

PARKING_SESSIONS_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "user_id", "slot_id", "vehicle_plate", "vehicle_type",
            "lifecycle_state", "created_at"
        ],
        "properties": {
            "user_id": {"bsonType": "objectId"},
            "slot_id": {"bsonType": "objectId"},
            "vehicle_plate": {"bsonType": "string"},
            "vehicle_type": {"enum": ["2W", "COMPACT", "SEDAN", "SUV", "VAN"]},
            "lifecycle_state": {
                "enum": ["RESERVED", "CHECKED_IN", "ACTIVE", "CHECKED_OUT", "SETTLED"]
            },
            "created_at": {"bsonType": "date"},
            "ingress_time": {"bsonType": ["date", "null"]},
            "egress_time": {"bsonType": ["date", "null"]},
            "ev_charging_telemetry": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "required": ["timestamp", "power_draw_kw", "cumulative_kwh"],
                    "properties": {
                        "timestamp": {"bsonType": "date"},
                        "power_draw_kw": {"bsonType": ["double", "int"]},
                        "cumulative_kwh": {"bsonType": ["double", "int"]}
                    }
                }
            },
            "tariff_breakdown": {
                "bsonType": "object",
                "properties": {
                    "base_rate": {"bsonType": ["decimal", "double", "int"]},
                    "surge_multiplier": {"bsonType": ["decimal", "double", "int"]},
                    "charging_cost": {"bsonType": ["decimal", "double", "int"]},
                    "total_amount": {"bsonType": ["decimal", "double", "int"]}
                }
            }
        }
    }
}

TARIFF_POLICIES_VALIDATOR = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["vehicle_category", "base_rate_per_hour", "ev_unit_rate_kwh"],
        "properties": {
            "vehicle_category": {"enum": ["2W", "COMPACT", "SEDAN", "SUV", "VAN"]},
            "base_rate_per_hour": {"bsonType": ["decimal", "double", "int"]},
            "ev_unit_rate_kwh": {"bsonType": ["decimal", "double", "int"]},
            "occupancy_thresholds": {
                "bsonType": "array",
                "items": {
                    "bsonType": "object",
                    "required": ["occupancy_pct", "multiplier"],
                    "properties": {
                        "occupancy_pct": {"bsonType": ["double", "int"]},
                        "multiplier": {"bsonType": ["double", "int"]}
                    }
                }
            }
        }
    }
}