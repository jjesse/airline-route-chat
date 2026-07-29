"""Streamlit chat + interactive visualization UI for the airline route finder."""

import streamlit as st
import pandas as pd

from route_finder import (
    load_graph,
    find_routes,
    find_shortest_by_time,
    format_duration,
    extract_airports,
    visualize_route_plotly,
    visualize_route_timeline_plotly,
    visualize_full_network_plotly,
    clamp_max_stops,
    MAX_STOPS,
)

st.set_page_config(
    page_title="Airline Route Chat",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("✈️ Airline Route Chat")
st.caption(
    "Ask for routes in plain English. Interactive maps highlight the path you choose. "
    "Data source: flights.csv only."
)

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_resource
def get_graph():
    return load_graph("flights.csv")

try:
    G = get_graph()
except Exception as e:
    st.error(f"Could not load flights.csv: {e}")
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Controls")
    st.success(f"{G.number_of_nodes()} airports  ·  {G.number_of_edges()} flights")

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
    if st.button("Show full network map", use_container_width=True):
        st.session_state["show_full_network"] = True

    st.divider()
    st.markdown("**Tips**")
    st.markdown(
        """
        - `How do I get from Detroit to Denver?`
        - `ORD to LAX`
        - `fastest Atlanta to Seattle`
        - City names and IATA codes both work
        """
    )
    st.caption("Hover nodes & edges for details. Zoom/pan the maps.")

# ---------------------------------------------------------------------------
# Full network view (optional)
# ---------------------------------------------------------------------------

if st.session_state.get("show_full_network"):
    with st.expander("Full flight network (interactive)", expanded=True):
        fig = visualize_full_network_plotly(G)
        st.plotly_chart(fig, use_container_width=True, config={
            "displayModeBar": True,
            "scrollZoom": True,
        })
        if st.button("Hide network map"):
            st.session_state["show_full_network"] = False
            st.rerun()

# ---------------------------------------------------------------------------
# Chat history
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Hi! Ask me something like:\n"
                "- How do I get from Detroit to Denver?\n"
                "- ORD to LAX\n"
                "- fastest from ATL to SEA\n\n"
                "Pick a route below to explore an **interactive** map and timeline."
            ),
            "routes": None,
            "origin": None,
            "dest": None,
        }
    ]

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
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

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
                "🗺️ Route map",
                "⏱️ Leg timeline",
                "📋 Leg details",
            ])

            with tab_map:
                fig_map = visualize_route_plotly(
                    G,
                    chosen,
                    title=f"{origin} → {dest}",
                )
                st.plotly_chart(fig_map, use_container_width=True, config={
                    "displayModeBar": True,
                    "scrollZoom": True,
                })
                st.caption(
                    "Green = origin · Orange = destination · Cyan edges = your path. "
                    "Hover for aircraft & duration."
                )

            with tab_time:
                fig_time = visualize_route_timeline_plotly(
                    chosen,
                    title=f"{origin} → {dest}",
                )
                st.plotly_chart(fig_time, use_container_width=True)

            with tab_legs:
                for leg in chosen["legs"]:
                    planes = ", ".join(leg["planes"]) if leg["planes"] else "?"
                    dur = format_duration(leg.get("duration"))
                    st.markdown(
                        f"- **{leg['from']} → {leg['to']}**  ·  {planes}  ·  {dur}"
                    )

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------

if prompt := st.chat_input("Ask for a route (e.g. Detroit to Denver or DTW to DEN)"):
    if len(prompt) > 500:
        st.warning("Query is too long. Please keep it under 500 characters.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    origin, dest = extract_airports(prompt)

    if not origin or not dest:
        reply = (
            "I need two airports (IATA code or city name).\n\n"
            "Try: **How do I get from Detroit to Denver?**  or  **DTW to LAX**"
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

    st.rerun()
