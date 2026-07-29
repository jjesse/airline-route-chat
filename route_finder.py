"""Core flight route finder using NetworkX.

Supports:
- Multi-leg path finding (fewest stops)
- Shortest path by flight duration (when DurationMinutes is present)
- Airport code + common city name resolution
- Static (matplotlib) and interactive (Plotly) visualizations

Security notes:
- All airport tokens are strictly sanitized (A-Z0-9 only, length 3)
- CSV row / airport counts are capped to prevent resource exhaustion
- max_stops is clamped to a safe range
- Visualization subgraphs are size-limited
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------------------------
# Security / resource limits
# ---------------------------------------------------------------------------

MAX_CSV_ROWS = 20_000
MAX_AIRPORTS = 2_000
MAX_STOPS = 5          # hard upper bound for path search
MAX_VIZ_NODES = 80     # prevent huge figures
MAX_QUERY_LEN = 500
MAX_PLANE_TYPE_LEN = 32
MAX_DURATION_MINUTES = 60 * 24 * 2  # 2 days

# ---------------------------------------------------------------------------
# Airport name / city → IATA helpers
# ---------------------------------------------------------------------------

AIRPORT_ALIASES: Dict[str, str] = {
    "DTW": "DTW", "ORD": "ORD", "DEN": "DEN", "LAX": "LAX", "ATL": "ATL",
    "MIA": "MIA", "SEA": "SEA", "SFO": "SFO", "MSP": "MSP",
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


def _sanitize_code(token: str) -> Optional[str]:
    """Return a clean 3-char A-Z0-9 airport code or None."""
    if not token or not isinstance(token, str):
        return None
    cleaned = re.sub(r"[^A-Z0-9]", "", token.upper().strip())
    if len(cleaned) == 3 and re.fullmatch(r"[A-Z0-9]{3}", cleaned):
        return cleaned
    return None


def resolve_airport(token: str) -> Optional[str]:
    """Turn a code or city name into a 3-letter IATA code (sanitized)."""
    if not token or not isinstance(token, str):
        return None
    if len(token) > 80:
        return None

    cleaned = re.sub(r"[^A-Z0-9\s']", "", token.upper().strip())
    cleaned = re.sub(r"\s+", " ", cleaned)

    if cleaned in AIRPORT_ALIASES:
        return _sanitize_code(AIRPORT_ALIASES[cleaned])

    code = _sanitize_code(cleaned)
    if code:
        return code

    for part in cleaned.split():
        if part in AIRPORT_ALIASES:
            return _sanitize_code(AIRPORT_ALIASES[part])
        code = _sanitize_code(part)
        if code:
            return code

    return None


def extract_airports(query: str) -> Tuple[Optional[str], Optional[str]]:
    """Robust extraction of origin and destination from natural language."""
    if not query or not isinstance(query, str):
        return None, None
    if len(query) > MAX_QUERY_LEN:
        return None, None

    q = query.upper().strip()

    m = re.search(
        r"FROM\s+([A-Z0-9\s']+?)\s+TO\s+([A-Z0-9\s']+?)(?:\s|$|[?.!,])",
        q,
    )
    if m:
        o, d = resolve_airport(m.group(1)), resolve_airport(m.group(2))
        if o and d:
            return o, d

    m = re.search(
        r"BETWEEN\s+([A-Z0-9\s']+?)\s+AND\s+([A-Z0-9\s']+?)(?:\s|$|[?.!,])",
        q,
    )
    if m:
        o, d = resolve_airport(m.group(1)), resolve_airport(m.group(2))
        if o and d:
            return o, d

    m = re.search(
        r"\b([A-Z0-9]{3}|[A-Z][A-Z\s']{2,})\s+(?:TO|-)\s+([A-Z0-9]{3}|[A-Z][A-Z\s']{2,})\b",
        q,
    )
    if m:
        o, d = resolve_airport(m.group(1)), resolve_airport(m.group(2))
        if o and d:
            return o, d

    tokens = re.findall(r"[A-Z0-9']{3,}(?:\s+[A-Z0-9']+)*", q)
    resolved = []
    for t in tokens:
        code = resolve_airport(t)
        if code and code not in resolved:
            resolved.append(code)
        if len(resolved) >= 2:
            return resolved[0], resolved[1]

    return None, None


def clamp_max_stops(value: int) -> int:
    """Force max_stops into the safe range [0, MAX_STOPS]."""
    try:
        v = int(value)
    except (TypeError, ValueError):
        return 3
    return max(0, min(v, MAX_STOPS))


# ---------------------------------------------------------------------------
# Graph loading (with resource limits)
# ---------------------------------------------------------------------------

def load_graph(csv_path: str | Path = "flights.csv") -> nx.DiGraph:
    """Load flights CSV into a directed graph."""
    path = Path(csv_path)
    if not path.is_file():
        raise ValueError(f"CSV file not found: {csv_path}")

    size_bytes = path.stat().st_size
    if size_bytes > 50 * 1024 * 1024:
        raise ValueError("CSV file is too large (max 50 MB).")

    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]

    if len(df) > MAX_CSV_ROWS:
        raise ValueError(
            f"CSV has {len(df)} rows; maximum allowed is {MAX_CSV_ROWS}."
        )

    required = {"Originating Airport", "Destination Airport", "Airplane Type"}
    if not required.issubset(set(df.columns)):
        raise ValueError(
            f"CSV must contain columns: {required}. Found: {list(df.columns)}"
        )

    has_duration = "DurationMinutes" in df.columns
    G = nx.DiGraph()

    for _, row in df.iterrows():
        origin = _sanitize_code(str(row["Originating Airport"]))
        dest = _sanitize_code(str(row["Destination Airport"]))
        if not origin or not dest:
            continue

        plane_raw = str(row["Airplane Type"]).strip()
        plane = re.sub(r"[^A-Za-z0-9\- ]", "", plane_raw)[:MAX_PLANE_TYPE_LEN]
        if not plane:
            plane = "UNKNOWN"

        duration = None
        if has_duration:
            try:
                duration = float(row["DurationMinutes"])
                if not (0 < duration <= MAX_DURATION_MINUTES):
                    duration = None
            except (TypeError, ValueError):
                duration = None

        if G.has_edge(origin, dest):
            if plane not in G[origin][dest]["planes"]:
                G[origin][dest]["planes"].append(plane)
            if duration is not None:
                existing = G[origin][dest].get("duration")
                if existing is None or duration < existing:
                    G[origin][dest]["duration"] = duration
        else:
            attrs: Dict[str, Any] = {"planes": [plane]}
            if duration is not None:
                attrs["duration"] = duration
            G.add_edge(origin, dest, **attrs)

        if G.number_of_nodes() > MAX_AIRPORTS:
            raise ValueError(
                f"Too many unique airports (max {MAX_AIRPORTS})."
            )

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
    """Find all simple routes from start to end up to max_stops."""
    start = _sanitize_code(start) or ""
    end = _sanitize_code(end) or ""
    max_stops = clamp_max_stops(max_stops)

    if not start or not end or start not in G or end not in G:
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
    """Dijkstra shortest path using DurationMinutes as weight."""
    start = _sanitize_code(start) or ""
    end = _sanitize_code(end) or ""

    if not start or not end or start not in G or end not in G:
        return None

    def weight(u, v, d):
        return d.get("duration", 1e9)

    try:
        path = nx.shortest_path(G, start, end, weight=weight)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None

    legs = []
    total_dur = 0
    for i in range(len(path) - 1):
        edge = G[path[i]][path[i + 1]]
        dur = edge.get("duration")
        if dur is None:
            return None
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

    try:
        limit = max(1, min(int(limit), 20))
    except (TypeError, ValueError):
        limit = 5

    lines = [f"Found {len(routes)} possible route(s) (showing up to {limit}):\n"]
    for i, r in enumerate(routes[:limit], 1):
        stop_label = "direct" if r["stops"] == 0 else f"{r['stops']} stop(s)"
        dur_str = ""
        if r.get("total_duration") is not None:
            dur_str = f" · total {format_duration(r['total_duration'])}"
        lines.append(f"{i}. {stop_label}: {r['route']}{dur_str}")
        for leg in r["legs"]:
            planes = ", ".join(leg["planes"]) if leg["planes"] else "unknown"
            leg_dur = (
                f" ({format_duration(leg.get('duration'))})"
                if leg.get("duration") is not None else ""
            )
            lines.append(f"      {leg['from']} → {leg['to']}  [{planes}]{leg_dur}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Shared layout helper
# ---------------------------------------------------------------------------

def _focused_subgraph(
    G: nx.DiGraph,
    airports: List[str],
) -> nx.DiGraph:
    """Build a size-capped subgraph around the path airports."""
    nodes_of_interest = set(airports)
    for n in airports:
        if n in G:
            nodes_of_interest.update(list(G.successors(n))[:20])
            nodes_of_interest.update(list(G.predecessors(n))[:20])

    if len(nodes_of_interest) > MAX_VIZ_NODES:
        extras = list(nodes_of_interest - set(airports))
        nodes_of_interest = set(airports) | set(extras[: max(0, MAX_VIZ_NODES - len(airports))])

    return G.subgraph(nodes_of_interest).copy()


def _spring_pos(G: nx.DiGraph, seed: int = 42) -> Dict[str, Tuple[float, float]]:
    return nx.spring_layout(G, seed=seed, k=1.8 / max(1, len(G) ** 0.5))


# ---------------------------------------------------------------------------
# Interactive Plotly visualizations
# ---------------------------------------------------------------------------

def visualize_route_plotly(
    G: nx.DiGraph,
    route: Dict[str, Any],
    title: Optional[str] = None,
) -> go.Figure:
    """Interactive Plotly network highlighting one chosen route.

    - Hover airports for degree / role
    - Hover path edges for duration + aircraft
    - Zoom / pan / export built-in
    """
    airports = route.get("airports") or []
    path_set = set(airports)
    path_edges = list(zip(airports[:-1], airports[1:])) if len(airports) >= 2 else []

    if not airports:
        fig = go.Figure()
        fig.add_annotation(
            text="No route to display",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(color="#f1f5f9", size=16),
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            height=360,
        )
        return fig

    sub = _focused_subgraph(G, airports)
    pos = _spring_pos(sub, seed=42)

    # --- Background edges ---
    bg_x, bg_y = [], []
    for u, v in sub.edges():
        if (u, v) in path_edges:
            continue
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        bg_x += [x0, x1, None]
        bg_y += [y0, y1, None]

    edge_bg = go.Scatter(
        x=bg_x, y=bg_y,
        mode="lines",
        line=dict(width=1, color="#334155"),
        hoverinfo="skip",
        name="Other flights",
        opacity=0.45,
    )

    # --- Path edges (one trace per leg so hover works) ---
    path_traces = []
    for u, v in path_edges:
        if u not in pos or v not in pos:
            continue
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge = G[u][v] if G.has_edge(u, v) else {}
        planes = ", ".join(edge.get("planes", [])) or "?"
        dur = edge.get("duration")
        dur_txt = format_duration(dur) if dur is not None else "?"
        path_traces.append(
            go.Scatter(
                x=[x0, x1], y=[y0, y1],
                mode="lines",
                line=dict(width=4, color="#38bdf8"),
                hovertemplate=(
                    f"<b>{u} → {v}</b><br>"
                    f"Aircraft: {planes}<br>"
                    f"Duration: {dur_txt}<extra></extra>"
                ),
                name=f"{u}→{v}",
                showlegend=False,
            )
        )

    # --- Nodes ---
    def node_trace(nodes, color, size, name, border):
        xs, ys, texts, hovers = [], [], [], []
        for n in nodes:
            if n not in pos:
                continue
            xs.append(pos[n][0])
            ys.append(pos[n][1])
            texts.append(n)
            role = "Origin" if airports and n == airports[0] else (
                "Destination" if airports and n == airports[-1] else (
                    "Via" if n in path_set else "Nearby"
                )
            )
            deg = sub.degree(n) if n in sub else 0
            hovers.append(f"<b>{n}</b><br>{role}<br>Connections: {deg}")
        return go.Scatter(
            x=xs, y=ys,
            mode="markers+text",
            text=texts,
            textposition="top center",
            textfont=dict(color="#f1f5f9", size=11, family="Arial Black"),
            marker=dict(
                size=size,
                color=color,
                line=dict(width=2, color=border),
            ),
            hovertemplate="%{hovertext}<extra></extra>",
            hovertext=hovers,
            name=name,
        )

    other_nodes = [n for n in sub.nodes if n not in path_set]
    mid_path = [n for n in airports[1:-1] if n in sub] if len(airports) > 2 else []

    traces = [edge_bg, *path_traces]
    if other_nodes:
        traces.append(node_trace(other_nodes, "#1e293b", 18, "Nearby", "#475569"))
    if mid_path:
        traces.append(node_trace(mid_path, "#0ea5e9", 24, "Via", "#7dd3fc"))
    if airports and airports[0] in pos:
        traces.append(node_trace([airports[0]], "#22c55e", 28, "Origin", "#86efac"))
    if len(airports) >= 2 and airports[-1] in pos:
        traces.append(node_trace([airports[-1]], "#f97316", 28, "Destination", "#fdba74"))

    display_title = title or f"Route: {route.get('route', '')}"
    if route.get("total_duration") is not None:
        display_title += f"  ·  {format_duration(route['total_duration'])} total"

    fig = go.Figure(data=traces)
    fig.update_layout(
        title=dict(text=display_title, font=dict(color="#f1f5f9", size=16)),
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        showlegend=True,
        legend=dict(bgcolor="rgba(15,23,42,0.8)", bordercolor="#334155"),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=60, b=20),
        height=520,
        hovermode="closest",
    )
    return fig


def visualize_route_timeline_plotly(
    route: Dict[str, Any],
    title: Optional[str] = None,
) -> go.Figure:
    """Horizontal timeline of each leg's duration (interactive bars)."""
    legs = route.get("legs") or []
    if not legs:
        fig = go.Figure()
        fig.add_annotation(
            text="No legs to display",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(color="#f1f5f9", size=14),
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a",
            height=200,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
        )
        return fig

    labels = []
    durations = []
    hover = []
    colors = []
    palette = ["#38bdf8", "#22c55e", "#a78bfa", "#f97316", "#f472b6", "#2dd4bf"]

    for i, leg in enumerate(legs):
        label = f"{leg['from']} → {leg['to']}"
        labels.append(label)
        dur = leg.get("duration")
        durations.append(dur if dur is not None else 0)
        planes = ", ".join(leg.get("planes") or []) or "?"
        hover.append(
            f"<b>{label}</b><br>Aircraft: {planes}<br>Duration: {format_duration(dur)}"
        )
        colors.append(palette[i % len(palette)])

    fig = go.Figure(
        go.Bar(
            x=durations,
            y=labels,
            orientation="h",
            marker=dict(color=colors, line=dict(color="#0f172a", width=1)),
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hover,
            text=[format_duration(d) if d else "?" for d in durations],
            textposition="auto",
            textfont=dict(color="#0f172a", size=12),
        )
    )

    total = route.get("total_duration")
    ttl = title or "Flight legs"
    if total is not None:
        ttl += f"  ·  total {format_duration(total)}"

    fig.update_layout(
        title=dict(text=ttl, font=dict(color="#f1f5f9", size=14)),
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        xaxis=dict(
            title="Minutes",
            color="#94a3b8",
            gridcolor="#1e293b",
        ),
        yaxis=dict(
            autorange="reversed",
            color="#f1f5f9",
        ),
        margin=dict(l=20, r=20, t=50, b=40),
        height=max(220, 80 + 40 * len(legs)),
        showlegend=False,
    )
    return fig


