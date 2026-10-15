"""
Unit VI: Time-Series / Linear Regression Forecaster & Allocation Dispatch.
"""
import sys
import os
import numpy as np
from sklearn.linear_model import LinearRegression

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.allocator_service import AllocationEngine
from services.tariff_service import TariffEngine
from config.db_config import DatabaseManager

def run_predictive_exhaustion_simulation():
    print("=== URBANFLOW PREDICTIVE OCCUPANCY & ALLOCATION ENGINE ===")
    tariff_svc = TariffEngine()
    allocator_svc = AllocationEngine()

    # Step 1: Linear Regression Occupancy Run-Rate Forecast
    time_minutes = np.array([0, 10, 20, 30, 40, 50]).reshape(-1, 1)
    observed_occupancy = np.array([45.0, 52.0, 60.0, 69.0, 77.0, 86.0])

    model = LinearRegression()
    model.fit(time_minutes, observed_occupancy)

    slope = model.coef_[0]
    intercept = model.intercept_
    target_capacity = 100.0
    minutes_to_exhaustion = (target_capacity - intercept) / slope - 50.0

    print(f"[MODEL] Regression Fit    : Occupancy(t) = {slope:.2f} * t + {intercept:.2f}")
    print(f"[MODEL] Rate of Inflow    : +{slope:.2f}% occupancy/min")
    print(f"[PREDICTION] Exhaustion In: {max(0.0, minutes_to_exhaustion):.1f} minutes\n")

    # Step 2: Intelligent Bay Allocation for an incoming SUV EV
    test_vehicle = {
        "vehicle_type": "SUV",
        "fuel_type": "EV",
        "dimensions": {"length_m": 4.9, "width_m": 2.1, "height_m": 1.9}
    }

    allocated_bay = allocator_svc.allocate_optimal_bay(test_vehicle)
    if allocated_bay:
        print("[ALLOCATION RESULT]")
        print(f"Vehicle Type : {test_vehicle['vehicle_type']} (Fuel: {test_vehicle['fuel_type']})")
        print(f"Assigned Bay : {allocated_bay['slot_number']}")
        print(f"Location     : Floor {allocated_bay['floor']}, Aisle {allocated_bay['aisle']}")
        print(f"Bay Class    : {allocated_bay['size_class']}")
        print(f"EV Charger   : {allocated_bay['features']['has_ev_charger']} ({allocated_bay['features']['charger_power_kw']} kW)")
    else:
        print("[ALLOCATION RESULT] No suitable bay found meeting physical and electrical criteria.")

    # Step 3: Dynamic Surge Calculation
    current_occ = tariff_svc.calculate_current_occupancy_pct()
    surge = tariff_svc.determine_surge_multiplier("SUV", current_occ)
    print(f"\n[SURGE ENGINE RESULT]")
    print(f"Live Facility Occupancy : {current_occ}%")
    print(f"Current Surge Multiplier: {surge}x")

if __name__ == "__main__":
    try:
        run_predictive_exhaustion_simulation()
    finally:
        DatabaseManager.close_connection()