"""
Unit IV: Index Deployment and Performance Analysis using PyMongo explain().
Verifies IXSCAN stage vs COLLSCAN.
"""
import sys
import os
from pymongo import ASCENDING

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.db_config import DatabaseManager

def optimize_indexes():
    db = DatabaseManager.get_database()

    print("[INDEX] Creating compound, unique, and TTL indexes...")

    # 1. Compound index for allocation queries
    db.parking_slots.create_index(
        [("status", ASCENDING), ("size_class", ASCENDING), ("floor", ASCENDING)],
        name="idx_status_size_floor"
    )

    # 2. Unique index to prevent duplicate bay designations
    db.parking_slots.create_index(
        [("facility_id", ASCENDING), ("slot_number", ASCENDING)],
        unique=True,
        name="uidx_facility_slot"
    )

    # 3. Compound index for session lifecycle lookups
    db.parking_sessions.create_index(
        [("user_id", ASCENDING), ("lifecycle_state", ASCENDING)],
        name="idx_user_session_state"
    )

    # 4. TTL Index: purge expired unconfirmed reservations after 10 minutes (600s)
    db.parking_sessions.create_index(
        "created_at",
        expireAfterSeconds=600,
        partialFilterExpression={"lifecycle_state": "RESERVED"},
        name="ttl_unconfirmed_reservations"
    )

    print("[SUCCESS] All performance and lifecycle indexes applied.\n")

def run_explain_analysis():
    db = DatabaseManager.get_database()
    print("================ EXPLAIN EXECUTION STATS ================")
    query = {
        "status": "AVAILABLE",
        "size_class": "SUV",
        "floor": 1
    }

    # PyMongo explain() takes NO arguments and returns the explain document
    explanation = db.parking_slots.find(query).explain()
    
    # Extract executionStats if present, otherwise inspect queryPlanner winningPlan
    stats = explanation.get("executionStats")
    
    if stats:
        root_stage = stats.get("executionStages", {})
        print(f"Target Collection       : parking_slots")
        print(f"Query Filter            : {query}")
        print(f"Root Execution Stage    : {root_stage.get('stage')}")
        print(f"Total Docs Examined     : {stats.get('totalDocsExamined')}")
        print(f"Total Keys Examined     : {stats.get('totalKeysExamined')}")
        print(f"Docs Returned           : {stats.get('nReturned')}")
        print(f"Execution Time (ms)     : {stats.get('executionTimeMillis')} ms")

        # Trace down inputStage to verify IXSCAN under FETCH
        stage = root_stage.get("stage")
        child_stage = root_stage.get("inputStage", {}).get("stage")
        is_ixscan = (stage == "IXSCAN") or (child_stage == "IXSCAN")
    else:
        planner = explanation.get("queryPlanner", {})
        winning_plan = planner.get("winningPlan", {})
        stage = winning_plan.get("stage")
        child_stage = winning_plan.get("inputStage", {}).get("stage")
        is_ixscan = (stage == "IXSCAN") or (child_stage == "IXSCAN")
        index_name = winning_plan.get("inputStage", {}).get("indexName") or winning_plan.get("indexName")

        print(f"Target Collection       : parking_slots")
        print(f"Query Filter            : {query}")
        print(f"Winning Plan Stage      : {stage}")
        print(f"Input Stage             : {child_stage}")
        print(f"Index Utilized          : {index_name}")

    print(f"Index Scan Verified     : {is_ixscan}")
    if is_ixscan:
        print("\n[VERIFICATION PASSED] Query utilizes IXSCAN (Indexed scan). Zero full-collection (COLLSCAN) scanning overhead.")
    else:
        print("\n[WARNING] Query did not register IXSCAN.")

if __name__ == "__main__":
    try:
        optimize_indexes()
        run_explain_analysis()
    finally:
        DatabaseManager.close_connection()