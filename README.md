# Airline Route Chat

A simple chat-style app that finds direct and multi-leg flight routes from a CSV file of flights.

**Data source**: A CSV with columns  
`Originating Airport`, `Destination Airport`, `Airplane Type`

The app builds a directed graph and uses path finding so you can ask things like:

> How do I get from DTW to DEN?

even when there is no direct flight.

## Quick Start

```bash
# Clone
git clone https://github.com/jjesse/airline-route-chat.git
cd airline-route-chat

# Install dependencies
pip install -r requirements.txt

# Run the CLI chat
python app.py

# Or run the Streamlit web UI
streamlit run streamlit_app.py
```

## CSV Format

Place your flight data in `flights.csv` (a sample is included):

```csv
Originating Airport,Destination Airport,Airplane Type
DTW,ORD,A320
ORD,DEN,B737
DTW,DEN,A321
...
```

Airport codes are normalized to uppercase automatically.

## How it works

1. Loads the CSV into a NetworkX directed graph.
2. Each row becomes a directed edge (origin → destination) with airplane type(s) stored on the edge.
3. Uses `nx.all_simple_paths` to find all routes up to a configurable number of stops.
4. Returns results sorted by fewest stops first.

## Files

| File | Purpose |
|------|---------|
| `app.py` | CLI chat interface |
| `streamlit_app.py` | Simple web chat UI |
| `route_finder.py` | Core graph + path finding logic |
| `flights.csv` | Sample flight data (replace with your own) |
| `requirements.txt` | Python dependencies |

## Next ideas

- Add flight times / distances as edge weights and find shortest by time
- Better natural-language parsing
- Export itineraries
- Support for multiple CSVs or live data sources
