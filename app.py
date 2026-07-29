#!/usr/bin/env python3
"""CLI chat interface for the airline route finder."""

import re
from route_finder import load_graph, find_routes, format_routes


def extract_airports(query: str) -> tuple[str | None, str | None]:
    """Very simple extraction of origin and destination from natural language."""
    q = query.upper()

    # Pattern: FROM XXX TO YYY
    match = re.search(r"FROM\s+([A-Z0-9]{3})\s+TO\s+([A-Z0-9]{3})", q)
    if match:
        return match.group(1), match.group(2)

    # Pattern: XXX TO YYY
    match = re.search(r"\b([A-Z0-9]{3})\s+TO\s+([A-Z0-9]{3})\b", q)
    if match:
        return match.group(1), match.group(2)

    # Pattern: between XXX and YYY
    match = re.search(r"BETWEEN\s+([A-Z0-9]{3})\s+AND\s+([A-Z0-9]{3})", q)
    if match:
        return match.group(1), match.group(2)

    return None, None


def main():
    print("=" * 50)
    print("  Airline Route Chat")
    print("  Type questions like: How do I get from DTW to DEN?")
    print("  Type 'quit' or 'exit' to leave.")
    print("=" * 50)

    try:
        G = load_graph("flights.csv")
        print(f"\nLoaded graph with {G.number_of_nodes()} airports and {G.number_of_edges()} flights.\n")
    except Exception as e:
        print(f"Failed to load flights.csv: {e}")
        return

    while True:
        try:
            query = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not query:
            continue

        if query.lower() in {"quit", "exit", "q"}:
            print("Bye!")
            break

        origin, dest = extract_airports(query)

        if not origin or not dest:
            print("Bot: I need two airport codes. Try something like:")
            print("     How do I get from DTW to DEN?")
            print("     DTW to LAX")
            continue

        routes = find_routes(G, origin, dest, max_stops=3)

        if not routes:
            print(f"Bot: No route found from {origin} to {dest} within 3 stops.")
        else:
            print("Bot:")
            print(format_routes(routes, limit=5))


if __name__ == "__main__":
    main()
