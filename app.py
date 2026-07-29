#!/usr/bin/env python3
"""CLI chat interface for the airline route finder."""

from route_finder import (
    load_graph,
    find_routes,
    find_shortest_by_time,
    format_routes,
    extract_airports,
    clamp_max_stops,
)


def main():
    print("=" * 56)
    print("  Airline Route Chat  (CLI)")
    print("  Examples:")
    print("    How do I get from Detroit to Denver?")
    print("    ORD to LAX")
    print("    fastest from ATL to SEA")
    print("  Type 'quit' or 'exit' to leave.")
    print("=" * 56)

    try:
        G = load_graph("flights.csv")
        print(
            f"\nLoaded graph with {G.number_of_nodes()} airports "
            f"and {G.number_of_edges()} flights.\n"
        )
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

        if len(query) > 500:
            print("Bot: Query too long (max 500 characters).")
            continue

        origin, dest = extract_airports(query)

        if not origin or not dest:
            print("Bot: I need two airports. Try:")
            print("     How do I get from Detroit to Denver?")
            print("     DTW to LAX")
            print("     fastest ORD to SEA")
            continue

        want_fastest = any(
            w in query.lower()
            for w in ("fastest", "shortest", "quickest", "least time", "by time")
        )

        if want_fastest:
            best = find_shortest_by_time(G, origin, dest)
            if not best:
                print(f"Bot: No timed route found from {origin} to {dest}.")
            else:
                print("Bot: Fastest route by flight time:")
                print(format_routes([best], limit=1))
        else:
            routes = find_routes(G, origin, dest, max_stops=clamp_max_stops(3))
            if not routes:
                print(f"Bot: No route found from {origin} to {dest} within 3 stops.")
            else:
                print("Bot:")
                print(format_routes(routes, limit=5))


if __name__ == "__main__":
    main()
