"""Simple Streamlit chat UI for the airline route finder."""

import streamlit as st
from route_finder import load_graph, find_routes, format_routes

st.set_page_config(page_title="Airline Route Chat", page_icon="✈️", layout="centered")

st.title("✈️ Airline Route Chat")
st.caption("Ask for routes between airports using only the flights.csv data source.")

# Load graph once and cache it
@st.cache_resource
def get_graph():
    return load_graph("flights.csv")

try:
    G = get_graph()
    st.sidebar.success(f"Loaded {G.number_of_nodes()} airports · {G.number_of_edges()} flights")
except Exception as e:
    st.error(f"Could not load flights.csv: {e}")
    st.stop()

# Sidebar controls
max_stops = st.sidebar.slider("Max stops", min_value=0, max_value=4, value=3)
show_limit = st.sidebar.slider("Max routes to show", min_value=1, max_value=10, value=5)

# Chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hi! Ask me something like:\n- How do I get from DTW to DEN?\n- ORD to LAX\n- Is there a route between ATL and SEA?",
        }
    ]

# Display history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask for a route (e.g. DTW to DEN)"):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Very simple extraction
    import re
    q = prompt.upper()
    origin = dest = None

    match = re.search(r"FROM\s+([A-Z0-9]{3})\s+TO\s+([A-Z0-9]{3})", q)
    if match:
        origin, dest = match.group(1), match.group(2)
    else:
        match = re.search(r"\b([A-Z0-9]{3})\s+TO\s+([A-Z0-9]{3})\b", q)
        if match:
            origin, dest = match.group(1), match.group(2)
        else:
            match = re.search(r"BETWEEN\s+([A-Z0-9]{3})\s+AND\s+([A-Z0-9]{3})", q)
            if match:
                origin, dest = match.group(1), match.group(2)

    if not origin or not dest:
        reply = (
            "I need two 3-letter airport codes.\n"
            "Try: **How do I get from DTW to DEN?** or just **DTW to DEN**"
        )
    else:
        routes = find_routes(G, origin, dest, max_stops=max_stops)
        if not routes:
            reply = f"No route found from **{origin}** to **{dest}** within {max_stops} stops."
        else:
            reply = format_routes(routes, limit=show_limit)

    st.session_state.messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.markdown(reply)
