"""Core flight route finder using NetworkX."""

from __future__ import annotations

import pandas as pd
import networkx as nx
from pathlib import Path
from typing import List, Dict, Any


def load_graph(csv_path: str | Path = "flights.csv") -> nx.DiGraph:
    """Load flights CSV into a directed graph.

    Expected columns:
        Originating Airport, Destination Airport, Airplane Type
    """
    df = pd.read_csv(csv_path)

    # Normalize column names just in case
    df.columns = [c.strip() for c in df.columns]

    required = {"Originating Airport", "Destination Airport", "Airplane Type"}
    if not required.issubset(set(df.columns)):
        raise ValueError(
            f"CSV must contain columns: {required}. Found: {list(df.columns)}"
        )

    G = nx.DiGraph()

    for _, row in df.iterrows():
        origin = str(row["Originating Airport"]).strip().upper()
        dest = str(row["Destination Airport"]).strip().upper()
        plane = str(row["Airplane Type"]).strip()

        if not origin or not dest:
            continue

        if G.has_edge(origin, dest):
            if plane not in G[origin][dest]["planes"]:
                G[origin][dest]["planes"].append(plane)
        else:
            G.add_edge(origin, dest, planes=[plane])

    return G


def find_routes(
    G: nx.DiGraph,
    start: str,
    end: str,
    max_stops: int = 3,
) -> List[Dict[str, Any]]:
    """Find all simple routes from start to end up to max_stops.

    Returns a list of dicts sorted by fewest stops first:
    {
        "stops": int,
        "route": "DTW → ORD → DEN",
        "airports": ["DTW", "ORD", "DEN"],
        "legs": [
            {"from": "DTW", "to": "ORD", "planes": ["A320"]},
            ...
        ]
    }
    """
    start = start.strip().upper()
    end = end.strip().upper()

    if start not in G or end not in G:
        return []

    if start == end:
        return [{
            "stops": 0,
            "route": start,
            "airports": [start],
            "legs": [],
        }]

    # cutoff is number of nodes in the path (stops + 1 hops + 1)
    paths = list(nx.all_simple_paths(G, start, end, cutoff=max_stops + 1))

    results = []
    for path in paths:
        legs = []
        for i in range(len(path) - 1):
            planes = G[path[i]][path[i + 1]].get("planes", [])
            legs.append({
                "from": path[i],
                "to": path[i + 1],
                "planes": planes,
            })

        results.append({
            "stops": len(path) - 2,  # 0 = direct
            "route": " → ".join(path),
            "airports": path,
            "legs": legs,
        })

    # Prefer fewer stops, then shorter string representation
    results.sort(key=lambda r: (r["stops"], r["route"]))
    return results


def format_routes(routes: List[Dict[str, Any]], limit: int = 5) -> str:
    """Pretty-print a list of routes for chat output."""
    if not routes:
        return "No routes found."

    lines = [f"Found {len(routes)} possible route(s) (showing up to {limit}):\n"]
    for i, r in enumerate(routes[:limit], 1):
        stop_label = "direct" if r["stops"] == 0 else f"{r['stops']} stop(s)"
        lines.append(f"{i}. {stop_label}: {r['route']}")
        for leg in r["legs"]:
            planes = ", ".join(leg["planes"]) if leg["planes"] else "unknown"
            lines.append(f"      {leg['from']} → {leg['to']}  [{planes}]")

    return "\n".join(lines)
