# Airline Route Chat

A chat-style app that finds **direct and multi-leg flight routes** from a single CSV file of flights.  
Ask questions in plain English (“How do I get from Detroit to Denver?”) and get ranked itineraries plus **geographic route maps**.

**Data source is only the CSV** — no external flight APIs.

---

## Features

- Multi-leg path finding (fewest stops)
- **Shortest path by flight time** when `DurationMinutes` is present
- Natural language + city names (“Detroit”, “Chicago”, “LA” …) as well as IATA codes
- **Interactive Plotly visualizations**
  - **Geographic route map** (real lat/lon, coastlines, zoom/pan)
  - Leg duration timeline
  - Full network overview on a US map
- CLI and Streamlit web UI
- Docker support (runs as non-root)
- Input sanitization and resource limits (see [SECURITY.md](SECURITY.md))
- Automated test suite (pytest)

---

## Quick Start

### Local

```bash
git clone https://github.com/jjesse/airline-route-chat.git
cd airline-route-chat

pip install -r requirements.txt

# CLI chat
python app.py

# Web UI with geographic maps (recommended)
streamlit run streamlit_app.py
```

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

---

## CSV Format

Required columns: `Originating Airport`, `Destination Airport`, `Airplane Type`  
Optional: `DurationMinutes`

Airport codes are sanitized to 3-letter uppercase. For geographic maps, add coordinates in `airport_coords.py` when you introduce new airports.

**Limits**: max ~20k rows, ~2k unique airports, 50 MB file size.

---

## How it works

1. **Load** — CSV → NetworkX directed graph.
2. **Parse** — NLP extracts origin & destination.
3. **Search** — fewest-stops paths or duration-weighted Dijkstra.
4. **Visualize (Streamlit)**
   - **Geographic map** — Plotly `Scattergeo` using lat/lon from `airport_coords.py`
   - **Leg timeline** — bar chart of segment minutes
   - **Full network** — all sample airports plotted on a US map

---

## Project layout

| File / dir            | Purpose                                      |
|-----------------------|----------------------------------------------|
| `route_finder.py`     | Graph, path finding, NLP, timeline, matplotlib |
| `geo_viz.py`          | Geographic Plotly maps (`Scattergeo`)        |
| `airport_coords.py`   | IATA → (lat, lon) lookup                     |
| `app.py`              | CLI chat                                     |
| `streamlit_app.py`    | Web chat + maps                              |
| `flights.csv`         | Sample data                                  |
| `tests/`              | pytest suite                                 |
| `Dockerfile`          | Non-root container                           |
| `SECURITY.md`         | Threat model                                 |

---

## Security

Local / demo tool. See **[SECURITY.md](SECURITY.md)**.

---

## License

Use freely for personal / home-lab / demo projects.
