"""Geographic Plotly visualizations for flight routes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import networkx as nx
import plotly.graph_objects as go

from airport_coords import (
    get_airport_coords,
    airport_name,
    airport_city,
    format_airport_label,
)
from route_finder import format_duration, MAX_VIZ_NODES, _focused_subgraph


def _hover_airport(code: str, role: str = "", connections: Optional[int] = None) -> str:
    """Build rich hover HTML for an airport marker."""
    name = airport_name(code) or ""
    city = airport_city(code) or ""
    lines = [f"<b>{code}</b>"]
    if name:
        lines.append(name)
    if city and city.lower() not in name.lower():
        lines.append(city)
    if role:
        lines.append(role)
    if connections is not None:
        lines.append(f"Connections: {connections}")
    return "<br>".join(lines)


def _geo_layout(codes) -> Dict[str, Any]:
    lats, lons = [], []
    for c in codes:
        xy = get_airport_coords(c)
        if xy:
            lats.append(xy[0])
            lons.append(xy[1])
    if not lats:
        return dict(
            projection=dict(type="natural earth"),
            center=dict(lat=39.0, lon=-98.0),
            lonaxis=dict(range=[-130, -65], showgrid=False),
            lataxis=dict(range=[24, 50], showgrid=False),
            showland=True,
            landcolor="#1e293b",
            showocean=True,
            oceancolor="#0f172a",
            showlakes=True,
            lakecolor="#0f172a",
            showcountries=True,
            countrycolor="#475569",
            showcoastlines=True,
            coastlinecolor="#64748b",
            bgcolor="#0f172a",
            resolution=50,
        )
    pad_lon = max(8.0, (max(lons) - min(lons)) * 0.4 + 3)
    pad_lat = max(5.0, (max(lats) - min(lats)) * 0.4 + 2)
    return dict(
        projection=dict(type="natural earth"),
        center=dict(lat=sum(lats) / len(lats), lon=sum(lons) / len(lons)),
        lonaxis=dict(range=[min(lons) - pad_lon, max(lons) + pad_lon], showgrid=False),
        lataxis=dict(range=[min(lats) - pad_lat, max(lats) + pad_lat], showgrid=False),
        showland=True,
        landcolor="#1e293b",
        showocean=True,
        oceancolor="#0f172a",
        showlakes=True,
        lakecolor="#0f172a",
        showcountries=True,
        countrycolor="#475569",
        showcoastlines=True,
        coastlinecolor="#64748b",
        bgcolor="#0f172a",
        resolution=50,
    )


def _empty_fig(msg: str = "No route to display") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=msg,
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


def visualize_route_plotly(
    G: nx.DiGraph,
    route: Dict[str, Any],
    title: Optional[str] = None,
) -> go.Figure:
    """Interactive geographic map highlighting one chosen route."""
    airports = route.get("airports") or []
    path_set = set(airports)
    path_edges = list(zip(airports[:-1], airports[1:])) if len(airports) >= 2 else []

    if not airports:
        return _empty_fig()

    path_with_coords = [a for a in airports if get_airport_coords(a)]
    if len(path_with_coords) < 1:
        return _empty_fig("No coordinates for airports on this route")

    sub = _focused_subgraph(G, airports)

    traces: List[Any] = []

    bg_lat, bg_lon = [], []
    for u, v in sub.edges():
        if (u, v) in path_edges:
            continue
        cu, cv = get_airport_coords(u), get_airport_coords(v)
        if not cu or not cv:
            continue
        bg_lat += [cu[0], cv[0], None]
        bg_lon += [cu[1], cv[1], None]
    if bg_lat:
        traces.append(
            go.Scattergeo(
                lat=bg_lat, lon=bg_lon,
                mode="lines",
                line=dict(width=1, color="#334155"),
                opacity=0.4,
                hoverinfo="skip",
                name="Other flights",
            )
        )

    for u, v in path_edges:
        cu, cv = get_airport_coords(u), get_airport_coords(v)
        if not cu or not cv:
            continue
        edge = G[u][v] if G.has_edge(u, v) else {}
        planes = ", ".join(edge.get("planes", [])) or "?"
        dur = edge.get("duration")
        dur_txt = format_duration(dur) if dur is not None else "?"
        u_label = format_airport_label(u)
        v_label = format_airport_label(v)
        traces.append(
            go.Scattergeo(
                lat=[cu[0], cv[0]], lon=[cu[1], cv[1]],
                mode="lines",
                line=dict(width=3.5, color="#38bdf8"),
                hovertemplate=(
                    f"<b>{u} → {v}</b><br>"
                    f"{u_label}<br>"
                    f"{v_label}<br>"
                    f"Aircraft: {planes}<br>"
                    f"Duration: {dur_txt}<extra></extra>"
                ),
                name=f"{u}→{v}",
                showlegend=False,
            )
        )

    def node_trace(nodes, color, size, name):
        lats, lons, texts, hovers = [], [], [], []
        for n in nodes:
            c = get_airport_coords(n)
            if not c:
                continue
            lats.append(c[0])
            lons.append(c[1])
            texts.append(n)
            role = "Origin" if airports and n == airports[0] else (
                "Destination" if airports and n == airports[-1] else (
                    "Via" if n in path_set else "Nearby"
                )
            )
            deg = sub.degree(n) if n in sub else 0
            hovers.append(_hover_airport(n, role=role, connections=deg))
        if not lats:
            return None
        return go.Scattergeo(
            lat=lats, lon=lons,
            mode="markers+text",
            text=texts,
            textposition="top center",
            textfont=dict(color="#f1f5f9", size=11),
            marker=dict(size=size, color=color, line=dict(width=1.5, color="#f1f5f9")),
            hovertemplate="%{hovertext}<extra></extra>",
            hovertext=hovers,
            name=name,
        )

    other = [n for n in sub.nodes if n not in path_set]
    mid = [n for n in airports[1:-1]] if len(airports) > 2 else []

    for nt in (
        node_trace(other, "#475569", 8, "Nearby"),
        node_trace(mid, "#0ea5e9", 12, "Via"),
        node_trace([airports[0]], "#22c55e", 14, "Origin") if airports else None,
        node_trace([airports[-1]], "#f97316", 14, "Destination") if len(airports) >= 2 else None,
    ):
        if nt is not None:
            traces.append(nt)

    display_title = title or f"Route: {route.get('route', '')}"
    if route.get("total_duration") is not None:
        display_title += f"  ·  {format_duration(route['total_duration'])} total"

    fig = go.Figure(data=traces)
    fig.update_layout(
        title=dict(text=display_title, font=dict(color="#f1f5f9", size=16)),
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        geo=_geo_layout(list(sub.nodes) + airports),
        showlegend=True,
        legend=dict(bgcolor="rgba(15,23,42,0.85)", bordercolor="#334155"),
        margin=dict(l=0, r=0, t=60, b=0),
        height=560,
    )
    return fig


def visualize_full_network_plotly(G: nx.DiGraph) -> go.Figure:
    """Interactive geographic overview of the flight network."""
    g = G
    if g.number_of_nodes() > MAX_VIZ_NODES:
        nodes = list(g.nodes)[:MAX_VIZ_NODES]
        g = g.subgraph(nodes).copy()

    traces: List[Any] = []

    edge_lat, edge_lon = [], []
    for u, v in g.edges():
        cu, cv = get_airport_coords(u), get_airport_coords(v)
        if not cu or not cv:
            continue
        edge_lat += [cu[0], cv[0], None]
        edge_lon += [cu[1], cv[1], None]
    if edge_lat:
        traces.append(
            go.Scattergeo(
                lat=edge_lat, lon=edge_lon,
                mode="lines",
                line=dict(width=1.2, color="#38bdf8"),
                opacity=0.55,
                hoverinfo="skip",
                name="Flights",
            )
        )

    lats, lons, texts, hovers = [], [], [], []
    for n in g.nodes():
        c = get_airport_coords(n)
        if not c:
            continue
        lats.append(c[0])
        lons.append(c[1])
        texts.append(n)
        hovers.append(
            _hover_airport(
                n,
                connections=g.out_degree(n) + g.in_degree(n),
            )
        )

    if lats:
        traces.append(
            go.Scattergeo(
                lat=lats, lon=lons,
                mode="markers+text",
                text=texts,
                textposition="top center",
                textfont=dict(color="#f1f5f9", size=11),
                marker=dict(size=12, color="#0ea5e9", line=dict(width=1.5, color="#7dd3fc")),
                hovertemplate="%{hovertext}<extra></extra>",
                hovertext=hovers,
                name="Airports",
            )
        )

    if not traces:
        return _empty_fig("No airport coordinates available")

    fig = go.Figure(data=traces)
    fig.update_layout(
        title=dict(text="Full Flight Network (geographic)", font=dict(color="#f1f5f9", size=16)),
        template="plotly_dark",
        paper_bgcolor="#0f172a",
        geo=_geo_layout(list(g.nodes)),
        showlegend=False,
        margin=dict(l=0, r=0, t=60, b=0),
        height=580,
    )
    return fig
