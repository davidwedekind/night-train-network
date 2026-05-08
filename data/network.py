# data/network.py
from dataclasses import dataclass, field
from pathlib import Path
from config import CREDENTIALS_PATH, SPREADSHEET_ID, NODES_SHEET_NAME, EDGES_CACHE_PATH, SCOPES
from google.oauth2.service_account import Credentials

import gspread
import networkx as nx
import json



# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Station:
    id: str
    name: str
    lat: float  #coordinate system?
    lon: float  #coordinate system?

@dataclass
class Edge:
    from_id: str
    to_id: str
    distance_km: float        # distance on track network in km
    min_travel_time_min: int  # minimum train traveling time in min

    @property
    def travel_time_steps(self) -> int:
        """Number of 15-min time steps. Always exact since travel_time_min is pre-rounded."""
        return _round_to_15(self.min_travel_time_min) // 15

@dataclass
class RailNetwork:
    stations: dict[str, Station]    # keyed by station id
    edges: list[Edge]
    graph: nx.DiGraph = field(default_factory=nx.DiGraph)

    def build_graph(self) -> None:
        """Populate the NetworkX DiGraph from stations and edges."""
        for s in self.stations.values():
            self.graph.add_node(s.id, name=s.name, lat=s.lat, lon=s.lon)

        for e in self.edges:
            self.graph.add_edge(
                e.from_id, e.to_id,
                distance_km=e.distance_km,
                min_travel_time_min=e.min_travel_time_min,
                min_travel_time_steps=e.travel_time_steps
            )

    def summary(self) -> str:
        return (
            f"RailNetwork: {len(self.stations)} stations, "
            f"{len(self.edges)} directed edges"
        )

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _round_to_15(minutes: float) -> int:
    """Round travel time up to the nearest 15-minute interval."""
    import math
    return int(math.ceil(minutes / 15)) * 15

def _get_gspread_client(credentials_path: str) -> gspread.Client:
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return gspread.authorize(creds)

# ---------------------------------------------------------------------------
# Stage 1 — Load nodes from Google Sheets
# ---------------------------------------------------------------------------

def load_stations_from_sheets(
    spreadsheet_id: str = SPREADSHEET_ID,
    sheet_name: str = NODES_SHEET_NAME,
    credentials_path: str = str(CREDENTIALS_PATH),
) -> dict[str, Station]:
    """
    Load station nodes from a Google Sheets tab.
    Expected columns: id, name, lat, lon
    Returns a dict keyed by station id.
    """
    client = _get_gspread_client(credentials_path)
    sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
    records = sheet.get_all_records()

    if not records:
        raise ValueError(f"Sheet '{sheet_name}' is empty or has no header row.")

    stations: dict[str, Station] = {}
    for row in records:
        station = Station(
            id=str(row["id"]).strip(),
            name=str(row["name"]).strip(),
            lat=float(row["lat"]),
            lon=float(row["lon"]),
        )
        if station.id in stations:
            raise ValueError(f"Duplicate station id: '{station.id}'")
        stations[station.id] = station

    return stations

# ---------------------------------------------------------------------------
# Stage 2 — Generate edges via routing tool
# ---------------------------------------------------------------------------

class RoutingTool:
    """
    Abstract base for a routing tool that returns minimum travel time and distance
    between two (lat, lon) points.

    Implement a subclass for your specific routing backend
    (e.g. OSRM, OpenRouteService, Google Maps, custom rail timetable API).
    """

    def query(
        self,
        origin: Station,
        destination: Station,
    ) -> tuple[float, int]:
        """
        Returns (distance_km, min_travel_time_min).
        travel_time_min will be rounded up to the nearest 15-min step.
        Raise RoutingError if no route exists.
        """
        raise NotImplementedError


class RoutingError(Exception):
    pass


