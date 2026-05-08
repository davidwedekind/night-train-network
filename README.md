# night-train-network

## Prerequisites

This project requires a running OpenRailRouting instance.
See https://github.com/geofabrik/OpenRailRouting for setup instructions.
Configure the URL in `config.py

## How to work with the rounting server?

First run / network changes:
  → start routing server
  → run with force_refresh=True
  → edges saved to files/edges_cache.json
  → stop routing server

Every subsequent run:
  → routing server NOT needed
  → loads from cache instantly