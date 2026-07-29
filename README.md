# Airline Route Chat

A chat-style app that finds **direct and multi-leg flight routes** from a single CSV file of flights.  
Ask questions in plain English (“How do I get from Detroit to Denver?”) and get ranked itineraries plus **visual route maps**.

**Data source is only the CSV** — no external flight APIs.

---

## Features

- Multi-leg path finding (fewest stops)
- **Shortest path by flight time** when `DurationMinutes` is present
- Natural language + city names (“Detroit”, “Chicago”, “LA” …) as well as IATA codes
- Rich **visualizations** of any chosen route (dark theme network graph with path highlighted)
- Full network overview map
- CLI and Streamlit web UI
- Docker support

---

## Quick Start

### Local

```bash
git clone https://github.com/jjesse/airline-route-chat.git
cd airline-route-chat

pip install -r requirements.txt

# CLI chat
python app.py

# Web UI with visualizations (recommended)
streamlit run streamlit_app.py
```

### Docker

```bash
docker build -t airline-route-chat .
docker run -p 8501:8501 airline-route-chat
```

Then open http://localhost:8501

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

Airport codes are normalized to uppercase. Replace `flights.csv` with your own data — the rest of the app will adapt automatically.

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

1. **Load** — CSV → NetworkX directed graph. Edges store airplane type(s) and optional duration.
2. **Parse** — Simple but robust NLP extracts origin & destination (codes or city names).
3. **Search**
   - Default: all simple paths up to *N* stops, ranked by stops then total duration.
   - “Fastest” / toggle: Dijkstra using `DurationMinutes` as edge weight.
4. **Visualize** — Matplotlib network plot (dark theme) highlighting the selected path in cyan; start = green, end = orange. Duration labels appear on path edges.

---

## Project layout

| File               | Purpose                                      |
|--------------------|----------------------------------------------|
| `route_finder.py`  | Graph loading, path finding, NLP, viz helpers |
| `app.py`           | CLI chat interface                           |
| `streamlit_app.py` | Web chat + interactive route visualizations  |
| `flights.csv`      | Sample data (replace with yours)             |
| `requirements.txt` | Python dependencies                          |
| `Dockerfile`       | Container image for the Streamlit app        |
| `.dockerignore`    | Keep image lean                              |

---

## Tips for your own data

- Keep IATA codes consistent (always 3 letters, same case is fine — we upper-case them).
- Adding `DurationMinutes` unlocks the “fastest route” mode and better ranking.
- Multiple rows for the same origin→destination are merged (union of plane types, shortest duration kept).

---

## License

Use freely for personal / home-lab / demo projects.
