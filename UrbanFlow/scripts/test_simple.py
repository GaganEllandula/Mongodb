import sys
import os
import time

# Ensure the project root directory (UrbanFlow) is in Python's module search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.simple_operations import add_user, add_vehicle, remove_vehicle, start_session, end_session

# 1. Add a new user with their vehicle
add_user("aravind", "aravind@gmail.com", "TS09EA1111", "SUV", "EV", initial_wallet=1000.0)

# 2. Add another vehicle for the same user
add_vehicle("aravind", "TS09EA2222", "2W", "PETROL")

# 3. Start parking for the SUV
start_session("TS09EA1111")

# Wait 2 seconds to simulate stay duration
time.sleep(2)

# 4. Car exits the parking, used 15 units of EV power
end_session("TS09EA1111", units_kwh_used=15.0)

# 5. Remove the bike if they sold it
remove_vehicle("aravind", "TS09EA2222")