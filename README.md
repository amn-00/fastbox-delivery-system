# FastBox Mystery Delivery System

Python assignment for Nexgensis Technologies. Simulates one day of deliveries: each package goes to the nearest agent, every agent's route is simulated, and the results are saved to `report.json`.

Uses only the Python standard library (tested on Python 3.8+), so there's nothing to install.

## How to run

```bash
python main.py                          # reads data.json, writes report.json
python main.py data/test_case_1.json    # run on any other input file
```

Bonus options:

```bash
python main.py --ascii                  # draw agent routes as an ASCII map
python main.py --delays                 # random delivery delays, saved to delay_log.json
python main.py --delays --seed 7        # different (but repeatable) delays
python main.py --new-agent A4 50 50 3   # agent A4 at (50,50) joins after 3 packages
```

`top_performer.csv` is written on every run.

Run the tests:

```bash
python -m unittest tests -v
```

## Files

- `main.py` - command line entry point
- `delivery.py` - all the logic (loading, assignment, simulation, report, bonuses)
- `tests.py` - unit tests, including a run over every file in `data/`
- `data.json` - the sample input from the assignment PDF
- `data/` - the test inputs that came with the assignment

## Output for data.json

```json
{
  "A1": {"packages_delivered": 2, "total_distance": 121.21, "efficiency": 60.61},
  "A2": {"packages_delivered": 2, "total_distance": 79.21, "efficiency": 39.6},
  "A3": {"packages_delivered": 1, "total_distance": 14.14, "efficiency": 14.14},
  "best_agent": "A3"
}
```

The numbers in the PDF's example report don't come from the sample data (they look like placeholders), but the package counts match (2, 2, 1). I checked A1 by hand: sqrt(50) + 50 + 50 + sqrt(200) = 121.21.

## Assumptions

The assignment asked to document any decisions on things the spec doesn't cover, so here they are:

1. **Two input formats.** `base_case.json` stores warehouses and agents as a list (`{"id": ..., "location": ...}`) and uses `warehouse_id`, while the PDF and the test cases use a dict and `warehouse`. The loader accepts both. `data.json` and `base_case.json` give the same report.
2. **Nearest agent** is measured from the agent's starting location to the package's warehouse, as the spec describes. If two agents are equally close, the lower ID wins (A1 before A2).
3. **No capacity limit.** An agent can get any number of packages, so in several test cases some agents get nothing.
4. **Route order.** Each agent handles its packages one at a time, in input order: current position -> warehouse -> destination. Agents don't return to their start at the end of the day.
5. **Efficiency = total distance / packages delivered**, i.e. distance per package, so **lower is better**. This matches the PDF example, where the agent with the lowest value is `best_agent`.
6. **Agents with 0 packages** show `efficiency: null` and can't be `best_agent`, since dividing by zero isn't meaningful and 0 would wrongly make them the best.
7. Rounding to 2 decimals only happens in the output. Comparisons use full values.
8. **Bad input** (missing keys, unknown warehouse, duplicate IDs, bad coordinates) stops the program with a clear error message instead of skipping packages, because skipping would break "delivered = total packages". The program also checks that count at the end.
9. **Delays** (bonus) only change arrival times, not distance, so `report.json` isn't affected. Assumed: day starts at 9:00, speed of 1 unit per minute, 30% chance of a 5 to 30 minute delay per delivery.
10. **Mid-day agent** (bonus): packages are assigned in input order, and the new agent can only get packages assigned after it joins. Earlier assignments aren't changed, since those agents are already out delivering.