def visualize_full_network_plotly(G: nx.DiGraph) -> go.Figure:
    """Interactive overview of the full (size-capped) flight network."""
    g = G
    if g.number_of_nodes() > MAX_VIZ_NODES:
        nodes = list(g.nodes)[:MAX_VIZ_NODES]
        g = g.subgraph(nodes).copy()

    pos = _spring_pos(g, seed=7)

    edge_x, edge_y = [], []
    for u, v in g.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(width=1.2, color="#334155"),
        hoverinfo="skip",
        name="Flights",
        opacity=0.55,
    )

    node_x, node_y, texts, hovers = [], [], [], []
    for n in g.nodes():
        node_x.append(pos[n][0])
        node_y.append(pos[n][1])
        texts.append(n)
        in_d = g.in_degree(n)
        out_d = g.out_degree(n)
        hovers.append(f"<b>{n}</b><br>Out: {out_d}  In: {in_d}")

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=texts,
        textposition="top center",
        textfont=dict(color="#f1f5f9", size=10),
        marker=dict(
            size=22,
            color="#0ea5e9",
            line=dict(width=2, color="#7dd3fc"),
        ),
        hovertemplate="%{hovertext}<extra></extra>",
        hovertext=hovers,
        name="Airports",
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title=dict(text="Full Flight Network", font=dict(color="#f1f5f9", size=16)),
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        plot_bgcolor="#0f172a",
        showlegend=False,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=60, b=20),
        height=560,
        hovermode="closest",
    )
    return fig