def generate_edges(
    stations: dict[str, Station],
    routing_tool: RoutingTool,
    connections: list[tuple[str, str]],
) -> list[Edge]:
    """
    Generates edges for all given station pairs.
    """
    existing = set(connections)
    pairs_to_query = list(connections)

    for a, b in connections:
        if (b, a) not in existing:
            pairs_to_query.append((b, a))

    edges: list[Edge] = []
    failed: list[tuple[str, str, str]] = []

    for from_id, to_id in pairs_to_query:
        if from_id not in stations:
            raise ValueError(f"Unknown station id: '{from_id}'")
        if to_id not in stations:
            raise ValueError(f"Unknown station id: '{to_id}'")

        origin = stations[from_id]
        dest   = stations[to_id]

        try:
            distance_km, min_travel_time_min = routing_tool.query(origin, dest)
            edges.append(Edge(
                from_id=from_id,
                to_id=to_id,
                distance_km=round(distance_km, 2),
                min_travel_time_min=min_travel_time_min,
            ))
        except RoutingError as e:
            failed.append((from_id, to_id, str(e)))

    if failed:
        details = "\n".join(f"  {a} -> {b}: {msg}" for a, b, msg in failed)
        raise RoutingError(
            f"{len(failed)} edge(s) could not be routed:\n{details}"
        )

    return edges

def save_edges(edges: list[Edge], path: str) -> None:
    data = [
        {
            "from_id": e.from_id,
            "to_id": e.to_id,
            "distance_km": e.distance_km,
            "travel_time_min": e.travel_time_min,
        }
        for e in edges
    ]
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Edges cached to {path}")


def load_edges(path: str) -> list[Edge]:
    with open(path, "r") as f:
        data = json.load(f)
    return [
        Edge(
            from_id=d["from_id"],
            to_id=d["to_id"],
            distance_km=d["distance_km"],
            min_travel_time_min=d["min_travel_time_min"],
        )
        for d in data
    ]
# ---------------------------------------------------------------------------
# Top-level loader — combines both stages
# ---------------------------------------------------------------------------

def load_network(
    connections: list[tuple[str, str]],
    routing_tool: RoutingTool,
    force_refresh: bool = False,   # set True to re-query routing server
    spreadsheet_id: str = SPREADSHEET_ID,
    sheet_name: str = NODES_SHEET_NAME,
    credentials_path: str = str(CREDENTIALS_PATH),
) -> RailNetwork:
    """
    Full pipeline: load stations from Sheets → load or generate edges
    → build and return a RailNetwork with a populated NetworkX graph.

    Args:
        connections:      List of (from_id, to_id) station pairs to connect.
        routing_tool:     Routing backend — only required when force_refresh=True
                          or no cache exists yet.
        force_refresh:    If True, re-query routing server and overwrite cache.
        spreadsheet_id:   Google Sheets ID (defaults to config).
        sheet_name:       Tab name for nodes (defaults to config).
        credentials_path: Path to Google service account JSON (defaults to config).
    """
    cache_path = Path(EDGES_CACHE_PATH)

    # --- Stage 1: load stations ---
    print("Loading stations from Google Sheets...")
    stations = load_stations_from_sheets(
        spreadsheet_id, sheet_name, credentials_path
    )
    print(f"  Loaded {len(stations)} stations.")

    # --- Stage 2: load or generate edges ---
    if not force_refresh and cache_path.exists():
        print(f"Loading edges from cache ({cache_path})...")
        edges = load_edges(str(cache_path))
        print(f"  Loaded {len(edges)} edges from cache.")
    else:
        if routing_tool is None:
            raise ValueError(
                "routing_tool is required when no edge cache exists or "
                "force_refresh=True. Pass an OpenRailRoutingTool instance."
            )
        print("Generating edges via routing tool...")
        edges = generate_edges(stations, routing_tool, connections)
        save_edges(edges, str(cache_path))
        print(f"  Generated and cached {len(edges)} edges.")

    # --- Stage 3: build graph ---
    network = RailNetwork(stations=stations, edges=edges)
    network.build_graph()
    print(network.summary())
    return network

