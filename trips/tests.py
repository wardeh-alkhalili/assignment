from datetime import datetime

from django.test import SimpleTestCase, TestCase

from trips.services.hos import (
    BREAK_AFTER_MIN,
    DRIVING,
    MAX_DRIVE_MIN,
    OFF_DUTY,
    ON_DUTY,
    SLEEPER,
    HosPlanner,
    build_daily_logs,
    plan_hos,
)


def _leg(miles, hours, origin, dest):
    return {
        "from": origin,
        "to": dest,
        "miles": miles,
        "minutes": hours * 60,
        "hours": hours,
        "coordinates": [
            [origin["lng"], origin["lat"]],
            [dest["lng"], dest["lat"]],
        ],
    }


CURRENT = {"label": "Chicago, IL", "lat": 41.88, "lng": -87.63}
PICKUP = {"label": "St. Louis, MO", "lat": 38.63, "lng": -90.20}
DROPOFF = {"label": "Kansas City, MO", "lat": 39.10, "lng": -94.58}


class HosPlannerTests(SimpleTestCase):
    def test_short_trip_includes_pickup_and_dropoff_hours(self):
        route = {
            "legs": [
                _leg(50, 1, CURRENT, PICKUP),
                _leg(50, 1, PICKUP, DROPOFF),
            ]
        }
        plan = plan_hos(
            route,
            {"current": CURRENT, "pickup": PICKUP, "dropoff": DROPOFF},
            cycle_used_hours=12,
            start=datetime(2026, 10, 2, 6, 0),
        )
        statuses = [e["status"] for e in plan["events"] if e["status"] != OFF_DUTY or "break" in e["remark"].lower()]
        self.assertIn(DRIVING, statuses)
        self.assertIn(ON_DUTY, statuses)
        on_duty = sum(e["minutes"] for e in plan["events"] if e["status"] == ON_DUTY)
        self.assertGreaterEqual(on_duty, 120)
        self.assertEqual(plan["summary"]["fuel_stops"], 0)
        self.assertEqual(len(plan["daily_logs"]), 1)
        totals = plan["daily_logs"][0]["totals"]
        self.assertAlmostEqual(
            totals["off_duty"] + totals["sleeper"] + totals["driving"] + totals["on_duty"],
            24,
            delta=0.1,
        )

    def test_eight_hours_driving_requires_break(self):
        planner = HosPlanner(datetime(2026, 10, 2, 6, 0), 0, CURRENT)
        planner.drive_leg(
            500,
            9 * 60,
            [[CURRENT["lng"], CURRENT["lat"]], [PICKUP["lng"], PICKUP["lat"]]],
            PICKUP["label"],
            PICKUP["lat"],
            PICKUP["lng"],
        )
        breaks = [e for e in planner.events if e["status"] == OFF_DUTY and "30-minute" in e["remark"]]
        self.assertTrue(breaks)
        driving = sum(e["minutes"] for e in planner.events if e["status"] == DRIVING)
        self.assertGreaterEqual(driving, BREAK_AFTER_MIN)

    def test_eleven_hour_drive_limit_inserts_sleeper(self):
        planner = HosPlanner(datetime(2026, 10, 2, 6, 0), 0, CURRENT)
        planner.drive_leg(
            900,
            16 * 60,
            [[CURRENT["lng"], CURRENT["lat"]], [DROPOFF["lng"], DROPOFF["lat"]]],
            DROPOFF["label"],
            DROPOFF["lat"],
            DROPOFF["lng"],
        )
        sleepers = [e for e in planner.events if e["status"] == SLEEPER]
        self.assertTrue(sleepers)
        self.assertGreaterEqual(sleepers[0]["minutes"], 10 * 60)
        max_drive_block = 0
        current_block = 0
        for event in planner.events:
            if event["status"] == DRIVING:
                current_block += event["minutes"]
                max_drive_block = max(max_drive_block, current_block)
            elif event["status"] == SLEEPER:
                current_block = 0
        self.assertLessEqual(max_drive_block, MAX_DRIVE_MIN)

    def test_fuel_stop_every_thousand_miles(self):
        route = {
            "legs": [
                _leg(200, 4, CURRENT, PICKUP),
                _leg(900, 16, PICKUP, DROPOFF),
            ]
        }
        plan = plan_hos(
            route,
            {"current": CURRENT, "pickup": PICKUP, "dropoff": DROPOFF},
            cycle_used_hours=0,
            start=datetime(2026, 10, 2, 6, 0),
        )
        self.assertGreaterEqual(plan["summary"]["fuel_stops"], 1)
        self.assertGreaterEqual(plan["summary"]["days"], 2)

    def test_cycle_limit_triggers_34_hour_restart(self):
        planner = HosPlanner(datetime(2026, 10, 2, 6, 0), 70, CURRENT)
        planner.on_duty_stop(60, "Pickup / loading (1 hour)", "pickup", "Pickup", PICKUP["lat"], PICKUP["lng"], PICKUP["label"])
        restarts = [e for e in planner.events if "34-hour" in e["remark"]]
        self.assertTrue(restarts)
        self.assertLessEqual(planner.cycle_min, 70 * 60)

    def test_daily_logs_cover_24_hours(self):
        events = [
            {
                "status": DRIVING,
                "status_label": "Driving",
                "start": "2026-10-02T06:00:00",
                "end": "2026-10-02T11:00:00",
                "minutes": 300,
                "remark": "Driving",
                "miles": 250,
                "lat": 41.8,
                "lng": -87.6,
                "location": "Chicago, IL",
                "cycle_used_after": 5,
            }
        ]
        logs = build_daily_logs(events, 0)
        self.assertEqual(len(logs), 1)
        totals = logs[0]["totals"]
        self.assertAlmostEqual(sum(totals.values()), 24, delta=0.05)


class PlanApiTests(TestCase):
    def test_health(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_plan_requires_locations(self):
        response = self.client.post(
            "/api/trips/plan/",
            data={"current_cycle_used": 10},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
