# Security Policy

## Threat Model

`airline-route-chat` is intended as a **local / home-lab / demo tool** for a silly airline simulation game.  
It is **not** designed to be exposed to the public internet without additional controls.

Primary risks we care about:

| Risk | Mitigation |
|------|------------|
| Malicious or huge CSV causing memory/CPU exhaustion | Row limit (20k), file size limit (50 MB), airport count limit (2k) |
| Pathological path-search (combinatorial explosion) | `max_stops` hard-clamped to 0–5 |
| Injection via airport codes / plane types | Strict sanitization: only `A-Z0-9` for codes; limited charset + length for plane types |
| Oversized user queries | Query length capped at 500 characters |
| Visualization resource spikes | Subgraph node count capped for matplotlib |
| Container privilege escalation | Dockerfile runs as non-root `appuser` (uid 1000) |
| Dependency vulnerabilities | Pin ranges in `requirements.txt`; run `pip-audit` periodically |

## What this app does **not** do

- No authentication / authorization
- No file upload endpoint (yet)
- No external network calls for flight data
- No shell execution or dynamic code evaluation
- No persistent storage of user queries beyond Streamlit session state

## Recommendations

1. **Do not** publish the Streamlit port to the open internet without putting it behind authentication (e.g. OAuth proxy, Cloudflare Access, basic auth, or a VPN).
2. When adding CSV upload in the future, treat the uploaded file with the same validation already present in `load_graph()`.
3. Keep dependencies updated:
   ```bash
   pip install pip-audit
   pip-audit -r requirements.txt
   ```
4. Prefer running via Docker so the process is isolated and non-root.

## Reporting Issues

This is a personal/demo project. If you find a security issue, open a GitHub issue or contact the maintainer directly. Please avoid filing public issues that contain exploit details until a fix is available.

## Hardening changelog

- 2026-07-29: Initial security pass — input sanitization, resource limits, non-root Docker user, this document.
