"""
FastBox delivery system - core logic.

Flow: load_data -> assign_packages -> simulate_deliveries -> generate_report
"""

import csv
import json
import math
import random


# ---------------- Task 1: loading ----------------

def load_data(filepath):
    """Read the input JSON and return (warehouses, agents, packages).

    The provided files use two different formats, so both are handled:
      dict format: {"W1": [0, 0]}                       (PDF + test_case files)
      list format: [{"id": "W1", "location": [0, 0]}]   (base_case.json)
    Packages can use either "warehouse" or "warehouse_id".
    """
    with open(filepath, "r") as f:
        data = json.load(f)

    for key in ("warehouses", "agents", "packages"):
        if key not in data:
            raise ValueError(f"missing '{key}' in {filepath}")

    warehouses = parse_locations(data["warehouses"])
    agents = parse_locations(data["agents"])
    packages = parse_packages(data["packages"], warehouses)

    if packages and not agents:
        raise ValueError("there are packages but no agents to deliver them")

    return warehouses, agents, packages


def parse_point(value, name):
    """Make sure a location is [x, y] with two numbers, return it as a tuple."""
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{name}: location should be [x, y], got {value}")
    for v in value:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(f"{name}: coordinates must be numbers, got {value}")
    return (float(value[0]), float(value[1]))


def parse_locations(section):
    """Convert either format into a dict like {"W1": (0.0, 0.0)}."""
    result = {}

    if isinstance(section, dict):
        pairs = section.items()
    else:
        # list format -> turn each entry into an (id, location) pair
        pairs = [(entry["id"], entry["location"]) for entry in section]

    for item_id, location in pairs:
        if item_id in result:
            raise ValueError(f"duplicate id '{item_id}'")
        result[item_id] = parse_point(location, item_id)

    return result


def parse_packages(package_list, warehouses):
    """Convert packages into dicts and check each one points to a real warehouse."""
    packages = []
    seen_ids = set()

    for pkg in package_list:
        pkg_id = pkg["id"]
        if pkg_id in seen_ids:
            raise ValueError(f"duplicate package id '{pkg_id}'")
        seen_ids.add(pkg_id)

        warehouse_id = pkg.get("warehouse", pkg.get("warehouse_id"))
        if warehouse_id not in warehouses:
            raise ValueError(f"package {pkg_id} has unknown warehouse '{warehouse_id}'")

        packages.append({
            "id": pkg_id,
            "warehouse": warehouse_id,
            "destination": parse_point(pkg["destination"], pkg_id),
        })

    return packages


# ---------------- Task 2: distance + assignment ----------------

def euclidean_distance(a, b):
    """Straight line distance: sqrt((x2 - x1)^2 + (y2 - y1)^2)"""
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    return math.sqrt(dx * dx + dy * dy)


def agent_sort_key(agent_id):
    """So that A2 comes before A10 when breaking ties (plain string sort gets this wrong)."""
    digits = "".join(ch for ch in agent_id if ch.isdigit())
    return (int(digits) if digits else 0, agent_id)


def find_nearest_agent(location, agents):
    """Return the agent closest to location. If two are equally close, lower id wins."""
    return min(agents, key=lambda a: (round(euclidean_distance(agents[a], location), 6),
                                      agent_sort_key(a)))


def assign_packages(warehouses, agents, packages, new_agent=None):
    """Give each package to the agent nearest to its warehouse.

    Distance is measured from the agent's starting location.

    new_agent (bonus) is optional: (agent_id, location, join_after).
    The new agent becomes available after `join_after` packages are assigned,
    so they can only pick up packages from that point on.
    """
    available = dict(agents)
    assignments = {agent_id: [] for agent_id in agents}
    if new_agent:
        assignments[new_agent[0]] = []

    for i, pkg in enumerate(packages):
        if new_agent and i == new_agent[2]:
            available[new_agent[0]] = new_agent[1]
            print(f"{new_agent[0]} joined mid-day at {new_agent[1]} "
                  f"(after {i} packages were assigned)")

        warehouse_location = warehouses[pkg["warehouse"]]
        nearest = find_nearest_agent(warehouse_location, available)
        assignments[nearest].append(pkg)

    return assignments


# ---------------- Task 3: simulation ----------------

def simulate_deliveries(agents, warehouses, assignments):
    """Walk each agent through their packages one by one:
    current position -> warehouse (pickup) -> destination (drop)

    Agents don't go back to their start at the end of the day
    (the spec doesn't mention it).
    """
    results = {}

    for agent_id, packages in assignments.items():
        position = agents[agent_id]
        total_distance = 0.0
        route = [position]  # kept for the ASCII map
        delivered = []

        for pkg in packages:
            warehouse_location = warehouses[pkg["warehouse"]]

            # go pick it up
            total_distance += euclidean_distance(position, warehouse_location)
            position = warehouse_location
            route.append(position)

            # drop it off
            total_distance += euclidean_distance(position, pkg["destination"])
            position = pkg["destination"]
            route.append(position)

            delivered.append({"id": pkg["id"], "distance_so_far": total_distance})

        results[agent_id] = {
            "delivered": delivered,
            "total_distance": total_distance,  # rounded later, only in the report
            "route": route,
        }

    return results


