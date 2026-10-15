"""
Unit IV: Real-Time Multi-Stage Aggregation Pipelines.
Covers $match, $group, $sort, $unwind, $facet, and $bucketAuto.
"""
import sys
import os
from tabulate import tabulate

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.db_config import DatabaseManager

def execute_occupancy_pipeline():
    db = DatabaseManager.get_database()
    
    pipeline = [
        # Stage 1: Group by floor and slot status
        {
            "$group": {
                "_id": {
                    "floor": "$floor",
                    "status": "$status"
                },
                "total_slots": {"$sum": 1}
            }
        },
        # Stage 2: Roll up status breakdown per floor
        {
            "$group": {
                "_id": "$_id.floor",
                "breakdown": {
                    "$push": {
                        "status": "$_id.status",
                        "count": "$total_slots"
                    }
                },
                "total_floor_bays": {"$sum": "$total_slots"}
            }
        },
        # Stage 3: Sort floors in ascending order
        {"$sort": {"_id": 1}}
    ]

    print(">>> PIPELINE 1: REAL-TIME FLOOR OCCUPANCY HEATMAP")
    results = list(db.parking_slots.aggregate(pipeline))
    table_rows = []
    for r in results:
        floor = r["_id"]
        total = r["total_floor_bays"]
        status_str = ", ".join([f"{item['status']}: {item['count']}" for item in r["breakdown"]])
        table_rows.append([f"Floor {floor}", total, status_str])

    print(tabulate(table_rows, headers=["Floor Level", "Total Bays", "Status Breakdown"], tablefmt="grid"))
    print("\n")

def execute_facet_cross_analytics():
    db = DatabaseManager.get_database()

    pipeline = [
        {
            "$facet": {
                # Sub-pipeline A: Revenue and volume per vehicle category
                "revenue_by_vehicle": [
                    {"$match": {"lifecycle_state": "SETTLED"}},
                    {
                        "$group": {
                            "_id": "$vehicle_type",
                            "settled_sessions": {"$sum": 1},
                            "total_revenue": {"$sum": "$tariff_breakdown.total_amount"},
                            "avg_revenue": {"$avg": "$tariff_breakdown.total_amount"}
                        }
                    },
                    {"$sort": {"total_revenue": -1}}
                ],
                # Sub-pipeline B: EV Power consumption analytics ($unwind)
                "ev_power_distribution": [
                    {"$match": {"ev_charging_telemetry": {"$exists": True, "$not": {"$size": 0}}}},
                    {"$unwind": "$ev_charging_telemetry"},
                    {
                        "$group": {
                            "_id": "$vehicle_type",
                            "total_energy_kwh": {"$max": "$ev_charging_telemetry.cumulative_kwh"},
                            "peak_draw_kw": {"$max": "$ev_charging_telemetry.power_draw_kw"}
                        }
                    }
                ],
                # Sub-pipeline C: Statistical auto-bucketing of settlement amounts
                "revenue_brackets": [
                    {"$match": {"lifecycle_state": "SETTLED"}},
                    {
                        "$bucketAuto": {
                            "groupBy": "$tariff_breakdown.total_amount",
                            "buckets": 3,
                            "output": {
                                "count": {"$sum": 1},
                                "sessions": {"$push": "$vehicle_plate"}
                            }
                        }
                    }
                ]
            }
        }
    ]

    print(">>> PIPELINE 2: EXECUTIVE FACETED REVENUE & TELEMETRY INSIGHTS ($facet)")
    facet_res = list(db.parking_sessions.aggregate(pipeline))[0]

    print("\n[Sub-Facet A: Settled Revenue Summary]")
    rev_data = [
        [
            item["_id"],
            item["settled_sessions"],
            f"INR {item['total_revenue'].to_decimal():.2f}" if hasattr(item["total_revenue"], "to_decimal") else f"INR {item['total_revenue']}",
            f"INR {item['avg_revenue'].to_decimal():.2f}" if hasattr(item["avg_revenue"], "to_decimal") else f"INR {item['avg_revenue']}"
        ]
        for item in facet_res["revenue_by_vehicle"]
    ]
    print(tabulate(rev_data, headers=["Vehicle Type", "Settled Count", "Total Revenue", "Avg Revenue"], tablefmt="simple"))

    print("\n[Sub-Facet B: EV Power Telemetry ($unwind)]")
    ev_data = [
        [item["_id"], f"{item['total_energy_kwh']} kWh", f"{item['peak_draw_kw']} kW"]
        for item in facet_res["ev_power_distribution"]
    ]
    print(tabulate(ev_data, headers=["Vehicle Type", "Max Cumulative Energy", "Peak Power Draw"], tablefmt="simple"))

    print("\n[Sub-Facet C: Statistical Auto-Bucketing ($bucketAuto)]")
    bucket_data = [
        [f"{b['_id']['min']} -> {b['_id']['max']}", b["count"], ", ".join(b["sessions"])]
        for b in facet_res["revenue_brackets"]
    ]
    print(tabulate(bucket_data, headers=["Bucket Range (INR)", "Session Count", "Vehicles Included"], tablefmt="simple"))

if __name__ == "__main__":
    try:
        execute_occupancy_pipeline()
        execute_facet_cross_analytics()
    finally:
        DatabaseManager.close_connection()