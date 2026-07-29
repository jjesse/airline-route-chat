"""Core flight route finder using NetworkX.

Supports:
- Multi-leg path finding (fewest stops)
- Shortest path by flight duration (when DurationMinutes is present)
- Airport code + common city name resolution
- Visualization of routes as matplotlib figures
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

# ---------------------------------------------------------------------------
# Airport name / city → IATA helpers
# ---------------------------------------------------------------------------

AIRPORT_ALIASES: Dict[str, str] = {
    # Codes map to themselves
    "DTW": "DTW", "ORD": "ORD", "DEN": "DEN", "LAX": "LAX", "ATL": "ATL",
    "MIA": "MIA", "SEA": "SEA", "SFO": "SFO", "MSP": "MSP",
    # Common city / airport names
    "DETROIT": "DTW", "METRO DETROIT": "DTW", "DTW DETROIT": "DTW",
    "CHICAGO": "ORD", "O'HARE": "ORD", "OHARE": "ORD", "CHICAGO O'HARE": "ORD",
    "DENVER": "DEN", "DIA": "DEN",
    "LOS ANGELES": "LAX", "LA": "LAX",
    "ATLANTA": "ATL", "HARTSFIELD": "ATL",
    "MIAMI": "MIA",
    "SEATTLE": "SEA", "SEATAC": "SEA",
    "SAN FRANCISCO": "SFO", "SF": "SFO",
    "MINNEAPOLIS": "MSP", "MINNEAPOLIS-ST PAUL": "MSP", "MSP MINNEAPOLIS": "MSP",
}


def resolve_airport(token: str) -> Optional[str]:
    """Turn a code or city name into a 3-letter IATA code."""
    if not token:
        return None
    cleaned = re.sub(r"[^A-Z0-9\s']", "", token.upper().strip())
    cleaned = re.sub(r"\s+", " ", cleaned)

    if cleaned in AIRPORT_ALIASES:
        return AIRPORT_ALIASES[cleaned]

    # Direct 3-letter code
    if re.fullmatch(r"[A-Z0-9]{3}", cleaned):
        return cleaned

    # Try first word or last word
    parts = cleaned.split()
    for part in parts:
        if part in AIRPORT_ALIASES:
            return AIRPORT_ALIASES[part]
        if re.fullmatch(r"[A-Z0-9]{3}", part):
            return part

    return None


def extract_airports(query: str) -> Tuple[Optional[str], Optional[str]]:
    """Robust extraction of origin and destination from natural language.

    Handles:
      - How do I get from DTW to DEN?
      - from Detroit to Denver
      - ORD to LAX
      - route between Atlanta and Seattle
      - fly DTW-DEN
    """
    q = query.upper().strip()

    # 1. FROM ... TO ...
    m = re.search(
        r"FROM\s+([A-Z0-9\s']+?)\s+TO\s+([A-Z0-9\s']+?)(?:\s|$|[?.!,])",
        q,
    )
    if m:
        o, d = resolve_airport(m.group(1)), resolve_airport(m.group(2))
        if o and d:
            return o, d

    # 2. BETWEEN ... AND ...
    m = re.search(
        r"BETWEEN\s+([A-Z0-9\s']+?)\s+AND\s+([A-Z0-9\s']+?)(?:\s|$|[?.!,])",
        q,
    )
    if m:
        o, d = resolve_airport(m.group(1)), resolve_airport(m.group(2))
        if o and d:
            return o, d

    # 3. XXX TO YYY  or  XXX-YYY
    m = re.search(
        r"\b([A-Z0-9]{3}|[A-Z][A-Z\s']{2,})\s+(?:TO|-)\s+([A-Z0-9]{3}|[A-Z][A-Z\s']{2,})\b",
        q,
    )
    if m:
        o, d = resolve_airport(m.group(1)), resolve_airport(m.group(2))
        if o and d:
            return o, d

    # 4. Fallback: find any two resolvable tokens
    tokens = re.findall(r"[A-Z0-9']{3,}(?:\s+[A-Z0-9']+)*", q)
    resolved = []
    for t in tokens:
        code = resolve_airport(t)
        if code and code not in resolved:
            resolved.append(code)
        if len(resolved) >= 2:
            return resolved[0], resolved[1]

    return None, None


# ---------------------------------------------------------------------------
# Graph loading
# ---------------------------------------------------------------------------

def load_graph(csv_path: str | Path = "flights.csv") -> nx.DiGraph:
    """Load flights CSV into a directed graph.

    Required columns: Originating Airport, Destination Airport, Airplane Type
    Optional column: DurationMinutes (used for weighted shortest path)
    """
    df = pd.read_csv(csv_path)
    df.columns = [c.strip() for c in df.columns]

    required = {"Originating Airport", "Destination Airport", "Airplane Type"}
    if not required.issubset(set(df.columns)):
        raise ValueError(
            f"CSV must contain columns: {required}. Found: {list(df.columns)}"
        )

    has_duration = "DurationMinutes" in df.columns

    G = nx.DiGraph()

    for _, row in df.iterrows():
        origin = str(row["Originating Airport"]).strip().upper()
        dest = str(row["Destination Airport"]).strip().upper()
        plane = str(row["Airplane Type"]).strip()

        if not origin or not dest:
            continue

        duration = None
        if has_duration:
            try:
                duration = float(row["DurationMinutes"])
            except (TypeError, ValueError):
                duration = None

        if G.has_edge(origin, dest):
            if plane not in G[origin][dest]["planes"]:
                G[origin][dest]["planes"].append(plane)
            # Keep the shortest duration if multiple entries exist
            if duration is not None:
                existing = G[origin][dest].get("duration")
                if existing is None or duration < existing:
                    G[origin][dest]["duration"] = duration
        else:
            attrs: Dict[str, Any] = {"planes": [plane]}
            if duration is not None:
                attrs["duration"] = duration
            G.add_edge(origin, dest, **attrs)

    return G


# ---------------------------------------------------------------------------
# Route finding
# ---------------------------------------------------------------------------

def find_routes(
    G: nx.DiGraph,
    start: str,
    end: str,
    max_stops: int = 3,
) -> List[Dict[str, Any]]:
    """Find all simple routes from start to end up to max_stops.

    Sorted by fewest stops, then by total duration (if available).
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
            "total_duration": 0,
        }]

    paths = list(nx.all_simple_paths(G, start, end, cutoff=max_stops + 1))

    results = []
    for path in paths:
        legs = []
        total_dur = 0
        has_all_durs = True
        for i in range(len(path) - 1):
            edge = G[path[i]][path[i + 1]]
            planes = edge.get("planes", [])
            dur = edge.get("duration")
            if dur is None:
                has_all_durs = False
            else:
                total_dur += dur
            legs.append({
                "from": path[i],
                "to": path[i + 1],
                "planes": planes,
                "duration": dur,
            })

        results.append({
            "stops": len(path) - 2,
            "route": " → ".join(path),
            "airports": path,
            "legs": legs,
            "total_duration": total_dur if has_all_durs else None,
        })

    # Prefer fewer stops, then shorter total duration, then lexical route
    results.sort(
        key=lambda r: (
            r["stops"],
            r["total_duration"] if r["total_duration"] is not None else 99999,
            r["route"],
        )
    )
    return results