# ---------------- Task 4 + 5: report ----------------

def generate_report(results, total_packages):
    """Build the report in the format from the spec.

    efficiency = total_distance / packages_delivered
    i.e. distance travelled per package, so lower is better.
    (Matches the PDF example where A1 has the lowest value and is best_agent.)

    Agents with 0 packages get efficiency = null, since dividing by zero
    doesn't make sense and 0 would wrongly make them the best agent.
    """
    report = {}
    best_agent = None
    best_efficiency = None
    delivered_total = 0

    for agent_id in sorted(results, key=agent_sort_key):
        count = len(results[agent_id]["delivered"])
        distance = results[agent_id]["total_distance"]
        delivered_total += count

        efficiency = distance / count if count > 0 else None

        report[agent_id] = {
            "packages_delivered": count,
            "total_distance": round(distance, 2),
            "efficiency": round(efficiency, 2) if efficiency is not None else None,
        }

        # compare unrounded values; on a tie the earlier (lower id) agent stays
        if efficiency is not None and (best_efficiency is None or efficiency < best_efficiency):
            best_efficiency = efficiency
            best_agent = agent_id

    # spec: total packages delivered must match total packages
    if delivered_total != total_packages:
        raise RuntimeError(f"only {delivered_total} of {total_packages} packages delivered")

    report["best_agent"] = best_agent
    return report


def save_report(report, path="report.json"):
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Report saved to {path}")


# ---------------- Bonus: export top performer to CSV ----------------

def export_top_performer_csv(report, path="top_performer.csv"):
    best = report["best_agent"]
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["agent_id", "packages_delivered", "total_distance", "efficiency"])
        if best:
            stats = report[best]
            writer.writerow([best, stats["packages_delivered"],
                             stats["total_distance"], stats["efficiency"]])
    print(f"Top performer saved to {path}")


# ---------------- Bonus: random delivery delays ----------------

def simulate_delays(results, seed=42, speed=1.0, start_hour=9):
    """Add random delays and estimate what time each package arrives.

    Assumptions: day starts at 9:00, agents move 1 distance unit per minute,
    each delivery has a 30% chance of a 5-30 minute delay.
    Delays only change timing, not distance, so report.json is not affected.
    The seed makes runs repeatable.
    """
    rng = random.Random(seed)
    log = []

    for agent_id in sorted(results, key=agent_sort_key):
        total_delay = 0.0
        for d in results[agent_id]["delivered"]:
            delay = round(rng.uniform(5, 30), 1) if rng.random() < 0.3 else 0.0
            total_delay += delay

            minutes = start_hour * 60 + d["distance_so_far"] / speed + total_delay
            arrival = f"{int(minutes // 60) % 24:02d}:{int(minutes % 60):02d}"

            log.append({"agent": agent_id, "package": d["id"],
                        "delay_minutes": delay, "arrival_time": arrival})
    return log


# ---------------- Bonus: ASCII route map ----------------

def print_ascii_map(warehouses, results, width=60, height=20):
    """Draw each agent's route on a text grid.

    W = warehouse, A = agent start, * = delivery point,
    1/2/3... = path of agent 1/2/3...
    """
    points = list(warehouses.values())
    for r in results.values():
        points += r["route"]

    min_x = min(p[0] for p in points)
    max_x = max(p[0] for p in points)
    min_y = min(p[1] for p in points)
    max_y = max(p[1] for p in points)
    span_x = max(max_x - min_x, 1)
    span_y = max(max_y - min_y, 1)

    def to_cell(p):
        col = round((p[0] - min_x) / span_x * (width - 1))
        row = round((max_y - p[1]) / span_y * (height - 1))  # flip so bigger y is at the top
        return row, col

    grid = [[" "] * width for _ in range(height)]
    agent_ids = sorted(results, key=agent_sort_key)

    # draw each route by stepping along every leg
    for n, agent_id in enumerate(agent_ids):
        symbol = str((n + 1) % 10)
        route = results[agent_id]["route"]
        for start, end in zip(route, route[1:]):
            steps = 50
            for s in range(steps + 1):
                t = s / steps
                x = start[0] + (end[0] - start[0]) * t
                y = start[1] + (end[1] - start[1]) * t
                r, c = to_cell((x, y))
                if grid[r][c] == " ":
                    grid[r][c] = symbol

    # markers go on top of the paths
    for agent_id in agent_ids:
        for p in results[agent_id]["route"][2::2]:  # every drop-off point
            r, c = to_cell(p)
            grid[r][c] = "*"
        r, c = to_cell(results[agent_id]["route"][0])
        grid[r][c] = "A"
    for loc in warehouses.values():
        r, c = to_cell(loc)
        grid[r][c] = "W"

    print("+" + "-" * width + "+")
    for row in grid:
        print("|" + "".join(row) + "|")
    print("+" + "-" * width + "+")
    print("W = warehouse  A = agent start  * = delivery point")
    for n, agent_id in enumerate(agent_ids):
        print(f"{(n + 1) % 10} = {agent_id}'s route")
