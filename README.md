# Airline Route Chat

A chat-style app that finds **direct and multi-leg flight routes** from a single CSV file of flights.  
Ask questions in plain English (“How do I get from Detroit to Denver?”) and get ranked itineraries plus **interactive route maps**.

**Data source is only the CSV** — no external flight APIs.

---

## Features

- Multi-leg path finding (fewest stops)
- **Shortest path by flight time** when `DurationMinutes` is present
- Natural language + city names (“Detroit”, “Chicago”, “LA” …) as well as IATA codes
- **Interactive Plotly visualizations**
  - Route network map (zoom, pan, hover for aircraft & duration)
  - Leg duration timeline
  - Full network overview
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

# Web UI with interactive visualizations (recommended)
streamlit run streamlit_app.py
```

### Docker

```bash
docker build -t airline-route-chat .
docker run -p 8501:8501 airline-route-chat
```

Then open http://localhost:8501

The container runs as an unprivileged user (`appuser`).

---

## Running tests

```bash
pip install -r requirements.txt
pytest
```

Tests cover sanitization, NLP extraction, CSV limits, path finding, formatting, and both matplotlib + Plotly visualization smoke tests.

---

## CSV Format

Required columns:

| Column                | Description              |
|-----------------------|--------------------------|
| Originating Airport   | 3-letter IATA code       |
| Destination Airport   | 3-letter IATA code       |
| Airplane Type         | e.g. A320, B737          |

Optional but recommended:

| Column            | Description                          |
|-------------------|--------------------------------------|
| DurationMinutes   | Block time in minutes (for weighted shortest path) |

Example:

```csv
Originating Airport,Destination Airport,Airplane Type,DurationMinutes
DTW,ORD,A320,70
ORD,DEN,B737,145
DTW,DEN,A321,175
...
```

Airport codes are sanitized and normalized to uppercase. Replace `flights.csv` with your own data — the rest of the app will adapt automatically.

**Limits** (for safety): max ~20k rows, ~2k unique airports, 50 MB file size.

---

## Example queries

```
How do I get from Detroit to Denver?
ORD to LAX
fastest from Atlanta to Seattle
route between Chicago and Miami
DTW-SFO
```

City names currently recognized: Detroit, Chicago / O'Hare, Denver, Los Angeles / LA, Atlanta, Miami, Seattle / SeaTac, San Francisco / SF, Minneapolis.

---

## How it works

1. **Load** — CSV → NetworkX directed graph (with size/airport caps).
2. **Parse** — Sanitized NLP extracts origin & destination.
3. **Search**
   - Default: all simple paths up to *N* stops (hard-capped at 5).
   - “Fastest”: Dijkstra using `DurationMinutes`.
4. **Visualize (Streamlit)**
   - **Route map** — interactive Plotly network; green origin, orange destination, cyan path edges; hover for plane type & duration.
   - **Leg timeline** — horizontal bar chart of each segment’s minutes.
   - **Full network** — zoomable overview of all airports in the CSV.

Static matplotlib helpers remain available for CLI / export / tests.

---

## Project layout

| File / dir         | Purpose                                      |
|--------------------|----------------------------------------------|
| `route_finder.py`  | Graph, path finding, NLP, matplotlib + Plotly viz |
| `app.py`           | CLI chat interface                           |
| `streamlit_app.py` | Web chat + interactive charts                |
| `flights.csv`      | Sample data                                  |
| `tests/`           | pytest suite                                 |
| `requirements.txt` | Python dependencies                          |
| `Dockerfile`       | Non-root container image                     |
| `SECURITY.md`      | Threat model and hardening notes             |

---

## Security

This is a **local / demo** tool. Do not expose the Streamlit port to the public internet without authentication.

See **[SECURITY.md](SECURITY.md)** for the full threat model, limits, and recommendations.

---

## License

Use freely for personal / home-lab / demo projects.
