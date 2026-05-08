# config.py  (project root)
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT     = Path(__file__).parent
CREDENTIALS_PATH = PROJECT_ROOT / "files" / "sheet_reader_credentials.json"
DATA_DIR         = PROJECT_ROOT / "files"
OUTPUT_DIR       = PROJECT_ROOT / "output"
EDGES_CACHE_PATH = PROJECT_ROOT / "files" / "edges_cache.json"

# ---------------------------------------------------------------------------
# Google Sheets Input
# ---------------------------------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

SPREADSHEET_ID    = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"

# Stops
NODES_SHEET_NAME  = "stops"
NODE_COL_ID   = "stop_id"
NODE_COL_NAME = "stop_name"
NODE_COL_LAT  = "stop_lat"
NODE_COL_LON  = "stop_lon"


# ---------------------------------------------------------------------------
# OPEN RAIL ROUTING
# ---------------------------------------------------------------------------
OPEN_RAIL_ROUTING_URL     = "http://localhost:8989"
OPEN_RAIL_ROUTING_PROFILE = "tgv_all"

# ---------------------------------------------------------------------------
# Network / time window
# ---------------------------------------------------------------------------
# TIME_STEP_MIN       = 15          # resolution in minutes
#EARLIEST_DEPARTURE  = 18 * 60     # 18:00 in minutes from midnight
#LATEST_ARRIVAL      = 11 * 60     # 11:00 next day in minutes from midnight
#MAX_TRAVEL_TIME_MIN = (24 - 18 + 11) * 60  # 17 hours = 1020 minutes

# ---------------------------------------------------------------------------
# Train
# ---------------------------------------------------------------------------
#TRAIN_CAPACITY    = 200           # beds per train
#FIXED_COST        = 5000.0        # € per train operated
#COST_PER_HOUR     = 150.0         # € per hour of train operation
#COST_PER_KM       = 3.5           # € per km

# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------
#CG_TOLERANCE      = 1e-6          # column generation convergence threshold
#MAX_CG_ITERATIONS = 500