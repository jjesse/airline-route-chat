# Security Policy

## Threat model

`airline-route-chat` is a **local / home-lab / demo** tool for an airline simulation game.
It is **not** designed to be exposed on the public internet without extra controls
(authentication proxy, VPN, or network isolation).

### Assets

- Process memory (uploaded CSV, in-memory graph, Streamlit session)
- Host filesystem (temporary upload files, Docker image layers)
- CPU (path enumeration on dense graphs)

### Trust boundary

Anyone who can open the Streamlit UI can upload a CSV and run route queries.
There is **no authentication**. Treat the UI as fully trusted only on a private network.

---

## Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Huge / malicious CSV → memory or CPU exhaustion | Upload capped at **50 MB** (Streamlit + `load_graph`); max **20,000** rows; max **2,000** airports |
| Temp file leftover after upload | Uploads written via `mkstemp` and **deleted** after graph load |
| Pathological multi-leg search | `max_stops` hard-clamped to **0–5** |
| Query / upload spam (CPU) | **Rate limits** (session + process): queries **30 / 60s** per session, **120 / 60s** global; uploads **5 / 5 min** per session, **20 / 5 min** global |
| Injection via airport / plane strings | Codes: `A-Z0-9` only, length 3–4; plane types length-capped and charset-limited |
| Oversized chat queries | Cap **500** characters |
| Unbounded session memory | Chat history trimmed to last **40** messages |
| Visualization spikes | Subgraph / node counts capped |
| Filename reflected in UI | Basename only + `html.escape` |
| Cargo freighter confusion (product, not security) | Cargo types excluded from passenger graph |
| Container privilege | Runs as non-root **`appuser` (uid 1000)** |
| Streamlit defaults | Headless; CORS disabled; XSRF protection on; max upload 50 MB; no usage stats |
| Dependency vulnerabilities | Review with `pip-audit` periodically |

---

## Rate limiting details

Implemented in `rate_limit.py` as a sliding window:

| Action | Per browser session | Process-wide |
|--------|---------------------|--------------|
| Chat / route query | 30 per 60 seconds | 120 per 60 seconds |
| New CSV upload | 5 per 5 minutes | 20 per 5 minutes |

Limits are **in-memory** on the Streamlit worker. They reset when the process
restarts. They are not a substitute for edge rate limiting (nginx, Cloudflare,
etc.) if the app is ever internet-facing.

---

## What this app does **not** do

- No login / roles / multi-tenant isolation
- No outbound network calls for live flight data (airport coords/names are **offline** via `airportsdata`)
- No shell execution, `eval`, or dynamic code loading from CSV content
- No durable database of user queries (Streamlit session only)

---

## CSV upload notes

Uploads **are** supported in the Streamlit sidebar. They are subject to the same
`load_graph()` validation as on-disk files:

1. Size ≤ 50 MB (checked before and during load)
2. Required origin / destination / aircraft columns (flexible header names)
3. Invalid codes skipped; cargo aircraft rows skipped
4. Temp file removed after successful or failed parse attempt (`finally`)
5. New file identity is rate-limited (see above)

Do not treat an uploaded CSV as trusted configuration for anything beyond this app.

---

## Recommendations

1. **Do not** publish port `8501` to the open internet without auth (OAuth proxy,
   Cloudflare Access, basic auth, Tailscale/VPN, etc.).
2. Prefer **Docker** so the process is non-root and filesystem is constrained.
3. Audit dependencies occasionally:
   ```bash
   pip install pip-audit
   pip-audit -r requirements.txt
   ```
4. Keep Streamlit and pandas updated when security advisories appear.
5. If you embed this behind a reverse proxy, terminate TLS there and restrict source IPs when possible.

---

## Reporting issues

Personal / demo project. Prefer a private report to the maintainer for exploitable
issues; avoid public PoCs until a fix is available.

---

## Hardening changelog

- **2026-07-29** — Initial pass: sanitization, resource limits, non-root Docker, this document.
- **2026-07-30** — CSV upload added; ICAO support; cargo filter.
- **2026-07-30** — Upload size, temp cleanup, session bounds, Streamlit server flags.
- **2026-07-30** — **Rate limiting** for queries and uploads (session + process sliding windows).
