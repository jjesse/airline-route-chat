"""Streamlit chat + interactive geographic visualization UI."""

from __future__ import annotations

import hashlib
import html
import os
import tempfile
import uuid
from pathlib import Path

import pandas as pd
import streamlit as st

from route_finder import (
    load_graph,
    find_routes,
    find_shortest_by_time,
    format_duration,
    extract_airports,
    visualize_route_timeline_plotly,
    clamp_max_stops,
    MAX_STOPS,
    MAX_QUERY_LEN,
)
from geo_viz import visualize_route_plotly, visualize_full_network_plotly
from rate_limit import check_query_allowed, check_upload_allowed

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_SESSION_MESSAGES = 40

st.set_page_config(
    page_title="Airline Route Chat",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("✈️ Airline Route Chat")
st.caption(
    "Ask for routes in plain English. Geographic maps use real airport coordinates "
    "looked up from ICAO/IATA codes. Data source: your flights CSV only. "
    "Local/demo tool — do not expose publicly without auth."
)


def _session_id() -> str:
    if "_rate_session_id" not in st.session_state:
        st.session_state["_rate_session_id"] = uuid.uuid4().hex
    return st.session_state["_rate_session_id"]


@st.cache_resource
def get_graph(cache_key: str, csv_bytes: bytes | None = None):
    """Load graph from default flights.csv or from uploaded bytes."""
    if csv_bytes is None:
        return load_graph("flights.csv"), "flights.csv (sample)"

    if len(csv_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError(
            f"Upload too large ({len(csv_bytes):,} bytes). "
            f"Maximum is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
        )

    fd, tmp_name = tempfile.mkstemp(suffix=".csv", prefix="airline_route_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(csv_bytes)
        G = load_graph(tmp_name)
        return G, f"uploaded ({len(csv_bytes):,} bytes)"
    finally:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass


def _trim_messages() -> None:
    msgs = st.session_state.get("messages") or []
    if len(msgs) > MAX_SESSION_MESSAGES:
        st.session_state.messages = msgs[-MAX_SESSION_MESSAGES:]


with st.sidebar:
    st.header("Data source")
    uploaded = st.file_uploader(
        "Upload your game flights CSV",
        type=["csv"],
        help=(
            "Game export columns: Org Airport Code, Dest Airport Code, Aircraft, "
            "Distance (mi). Max 50 MB. Extra columns ignored. Cargo aircraft excluded."
        ),
    )

    if uploaded is not None:
        raw = uploaded.getvalue()
        if len(raw) > MAX_UPLOAD_BYTES:
            st.error(
                f"File is too large ({len(raw) / (1024 * 1024):.1f} MB). "
                f"Maximum is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
            )
            st.stop()

        cache_key = hashlib.sha256(raw).hexdigest()[:16]
        prev = st.session_state.get("_csv_key")
        if prev != cache_key:
            # Rate-limit only when accepting a *new* file
            up = check_upload_allowed(_session_id())
            if not up.allowed:
                st.error(up.message)
                st.stop()

            st.session_state["_csv_key"] = cache_key
            st.session_state["messages"] = []
            st.session_state["show_full_network"] = False
            get_graph.clear()
        try:
            G, source_label = get_graph(cache_key, raw)
        except Exception as e:
            st.error(f"Could not load uploaded CSV: {type(e).__name__}: {e}")
            st.stop()
        safe_name = html.escape(Path(str(uploaded.name)).name[:120])
        st.caption(f"Using **{safe_name}**")
    else:
        try:
            G, source_label = get_graph("default", None)
        except Exception as e:
            st.error(f"Could not load flights.csv: {type(e).__name__}: {e}")
            st.stop()
        st.caption("Using sample `flights.csv` — upload yours above.")

    st.success(f"{G.number_of_nodes()} airports  ·  {G.number_of_edges()} flights")
    st.caption(f"Source: {html.escape(str(source_label)[:80])}")

    st.divider()
    st.header("Controls")

    max_stops = st.slider(
        "Max stops (for multi-leg search)",
        min_value=0,
        max_value=MAX_STOPS,
        value=3,
    )
    max_stops = clamp_max_stops(max_stops)

    show_limit = st.slider("Max routes to list", 1, 10, 5)
    prefer_fastest = st.toggle("Prefer fastest by flight time", value=False)

    st.divider()
    if st.button("Show full network map", width="stretch"):
        st.session_state["show_full_network"] = True

    st.divider()
    st.markdown("**Tips**")
    st.markdown(
        """
        - `How do I get from Detroit to Denver?`
        - `KORD to KLAX`
        - `fastest Atlanta to Seattle`
        - City names and ICAO/IATA codes both work
        - Cargo freighters are excluded from routes
        """
    )
    st.caption(
        "Maps look up lat/lon and airport names offline. "
        "Hover markers for full airport names."
    )

if st.session_state.get("show_full_network"):
    with st.expander("Full flight network (geographic)", expanded=True):
        fig = visualize_full_network_plotly(G)
        st.plotly_chart(fig, width="stretch", config={
            "displayModeBar": True,
            "scrollZoom": True,
        })
        if st.button("Hide network map"):
            st.session_state["show_full_network"] = False
            st.rerun()

if "messages" not in st.session_state or not st.session_state.messages:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hi! Ask me something like:\n"
                "- How do I get from Detroit to Denver?\n"
                "- KORD to KLAX\n"
                "- fastest from ATL to SEA\n\n"
                "Upload **your game CSV** in the sidebar to replace the sample data. "
                "Pick a route to see it on a **geographic map** and timeline."
            ),
            "routes": None,
            "origin": None,
            "dest": None,
        }
    ]

