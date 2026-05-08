# scripts/test_routing_connection.py
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.routing.open_rail_routing import OpenRailRoutingTool
from data.network import Station, _round_to_15

tool = OpenRailRoutingTool()

vienna = Station(id="vienna", name="Wien Hbf",     lat=48.2082, lon=16.3738)
munich = Station(id="munich", name="München Hbf",  lat=48.1351, lon=11.5820)

distance_km, travel_time_min = tool.query(vienna, munich)

print(f"Distance:       {distance_km:.1f} km")
print(f"Raw time:       {travel_time_min:.1f} min")
print(f"Rounded time:   {_round_to_15(travel_time_min)} min")
print(f"Time steps:     {_round_to_15(travel_time_min) // 15} steps")