def find_shortest_by_time(
    G: nx.DiGraph,
    start: str,
    end: str,
) -> Optional[Dict[str, Any]]:
    """Dijkstra shortest path using DurationMinutes as weight.

    Returns a single route dict or None if unreachable / no durations.
    """
    start = start.strip().upper()
    end = end.strip().upper()

    if start not in G or end not in G:
        return None

    # Only use edges that have duration
    def weight(u, v, d):
        return d.get("duration", 1e9)

    try:
        path = nx.shortest_path(G, start, end, weight=weight)
    except nx.NetworkXNoPath:
        return None

    legs = []
    total_dur = 0
    for i in range(len(path) - 1):
        edge = G[path[i]][path[i + 1]]
        dur = edge.get("duration")
        if dur is None:
            return None  # incomplete data
        total_dur += dur
        legs.append({
            "from": path[i],
            "to": path[i + 1],
            "planes": edge.get("planes", []),
            "duration": dur,
        })

    return {
        "stops": len(path) - 2,
        "route": " → ".join(path),
        "airports": path,
        "legs": legs,
        "total_duration": total_dur,
    }


def format_duration(minutes: Optional[float]) -> str:
    if minutes is None:
        return "?"
    minutes = int(round(minutes))
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{m}m"


def format_routes(routes: List[Dict[str, Any]], limit: int = 5) -> str:
    """Pretty-print a list of routes for chat output."""
    if not routes:
        return "No routes found."

    lines = [f"Found {len(routes)} possible route(s) (showing up to {limit}):\n"]
    for i, r in enumerate(routes[:limit], 1):
        stop_label = "direct" if r["stops"] == 0 else f"{r['stops']} stop(s)"
        dur_str = ""
        if r.get("total_duration") is not None:
            dur_str = f" · total {format_duration(r['total_duration'])}"
        lines.append(f"{i}. {stop_label}: {r['route']}{dur_str}")
        for leg in r["legs"]:
            planes = ", ".join(leg["planes"]) if leg["planes"] else "unknown"
            leg_dur = f" ({format_duration(leg.get('duration'))})" if leg.get("duration") is not None else ""
            lines.append(f"      {leg['from']} → {leg['to']}  [{planes}]{leg_dur}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def visualize_route(
    G: nx.DiGraph,
    route: Dict[str, Any],
    title: Optional[str] = None,
) -> plt.Figure:
    """Create a clean matplotlib figure highlighting one chosen route.

    Shows the full relevant subgraph (all neighbors of the path airports)
    with the chosen path drawn in a strong accent color.
    """
    airports = route["airports"]
    path_edges = list(zip(airports[:-1], airports[1:]))

    # Build a focused subgraph: the path + immediate neighbors
    nodes_of_interest = set(airports)
    for n in airports:
        nodes_of_interest.update(G.successors(n))
        nodes_of_interest.update(G.predecessors(n))
    sub = G.subgraph(nodes_of_interest).copy()

    # Layout – spring with a little help from path order
    pos = nx.spring_layout(sub, seed=42, k=1.8 / max(1, len(sub) ** 0.5))

    fig, ax = plt.subplots(figsize=(11, 7), facecolor="#0f172a")
    ax.set_facecolor("#0f172a")

    # All edges (faint)
    nx.draw_networkx_edges(
        sub, pos, ax=ax,
        edge_color="#334155", width=1.0, alpha=0.5,
        arrows=True, arrowsize=12, connectionstyle="arc3,rad=0.05",
    )

    # Highlighted path edges
    nx.draw_networkx_edges(
        sub, pos, edgelist=path_edges, ax=ax,
        edge_color="#38bdf8", width=3.5, alpha=1.0,
        arrows=True, arrowsize=18, connectionstyle="arc3,rad=0.05",
    )

    # Nodes
    path_set = set(airports)
    other_nodes = [n for n in sub.nodes if n not in path_set]

    nx.draw_networkx_nodes(
        sub, pos, nodelist=other_nodes, ax=ax,
        node_color="#1e293b", node_size=900,
        edgecolors="#475569", linewidths=1.5,
    )
    nx.draw_networkx_nodes(
        sub, pos, nodelist=airports, ax=ax,
        node_color="#0ea5e9", node_size=1400,
        edgecolors="#7dd3fc", linewidths=2.5,
    )

    # Start / end special colors
    if len(airports) >= 1:
        nx.draw_networkx_nodes(
            sub, pos, nodelist=[airports[0]], ax=ax,
            node_color="#22c55e", node_size=1600,
            edgecolors="#86efac", linewidths=2.5,
        )
    if len(airports) >= 2:
        nx.draw_networkx_nodes(
            sub, pos, nodelist=[airports[-1]], ax=ax,
            node_color="#f97316", node_size=1600,
            edgecolors="#fdba74", linewidths=2.5,
        )

    # Labels
    nx.draw_networkx_labels(
        sub, pos, ax=ax,
        font_size=10, font_weight="bold", font_color="#f1f5f9",
    )

    # Edge duration labels on the chosen path
    edge_labels = {}
    for u, v in path_edges:
        dur = G[u][v].get("duration")
        if dur is not None:
            edge_labels[(u, v)] = format_duration(dur)
    nx.draw_networkx_edge_labels(
        sub, pos, edge_labels=edge_labels, ax=ax,
        font_color="#7dd3fc", font_size=8,
        bbox=dict(boxstyle="round,pad=0.2", facecolor="#0f172a", edgecolor="none", alpha=0.85),
    )

    display_title = title or f"Route: {route['route']}"
    if route.get("total_duration") is not None:
        display_title += f"  ·  {format_duration(route['total_duration'])} total"
    ax.set_title(display_title, color="#f1f5f9", fontsize=14, pad=16, fontweight="bold")

    ax.axis("off")
    plt.tight_layout()
    return fig


def visualize_full_network(G: nx.DiGraph) -> plt.Figure:
    """Overview map of the entire flight network."""
    pos = nx.spring_layout(G, seed=7, k=2.2 / max(1, len(G) ** 0.5))

    fig, ax = plt.subplots(figsize=(12, 8), facecolor="#0f172a")
    ax.set_facecolor("#0f172a")

    nx.draw_networkx_edges(
        G, pos, ax=ax,
        edge_color="#334155", width=1.2, alpha=0.6,
        arrows=True, arrowsize=10, connectionstyle="arc3,rad=0.06",
    )
    nx.draw_networkx_nodes(
        G, pos, ax=ax,
        node_color="#0ea5e9", node_size=1100,
        edgecolors="#7dd3fc", linewidths=2,
    )
    nx.draw_networkx_labels(
        G, pos, ax=ax,
        font_size=9, font_weight="bold", font_color="#f1f5f9",
    )

    ax.set_title("Full Flight Network", color="#f1f5f9", fontsize=15, pad=14, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    return fig
