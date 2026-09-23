"""
FastBox Mystery Delivery System

Usage:
    python main.py                            # uses data.json
    python main.py data/test_case_1.json
    python main.py --ascii --delays
    python main.py --new-agent A4 50 50 3     # A4 joins after 3 packages
"""

import argparse
import json
import sys

from delivery import (
    load_data, assign_packages, simulate_deliveries, generate_report,
    save_report, export_top_performer_csv, simulate_delays, print_ascii_map,
)


def main():
    parser = argparse.ArgumentParser(description="FastBox delivery simulator")
    parser.add_argument("input", nargs="?", default="data.json", help="input JSON file")
    parser.add_argument("-o", "--output", default="report.json", help="where to save the report")
    parser.add_argument("--ascii", action="store_true", help="show routes as an ASCII map")
    parser.add_argument("--delays", action="store_true", help="simulate random delivery delays")
    parser.add_argument("--seed", type=int, default=42, help="random seed for --delays")
    parser.add_argument("--new-agent", nargs=4, metavar=("ID", "X", "Y", "JOIN_AFTER"),
                        help="add an agent mid-day, e.g. --new-agent A4 50 50 3")
    args = parser.parse_args()

    try:
        warehouses, agents, packages = load_data(args.input)
    except FileNotFoundError:
        print(f"Error: file '{args.input}' not found")
        sys.exit(1)
    except (ValueError, KeyError, TypeError) as e:
        print(f"Error: bad input data - {e}")
        sys.exit(1)

    new_agent = None
    if args.new_agent:
        agent_id, x, y, join_after = args.new_agent
        if agent_id in agents:
            print(f"Error: agent '{agent_id}' already exists")
            sys.exit(1)
        new_agent = (agent_id, (float(x), float(y)), int(join_after))

    assignments = assign_packages(warehouses, agents, packages, new_agent)

    # the new agent needs a start point for the simulation too
    start_points = dict(agents)
    if new_agent:
        start_points[new_agent[0]] = new_agent[1]
    results = simulate_deliveries(start_points, warehouses, assignments)
    report = generate_report(results, len(packages))

    save_report(report, args.output)
    export_top_performer_csv(report)

    # summary table
    print(f"\n{'Agent':<7}{'Packages':>9}{'Distance':>11}{'Efficiency':>12}")
    for agent_id, stats in report.items():
        if agent_id == "best_agent":
            continue
        eff = stats["efficiency"] if stats["efficiency"] is not None else "-"
        print(f"{agent_id:<7}{stats['packages_delivered']:>9}"
              f"{stats['total_distance']:>11.2f}{eff:>12}")
    print(f"Best agent: {report['best_agent']}")

    if args.delays:
        log = simulate_delays(results, seed=args.seed)
        with open("delay_log.json", "w") as f:
            json.dump(log, f, indent=2)
        print("\nDelivery times with random delays:")
        for entry in log:
            note = f"(+{entry['delay_minutes']} min delay)" if entry["delay_minutes"] else ""
            print(f"  {entry['agent']} delivered {entry['package']} at {entry['arrival_time']} {note}")
        print("Saved to delay_log.json")

    if args.ascii:
        print()
        print_ascii_map(warehouses, results)


if __name__ == "__main__":
    main()
