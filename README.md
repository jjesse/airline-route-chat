# Airline Route Chat

A chat-style app that finds **direct and multi-leg flight routes** from a single CSV file of flights.  
Ask questions in plain English (“How do I get from Detroit to Denver?”) and get ranked itineraries plus **geographic route maps**.

**Flight data comes only from your CSV** — no external flight APIs.  
**Airport coordinates** are looked up automatically from IATA codes via the offline [`airportsdata`](https://pypi.org/project/airportsdata/) package.

---

## Features

- Multi-leg path finding (fewest stops)
- **Shortest path by flight time** when `DurationMinutes` is present
- Natural language + city names (“Detroit”, “Chicago”, “LA” …) as well as IATA codes
- **Upload your own game/simulation CSV** in the Streamlit sidebar
- **Interactive Plotly visualizations**
  - **Geographic route map** (real lat/lon from IATA lookup, coastlines, zoom/pan)
  - Leg duration timeline
  - Full network overview on a map
- CLI and Streamlit web UI
- Docker support (runs as non-root)
- Input sanitization and resource limits (see [SECURITY.md](SECURITY.md))
- Automated test suite (pytest) + GitHub Actions CI

---

## Quick Start

### Local

```bash
git clone https://github.com/jjesse/airline-route-chat.git
cd airline-route-chat

pip install -r requirements.txt

# CLI chat (uses flights.csv in the repo)
python app.py

# Web UI with geographic maps + CSV upload (recommended)
streamlit run streamlit_app.py
```

In the sidebar, upload your airline-sim export to replace the sample network.

### Docker

```bash
docker build -t airline-route-chat .
docker run -p 8501:8501 airline-route-chat
```

Then open http://localhost:8501

---

## Running tests

```bash
pip install -r requirements.txt
pytest
```

CI runs the same suite on every push.

---

## CSV Format

Required columns:

| Column                | Description        |
|-----------------------|--------------------|
| Originating Airport   | 3-letter IATA code |
| Destination Airport   | 3-letter IATA code |
| Airplane Type         | e.g. A320, B737    |

Optional:

| Column            | Description                                      |
|-------------------|--------------------------------------------------|
| DurationMinutes   | Block time in minutes (enables fastest-by-time)  |

Example:

```csv
Originating Airport,Destination Airport,Airplane Type,DurationMinutes
DTW,ORD,A320,70
ORD,DEN,B737,145
DTW,DEN,A321,175
```

Airport codes are sanitized to 3-letter uppercase.  
**You do not need to supply latitude/longitude** — any standard IATA code is resolved offline (e.g. DTW ≈ 42.21° N, 83.35° W). Optional overrides live in `LOCAL_OVERRIDES` inside `airport_coords.py`.

**Limits** (safety): max ~20k rows, ~2k unique airports, 50 MB file size.

---

## Using your game data

1. Export routes from the sim as CSV with the columns above.
2. `streamlit run streamlit_app.py`
3. **Upload** the file in the sidebar (chat history resets so answers match the new network).
4. Ask multi-leg questions and open the geographic map tab.

If a code is missing from the offline database, that airport simply won’t plot until you add an override.

---

## How it works

1. **Load** — CSV → NetworkX directed graph (sample file or upload).
2. **Parse** — NLP extracts origin & destination.
3. **Search** — fewest-stops paths or duration-weighted Dijkstra.
4. **Visualize** — Plotly `Scattergeo` maps with coordinates from `airportsdata` IATA lookup.

---

## Project layout

| File / dir            | Purpose                                         |
|-----------------------|-------------------------------------------------|
| `route_finder.py`     | Graph, path finding, NLP, timeline, matplotlib  |
| `geo_viz.py`          | Geographic Plotly maps (`Scattergeo`)           |
| `airport_coords.py`   | IATA → (lat, lon) via `airportsdata` + fallback |
| `app.py`              | CLI chat                                        |
| `streamlit_app.py`    | Web chat, CSV upload, maps                      |
| `flights.csv`         | Sample data                                     |
| `tests/`              | pytest suite                                    |
| `Dockerfile`          | Non-root container                              |
| `SECURITY.md`         | Threat model                                    |

---

## Security

Local / demo tool. Do not expose Streamlit to the public internet without auth.  
See **[SECURITY.md](SECURITY.md)**.

---

## License

Use freely for personal / home-lab / demo projects.
