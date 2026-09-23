"""
Unit tests for the FastBox delivery system.
Run: python -m unittest tests -v
"""

import glob
import math
import unittest

from delivery import (
    euclidean_distance, load_data, parse_locations, parse_packages,
    find_nearest_agent, assign_packages, simulate_deliveries, generate_report
)

# sample data matching the PDF spec
WAREHOUSES = {"W1": (0.0, 0.0), "W2": (50.0, 75.0), "W3": (100.0, 25.0)}
AGENTS     = {"A1": (5.0, 5.0), "A2": (60.0, 60.0), "A3": (95.0, 30.0)}
PACKAGES   = [
    {"id": "P1", "warehouse": "W1", "destination": (30.0, 40.0)},
    {"id": "P2", "warehouse": "W2", "destination": (70.0, 90.0)},
    {"id": "P3", "warehouse": "W3", "destination": (105.0, 20.0)},
    {"id": "P4", "warehouse": "W1", "destination": (10.0, 10.0)},
    {"id": "P5", "warehouse": "W2", "destination": (40.0, 80.0)},
]


class TestDistance(unittest.TestCase):

    def test_3_4_5_triangle(self):
        # classic pythagorean triple: distance should be exactly 5
        self.assertEqual(euclidean_distance((0, 0), (3, 4)), 5.0)

    def test_same_point_is_zero(self):
        self.assertEqual(euclidean_distance((10, 20), (10, 20)), 0.0)

    def test_a3_to_w3(self):
        # A3 is at (95,30), W3 is at (100,25) - should be sqrt(50)
        dist = euclidean_distance((95, 30), (100, 25))
        self.assertAlmostEqual(dist, math.sqrt(50), places=5)


class TestAssignment(unittest.TestCase):

    def test_correct_assignment(self):
        a = assign_packages(WAREHOUSES, AGENTS, PACKAGES)
        # A1 is closest to W1, should get P1 and P4
        self.assertEqual([p["id"] for p in a["A1"]], ["P1", "P4"])
        # A2 is closest to W2, should get P2 and P5
        self.assertEqual([p["id"] for p in a["A2"]], ["P2", "P5"])
        # A3 is closest to W3, should get P3
        self.assertEqual([p["id"] for p in a["A3"]], ["P3"])

    def test_all_packages_assigned(self):
        a = assign_packages(WAREHOUSES, AGENTS, PACKAGES)
        total = sum(len(pkgs) for pkgs in a.values())
        self.assertEqual(total, len(PACKAGES))


    def test_tie_goes_to_lower_id(self):
        agents = {"A2": (1.0, 0.0), "A1": (-1.0, 0.0)}  # both 1 unit from (0, 0)
        self.assertEqual(find_nearest_agent((0.0, 0.0), agents), "A1")

    def test_new_agent_only_gets_later_packages(self):
        # A4 sits right on W1 but only joins after 3 packages,
        # so P1 (1st) still goes to A1 and P4 (4th) goes to A4
        a = assign_packages(WAREHOUSES, AGENTS, PACKAGES, new_agent=("A4", (0.0, 0.0), 3))
        self.assertEqual([p["id"] for p in a["A1"]], ["P1"])
        self.assertEqual([p["id"] for p in a["A4"]], ["P4"])


class TestLoading(unittest.TestCase):

    def test_unknown_warehouse_raises(self):
        with self.assertRaises(ValueError):
            parse_packages([{"id": "P1", "warehouse": "W9", "destination": [1, 1]}], WAREHOUSES)

    def test_bad_coordinates_raise(self):
        for bad in ([1], [1, "2"], "1,2"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse_locations({"W1": bad})


class TestSimulation(unittest.TestCase):

    def test_a3_total_distance(self):
        # A3 -> W3 -> destination: sqrt(50) + sqrt(50) = 14.14
        a = assign_packages(WAREHOUSES, AGENTS, PACKAGES)
        results = simulate_deliveries(AGENTS, WAREHOUSES, a)
        self.assertAlmostEqual(results["A3"]["total_distance"], 2 * math.sqrt(50))

    def test_a1_total_distance(self):
        # A1: start -> W1 -> P1 -> W1 -> P4 = sqrt(50) + 50 + 50 + sqrt(200)
        a = assign_packages(WAREHOUSES, AGENTS, PACKAGES)
        results = simulate_deliveries(AGENTS, WAREHOUSES, a)
        expected = math.sqrt(50) + 50 + 50 + math.sqrt(200)
        self.assertAlmostEqual(results["A1"]["total_distance"], expected)


class TestReport(unittest.TestCase):

    def test_best_agent_is_a3(self):
        a = assign_packages(WAREHOUSES, AGENTS, PACKAGES)
        results = simulate_deliveries(AGENTS, WAREHOUSES, a)
        report = generate_report(results, len(PACKAGES))
        self.assertEqual(report["best_agent"], "A3")
        self.assertEqual(report["A1"]["efficiency"], 60.61)

    def test_idle_agent_gets_null_efficiency(self):
        # agent with no packages shouldn't crash and shouldn't be best_agent
        results = {
            "A1": {"delivered": [{"id": "P1", "distance_so_far": 10.0}], "total_distance": 10.0, "route": []},
            "A2": {"delivered": [], "total_distance": 0.0, "route": []},
        }
        report = generate_report(results, 1)
        self.assertIsNone(report["A2"]["efficiency"])
        self.assertEqual(report["best_agent"], "A1")

    def test_both_json_formats_give_same_result(self):
        # data.json (dict format) and base_case.json (list format) are the same scenario
        w1, a1, p1 = load_data("data.json")
        w2, a2, p2 = load_data("data/base_case.json")
        r1 = generate_report(simulate_deliveries(a1, w1, assign_packages(w1, a1, p1)), len(p1))
        r2 = generate_report(simulate_deliveries(a2, w2, assign_packages(w2, a2, p2)), len(p2))
        self.assertEqual(r1, r2)


class TestAllTestCases(unittest.TestCase):

    def test_all_provided_files(self):
        """Run the full pipeline on every provided test file."""
        files = glob.glob("data/test_case_*.json")
        self.assertTrue(len(files) > 0, "No test files found in data/")
        for filepath in sorted(files):
            with self.subTest(file=filepath):
                w, a, p = load_data(filepath)
                assignments = assign_packages(w, a, p)
                results = simulate_deliveries(a, w, assignments)
                report = generate_report(results, len(p))
                # every package must be delivered
                total = sum(v["packages_delivered"] for k, v in report.items()
                            if k != "best_agent")
                self.assertEqual(total, len(p))
                # best_agent must be one of the agents
                self.assertIn(report["best_agent"], a)


if __name__ == "__main__":
    unittest.main()