_trim_messages()

for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg.get("routes"):
            routes = msg["routes"]
            origin = msg.get("origin")
            dest = msg.get("dest")

            rows = []
            for i, r in enumerate(routes[:show_limit], 1):
                rows.append({
                    "#": i,
                    "Route": r["route"],
                    "Stops": r["stops"],
                    "Total time": format_duration(r.get("total_duration")),
                })
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

            options = [
                f"{i}. {r['route']}  ({format_duration(r.get('total_duration'))})"
                for i, r in enumerate(routes[:show_limit], 1)
            ]
            choice = st.selectbox(
                "Visualize a route",
                options=options,
                key=f"viz_select_{idx}",
                index=0,
            )
            chosen_idx = options.index(choice)
            chosen = routes[chosen_idx]

            tab_map, tab_time, tab_legs = st.tabs([
                "🗺️ Geographic map",
                "⏱️ Leg timeline",
                "📋 Leg details",
            ])

            with tab_map:
                fig_map = visualize_route_plotly(
                    G,
                    chosen,
                    title=f"{origin} → {dest}",
                )
                st.plotly_chart(fig_map, width="stretch", config={
                    "displayModeBar": True,
                    "scrollZoom": True,
                })
                st.caption(
                    "Green = origin · Orange = destination · Cyan = your path. "
                    "Hover for airport names, aircraft & duration."
                )

            with tab_time:
                fig_time = visualize_route_timeline_plotly(
                    chosen,
                    title=f"{origin} → {dest}",
                )
                st.plotly_chart(fig_time, width="stretch")

            with tab_legs:
                for leg in chosen["legs"]:
                    planes = ", ".join(leg["planes"]) if leg["planes"] else "?"
                    dur = format_duration(leg.get("duration"))
                    st.markdown(
                        f"- **{leg['from']} → {leg['to']}**  ·  {planes}  ·  {dur}"
                    )

if prompt := st.chat_input("Ask for a route (e.g. Detroit to Denver or KDTW to KDEN)"):
    if len(prompt) > MAX_QUERY_LEN:
        st.warning(f"Query is too long. Please keep it under {MAX_QUERY_LEN} characters.")
        st.stop()

    rl = check_query_allowed(_session_id())
    if not rl.allowed:
        st.warning(rl.message)
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    origin, dest = extract_airports(prompt)

    if not origin or not dest:
        reply = (
            "I need two airports (ICAO/IATA code or city name).\n\n"
            "Try: **How do I get from Detroit to Denver?**  or  **KDTW to KLAX**"
        )
        routes = None
    else:
        want_fastest = prefer_fastest or any(
            w in prompt.lower()
            for w in ("fastest", "shortest", "quickest", "least time", "by time")
        )

        if want_fastest:
            best = find_shortest_by_time(G, origin, dest)
            routes = [best] if best else []
            if not routes:
                reply = f"No timed route found from **{origin}** to **{dest}**."
            else:
                reply = f"Fastest route by flight time from **{origin}** to **{dest}**:"
        else:
            routes = find_routes(G, origin, dest, max_stops=max_stops)
            if not routes:
                reply = (
                    f"No route found from **{origin}** to **{dest}** "
                    f"within {max_stops} stops."
                )
            else:
                reply = (
                    f"Found **{len(routes)}** route(s) from **{origin}** to **{dest}** "
                    f"(showing up to {show_limit}). Pick one below to explore."
                )

    st.session_state.messages.append({
        "role": "assistant",
        "content": reply,
        "routes": routes,
        "origin": origin,
        "dest": dest,
    })
    _trim_messages()
    st.rerun()