# ---------------------------------------------------------------------------
# Static matplotlib visualizations (kept for CLI / tests / export)
# ---------------------------------------------------------------------------

def visualize_route(
    G: nx.DiGraph,
    route: Dict[str, Any],
    title: Optional[str] = None,
) -> plt.Figure:
    """Create a clean matplotlib figure highlighting one chosen route."""
    airports = route.get("airports") or []
    if not airports:
        fig, ax = plt.subplots(figsize=(6, 3), facecolor="#0f172a")
        ax.set_facecolor("#0f172a")
        ax.text(0.5, 0.5, "No route to display", ha="center", va="center",
                color="#f1f5f9")
        ax.axis("off")
        return fig

    path_edges = list(zip(airports[:-1], airports[1:]))
    sub = _focused_subgraph(G, airports)
    pos = _spring_pos(sub, seed=42)

    fig, ax = plt.subplots(figsize=(11, 7), facecolor="#0f172a")
    ax.set_facecolor("#0f172a")

    nx.draw_networkx_edges(
        sub, pos, ax=ax,
        edge_color="#334155", width=1.0, alpha=0.5,
        arrows=True, arrowsize=12, connectionstyle="arc3,rad=0.05",
    )

    valid_path_edges = [(u, v) for u, v in path_edges if sub.has_edge(u, v)]
    nx.draw_networkx_edges(
        sub, pos, edgelist=valid_path_edges, ax=ax,
        edge_color="#38bdf8", width=3.5, alpha=1.0,
        arrows=True, arrowsize=18, connectionstyle="arc3,rad=0.05",
    )

    path_set = set(airports)
    other_nodes = [n for n in sub.nodes if n not in path_set]

    nx.draw_networkx_nodes(
        sub, pos, nodelist=other_nodes, ax=ax,
        node_color="#1e293b", node_size=900,
        edgecolors="#475569", linewidths=1.5,
    )
    nx.draw_networkx_nodes(
        sub, pos, nodelist=[n for n in airports if n in sub], ax=ax,
        node_color="#0ea5e9", node_size=1400,
        edgecolors="#7dd3fc", linewidths=2.5,
    )

    if airports and airports[0] in sub:
        nx.draw_networkx_nodes(
            sub, pos, nodelist=[airports[0]], ax=ax,
            node_color="#22c55e", node_size=1600,
            edgecolors="#86efac", linewidths=2.5,
        )
    if len(airports) >= 2 and airports[-1] in sub:
        nx.draw_networkx_nodes(
            sub, pos, nodelist=[airports[-1]], ax=ax,
            node_color="#f97316", node_size=1600,
            edgecolors="#fdba74", linewidths=2.5,
        )

    nx.draw_networkx_labels(
        sub, pos, ax=ax,
        font_size=10, font_weight="bold", font_color="#f1f5f9",
    )

    edge_labels = {}
    for u, v in valid_path_edges:
        dur = G[u][v].get("duration")
        if dur is not None:
            edge_labels[(u, v)] = format_duration(dur)
    nx.draw_networkx_edge_labels(
        sub, pos, edge_labels=edge_labels, ax=ax,
        font_color="#7dd3fc", font_size=8,
        bbox=dict(boxstyle="round,pad=0.2", facecolor="#0f172a",
                  edgecolor="none", alpha=0.85),
    )

    display_title = title or f"Route: {route.get('route', '')}"
    if route.get("total_duration") is not None:
        display_title += f"  ·  {format_duration(route['total_duration'])} total"
    ax.set_title(display_title, color="#f1f5f9", fontsize=14, pad=16,
                 fontweight="bold")

    ax.axis("off")
    plt.tight_layout()
    return fig


def visualize_full_network(G: nx.DiGraph) -> plt.Figure:
    """Overview map of the entire flight network (size-capped)."""
    if G.number_of_nodes() > MAX_VIZ_NODES:
        nodes = list(G.nodes)[:MAX_VIZ_NODES]
        G = G.subgraph(nodes).copy()

    pos = _spring_pos(G, seed=7)

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

    ax.set_title("Full Flight Network", color="#f1f5f9", fontsize=15, pad=14,
                 fontweight="bold")
    ax.axis("off")
    plt.tight_layout()
    return fig
