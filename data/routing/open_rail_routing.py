# data/routing/open_rail_routing.py

from __future__ import annotations
import time
import requests
from data.network import RoutingTool, Station, RoutingError
from config import OPEN_RAIL_ROUTING_URL, OPEN_RAIL_ROUTING_PROFILE


class OpenRailRoutingTool(RoutingTool):
    """
    Calls a self-hosted OpenRailRouting instance (GraphHopper-based).

    OpenRailRouting exposes the standard GraphHopper /route GET endpoint:
      GET /route?point=lat,lon&point=lat,lon&profile=<profile>&calc_points=false

    Response JSON structure (relevant fields only):
      {
        "paths": [{
          "distance": 352432.1,   ← metres
          "time":     12453000    ← milliseconds
        }]
      }

    Setup:
      1. Build and run OpenRailRouting locally (see github.com/geofabrik/OpenRailRouting)
      2. Import your OSM rail data (e.g. europe-rail.osm.pbf)
      3. Start the server:  java -jar railway_routing.jar serve config.yml
      4. Default port: 8989  →  base_url = "http://localhost:8989"

    Profile options (defined in your config.yml, typically):
      - "rail"           →  standard rail, any gauge
      - "all_tracks"     →  all track types including tram/subway
      - "gauge_1435"     →  standard gauge only (1435mm, used in most of Europe)
    """

    def __init__(
        self,
        base_url: str = OPEN_RAIL_ROUTING_URL,
        profile: str = OPEN_RAIL_ROUTING_PROFILE,
        timeout: int = 10,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        self.base_url    = base_url.rstrip("/")
        self.profile     = profile
        self.timeout     = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay    = retry_delay
        self._session    = requests.Session()  # reuse TCP connection across calls

    def query(
        self,
        origin: Station,
        destination: Station,
    ) -> tuple[float, int]:
        """
        Query OpenRailRouting for the rail route between two stations.

        Returns:
            (distance_km, min_travel_time_min) — minimum time is raw float minutes)

        Raises:
            RoutingError if no route found or server unreachable.
        """
        params = {
            "point":        [
                f"{origin.lat},{origin.lon}",
                f"{destination.lat},{destination.lon}",
            ],
            "profile":      self.profile,
            "calc_points":  "false",   # skip geometry — we only need time + distance
            "instructions": "false",   # skip turn-by-turn — faster response
        }

        last_error: Exception | None = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                response = self._session.get(
                    f"{self.base_url}/route",
                    params=params,
                    timeout=self.timeout,
                )
                return self._parse_response(response, origin, destination)

            except RoutingError:
                raise   # don't retry routing failures — no route exists
            except requests.RequestException as e:
                last_error = e
                if attempt < self.retry_attempts:
                    time.sleep(self.retry_delay)

        raise RoutingError(
            f"OpenRailRouting unreachable after {self.retry_attempts} attempts "
            f"({origin.id} → {destination.id}): {last_error}"
        )

    def _parse_response(
        self,
        response: requests.Response,
        origin: Station,
        destination: Station,
    ) -> tuple[float, int]:
        """Parse GraphHopper /route response and extract distance + time."""

        # HTTP-level errors (500, 404, etc.)
        if response.status_code != 200:
            try:
                msg = response.json().get("message", response.text)
            except Exception:
                msg = response.text
            raise RoutingError(
                f"OpenRailRouting returned HTTP {response.status_code} "
                f"({origin.id} → {destination.id}): {msg}"
            )

        data = response.json()

        # GraphHopper signals routing failure in the JSON body even on 200
        if "paths" not in data or not data["paths"]:
            msg = data.get("message", "No paths returned")
            raise RoutingError(
                f"No rail route found ({origin.id} → {destination.id}): {msg}"
            )

        path = data["paths"][0]

        distance_m       = path["distance"]            # metres
        min_travel_time_ms   = path["time"]                # milliseconds

        distance_km      = distance_m / 1000
        min_travel_time_min  = min_travel_time_ms / 1000 / 60  # float minutes

        return distance_km, min_travel_time_min