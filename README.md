# UrbanFlow: Autonomous Multi-Tier Smart Parking Allocation 

UrbanFlow is an intelligent, multi-tier smart parking and mobility telemetry management system built with Python, PyMongo, and MongoDB. It features constraint-satisfaction slot allocation, live telemetry tracking for EV charging, dynamic occupancy-based surge pricing, and time-series capacity forecasting.

---

## 📌 Features

- **Multi-Level Facility Layout**: 5-floor parking facility (100 slots total) with dedicated tiers for 2-Wheelers, Compacts, Sedans, SUVs, Vans, and Ground Floor Accessible/Handicapped bays.
- **Strict Data Validation**: Strict schema enforcement using MongoDB `$jsonSchema` with BSON data types, regex validation (for license plates and emails), and enumerated constraints.
- **Constraint-Satisfaction Bay Allocation**: Matches vehicle physical dimensions ($L \times W \times H$), fuel type (EV charger requirements), and spatial proximity (floor/aisle optimization).
- **Dynamic Surge Pricing Engine**: Real-time occupancy tracking adjusting rates based on capacity thresholds (e.g., $1.5\times$ at $\ge 70\%$, $2.5\times$ at $\ge 90\%$).
- **EV Telemetry & Billing**: Ingests time-series power consumption curves (`kWh`, `kW`) and produces itemized settlement receipts.
- **Predictive Exhaustion Analytics**: Scikit-Learn linear regression forecaster predicting minutes remaining until parking facility saturation.
- **Performance Optimized**: Compound indexes (`status, size_class, floor`), unique constraints, and TTL auto-expiring reservation holds verified via `.explain()` index scans (`IXSCAN`).

---

## 🏗️ 5-Floor Facility Architecture

| Floor | Level | Allocation & Size Class | EV Charging Support | Special Features |
| :--- | :---: | :--- | :--- | :--- |
| **Top Floor** | `5` | `2W` (10 bays) + `COMPACT` (10 bays) | None | High-density light vehicles |
| **4th Floor** | `4` | `SUV` (20 bays) | Fast DC (60 kW) | High clearance bays |
| **3rd Floor** | `3` | `SEDAN` (20 bays) | Fast AC (50 kW) | Dedicated executive sedans |
| **2nd Floor** | `2` | `VAN` (10 bays) + `COMPACT` (10 bays) | Mixed (22 kW on Compacts) | Utility and compact EVs |
| **Ground Floor** | `0` | `VAN` & Mixed Overflow (10 bays) + Priority Bays (10 bays) | Mixed (50 kW DC) | Direct ground clearance + Handicapped accessibility |

---

## 📁 Project Structure

```text
UrbanFlow/
├── config/
│   ├── __init__.py
│   └── db_config.py             # Singleton MongoDB connection pooling manager
├── schemas/
│   ├── __init__.py
│   └── collection_validators.py # Strict $jsonSchema validation rules
├── services/
│   ├── __init__.py
│   ├── allocator_service.py     # Vehicle dimension & bay constraint matcher
│   └── tariff_service.py        # Dynamic surge pricing & settlement engine
├── scripts/
│   ├── __init__.py
│   ├── 01_initialize_db.py      # Schema deployment & validation setup
│   ├── 02_seed_data.py          # Seeds 100-bay structure & 78% occupancy state
│   ├── 03_crud_operations.py    # Atomic BSON updates, $inc, $push, array queries
│   ├── 04_index_optimization.py # Compound, unique, TTL indexes & explain() verification
│   ├── 05_analytics_engine.py   # Multi-stage pipelines ($facet, $bucketAuto, $unwind)
│   ├── 06_predictive_engine.py  # Linear regression capacity exhaustion forecaster
│   ├── 07_simulate_end_to_end.py# Full lifecycle simulation (entry to wallet deduction)
│   └── view_users.py            # Terminal inspection script for registered users
├── tests/
│   ├── __init__.py
│   └── test_connection.py       # MongoDB health check & cluster ping
├── requirements.txt
└── README.md
