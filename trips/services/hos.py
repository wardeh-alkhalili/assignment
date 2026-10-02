from collections import defaultdict
from datetime import datetime, timedelta, time as dt_time

from .routing import point_along

OFF_DUTY = "off_duty"
SLEEPER = "sleeper"
DRIVING = "driving"
ON_DUTY = "on_duty"

STATUS_LABELS = {
    OFF_DUTY: "Off Duty",
    SLEEPER: "Sleeper Berth",
    DRIVING: "Driving",
    ON_DUTY: "On Duty (not driving)",
}

MAX_DRIVE_MIN = 11 * 60
MAX_WINDOW_MIN = 14 * 60
REST_MIN = 10 * 60
BREAK_AFTER_MIN = 8 * 60
BREAK_MIN = 30
PICKUP_MIN = 60
DROPOFF_MIN = 60
FUEL_EVERY_MILES = 1000
FUEL_MIN = 30
CYCLE_MAX_MIN = 70 * 60
RESTART_MIN = 34 * 60


def snap_minutes(minutes):
    if minutes <= 0:
        return 0
    snapped = int(round(minutes / 15.0) * 15)
    return snapped if snapped > 0 else 15


def _iso(value):
    return value.strftime("%Y-%m-%dT%H:%M:%S")


def _clock(value):
    return value.strftime("%H:%M")


class HosPlanner:
    def __init__(self, start, cycle_used_hours, current):
        self.now = start
        self.cycle_min = snap_minutes(float(cycle_used_hours) * 60)
        self.initial_cycle_min = self.cycle_min
        self.window_start = None
        self.drive_window = 0
        self.drive_break = 0
        self.miles_since_fuel = 0.0
        self.total_miles = 0.0
        self.events = []
        self.stops = []
        self.lat = current["lat"]
        self.lng = current["lng"]
        self.location = current["label"]
        self._pad_start_of_day(start)
        self._add_stop("current", "Current location", start, current["lat"], current["lng"], current["label"])

    def _pad_start_of_day(self, start):
        midnight = datetime.combine(start.date(), dt_time.min)
        if start > midnight:
            self.events.append(
                self._event(
                    OFF_DUTY,
                    midnight,
                    start,
                    "Off duty before trip start",
                    miles=0,
                    lat=self.lat,
                    lng=self.lng,
                    location=self.location,
                    cycle_after=self.cycle_min / 60.0,
                )
            )

    def _event(self, status, start, end, remark, miles, lat, lng, location, cycle_after):
        minutes = int((end - start).total_seconds() / 60)
        return {
            "status": status,
            "status_label": STATUS_LABELS[status],
            "start": _iso(start),
            "end": _iso(end),
            "start_clock": _clock(start),
            "end_clock": _clock(end),
            "hours": round(minutes / 60.0, 2),
            "minutes": minutes,
            "remark": remark,
            "miles": round(miles, 1),
            "lat": lat,
            "lng": lng,
            "location": location,
            "cycle_used_after": round(cycle_after, 2),
        }

    def _add_stop(self, kind, title, when, lat, lng, location, remark=""):
        self.stops.append(
            {
                "type": kind,
                "title": title,
                "time": _iso(when),
                "clock": _clock(when),
                "lat": lat,
                "lng": lng,
                "location": location,
                "remark": remark,
            }
        )

    def _window_left(self):
        if self.window_start is None:
            return MAX_WINDOW_MIN
        used = int((self.now - self.window_start).total_seconds() / 60)
        return max(0, MAX_WINDOW_MIN - used)

    def _add(self, status, minutes, remark, miles=0.0, lat=None, lng=None, location=None):
        minutes = snap_minutes(minutes)
        if minutes <= 0:
            return
        if status in (DRIVING, ON_DUTY) and self.window_start is None:
            self.window_start = self.now
        if status in (DRIVING, ON_DUTY):
            self.cycle_min += minutes
            if status == DRIVING:
                self.drive_window += minutes
                self.drive_break += minutes
        if lat is not None:
            self.lat = lat
        if lng is not None:
            self.lng = lng
        if location:
            self.location = location
        start = self.now
        end = start + timedelta(minutes=minutes)
        self.now = end
        self.total_miles += miles
        if miles:
            self.miles_since_fuel += miles
        self.events.append(
            self._event(
                status,
                start,
                end,
                remark,
                miles,
                self.lat,
                self.lng,
                self.location,
                self.cycle_min / 60.0,
            )
        )

    def rest_10(self, remark="10-hour sleeper berth rest (11/14-hour reset)"):
        self._add_stop("rest", "Sleeper berth rest", self.now, self.lat, self.lng, self.location, remark)
        self._add(SLEEPER, REST_MIN, remark)
        self.window_start = None
        self.drive_window = 0
        self.drive_break = 0

    def break_30(self):
        self._add_stop(
            "break",
            "30-minute break",
            self.now,
            self.lat,
            self.lng,
            self.location,
            "Required after 8 hours of driving",
        )
        self._add(OFF_DUTY, BREAK_MIN, "30-minute rest break")
        self.drive_break = 0

    def restart_34(self):
        self._add_stop(
            "restart",
            "34-hour restart",
            self.now,
            self.lat,
            self.lng,
            self.location,
            "70-hour / 8-day cycle reset",
        )
        self._add(OFF_DUTY, RESTART_MIN, "34-hour restart (70-hour / 8-day cycle reset)")
        self.cycle_min = 0
        self.window_start = None
        self.drive_window = 0
        self.drive_break = 0

    def ensure_can_drive(self):
        guard = 0
        while guard < 20:
            guard += 1
            if CYCLE_MAX_MIN - self.cycle_min < 15:
                self.restart_34()
                continue
            window_left = self._window_left()
            drive_left = MAX_DRIVE_MIN - self.drive_window
            until_break = BREAK_AFTER_MIN - self.drive_break
            if drive_left < 15 or window_left < 15:
                self.rest_10()
                continue
            if until_break < 15:
                if window_left >= BREAK_MIN + 15:
                    self.break_30()
                else:
                    self.rest_10()
                continue
            return min(window_left, drive_left, until_break, CYCLE_MAX_MIN - self.cycle_min)
        return 15

    def maybe_fuel(self):
        if self.miles_since_fuel < FUEL_EVERY_MILES - 0.5:
            return
        if CYCLE_MAX_MIN - self.cycle_min < FUEL_MIN:
            self.restart_34()
        if self._window_left() < FUEL_MIN:
            self.rest_10()
        self._add_stop(
            "fuel",
            "Fuel stop",
            self.now,
            self.lat,
            self.lng,
            self.location,
            "Fueling at least once every 1,000 miles",
        )
        self._add(ON_DUTY, FUEL_MIN, "Fuel stop (required every 1,000 miles)")
        self.miles_since_fuel = 0

    def on_duty_stop(self, minutes, remark, kind, title, lat, lng, location):
        if CYCLE_MAX_MIN - self.cycle_min < minutes:
            self.restart_34()
        self._add_stop(kind, title, self.now, lat, lng, location, remark)
        self._add(ON_DUTY, minutes, remark, lat=lat, lng=lng, location=location)

    def drive_leg(self, miles, minutes, coords, dest_label, dest_lat, dest_lng):
        if miles < 0.2:
            self.lat, self.lng = dest_lat, dest_lng
            self.location = dest_label
            return

        remaining_m = float(miles)
        remaining_min = float(minutes)
        traveled = 0.0
        guard = 0
        while remaining_m > 0.05 and guard < 400:
            guard += 1
            self.maybe_fuel()
            cap_min = self.ensure_can_drive()
            mpm = remaining_min / remaining_m if remaining_m else 0
            miles_to_fuel = max(0.1, FUEL_EVERY_MILES - self.miles_since_fuel)
            cap_miles = cap_min / mpm if mpm else remaining_m
            chunk_m = min(remaining_m, miles_to_fuel, cap_miles)
            chunk_min = chunk_m * mpm if mpm else cap_min
            if remaining_m - chunk_m <= 0.05:
                chunk_m = remaining_m
                chunk_min = remaining_min
            chunk_min = snap_minutes(chunk_min)
            if chunk_min <= 0:
                self.rest_10()
                continue
            traveled += chunk_m
            fraction = min(1.0, traveled / miles)
            lat, lng = point_along(coords, fraction) or (dest_lat, dest_lng)
            self._add(
                DRIVING,
                chunk_min,
                f"Driving toward {dest_label.split(',')[0]}",
                miles=chunk_m,
                lat=lat,
                lng=lng,
                location=self.location,
            )
            remaining_m -= chunk_m
            remaining_min = max(0, remaining_min - chunk_min)

        self.lat, self.lng = dest_lat, dest_lng
        self.location = dest_label


def _split_at_midnight(event):
    start = datetime.fromisoformat(event["start"])
    end = datetime.fromisoformat(event["end"])
    pieces = []
    cursor = start
    while cursor < end:
        next_midnight = datetime.combine(cursor.date() + timedelta(days=1), dt_time.min)
        chunk_end = min(end, next_midnight)
        minutes = int((chunk_end - cursor).total_seconds() / 60)
        piece = dict(event)
        piece["start"] = _iso(cursor)
        piece["end"] = _iso(chunk_end)
        piece["start_clock"] = _clock(cursor)
        piece["end_clock"] = _clock(chunk_end)
        piece["minutes"] = minutes
        piece["hours"] = round(minutes / 60.0, 2)
        if event["minutes"]:
            piece["miles"] = round(event["miles"] * (minutes / event["minutes"]), 1)
        pieces.append(piece)
        cursor = chunk_end
    return pieces


def _minutes_from_midnight(iso_value):
    value = datetime.fromisoformat(iso_value)
    return value.hour * 60 + value.minute


def build_daily_logs(events, start_cycle_hours):
    by_day = defaultdict(list)
    for event in events:
        for piece in _split_at_midnight(event):
            day = datetime.fromisoformat(piece["start"]).date()
            by_day[day].append(piece)

    logs = []
    on_duty_by_day = {}
    for day in sorted(by_day):
        pieces = by_day[day]
        day_start = datetime.combine(day, dt_time.min)
        first_start = datetime.fromisoformat(pieces[0]["start"])
        if first_start > day_start:
            lead = int((first_start - day_start).total_seconds() / 60)
            pieces.insert(
                0,
                {
                    "status": OFF_DUTY,
                    "status_label": STATUS_LABELS[OFF_DUTY],
                    "start": _iso(day_start),
                    "end": _iso(first_start),
                    "start_clock": "00:00",
                    "end_clock": _clock(first_start),
                    "hours": round(lead / 60.0, 2),
                    "minutes": lead,
                    "remark": "Off duty",
                    "miles": 0,
                    "lat": pieces[0]["lat"],
                    "lng": pieces[0]["lng"],
                    "location": pieces[0]["location"],
                    "cycle_used_after": pieces[0].get("cycle_used_after"),
                },
            )
        last_end = datetime.fromisoformat(pieces[-1]["end"])
        end_of_day = datetime.combine(day + timedelta(days=1), dt_time.min)
        if last_end < end_of_day:
            leftover = int((end_of_day - last_end).total_seconds() / 60)
            if leftover:
                pieces.append(
                    {
                        "status": OFF_DUTY,
                        "status_label": STATUS_LABELS[OFF_DUTY],
                        "start": _iso(last_end),
                        "end": _iso(end_of_day),
                        "start_clock": _clock(last_end),
                        "end_clock": "24:00",
                        "hours": round(leftover / 60.0, 2),
                        "minutes": leftover,
                        "remark": "Off duty",
                        "miles": 0,
                        "lat": pieces[-1]["lat"],
                        "lng": pieces[-1]["lng"],
                        "location": pieces[-1]["location"],
                        "cycle_used_after": pieces[-1]["cycle_used_after"],
                    }
                )

        totals = {OFF_DUTY: 0, SLEEPER: 0, DRIVING: 0, ON_DUTY: 0}
        grid = []
        remarks = []
        miles = 0.0
        for piece in pieces:
            totals[piece["status"]] += piece["minutes"]
            miles += piece.get("miles") or 0
            start_min = _minutes_from_midnight(piece["start"])
            end_min = start_min + piece["minutes"]
            if end_min > 24 * 60:
                end_min = 24 * 60
            grid.append(
                {
                    "status": piece["status"],
                    "start_min": start_min,
                    "end_min": end_min,
                    "remark": piece["remark"],
                }
            )
            if piece["status"] != OFF_DUTY or "break" in piece["remark"].lower() or "restart" in piece["remark"].lower():
                remarks.append(
                    {
                        "time": piece["start_clock"],
                        "status": piece["status_label"],
                        "text": piece["remark"],
                        "location": piece.get("location") or "",
                    }
                )

        on_duty_today = (totals[DRIVING] + totals[ON_DUTY]) / 60.0
        on_duty_by_day[day] = on_duty_today
        cycle_at_end = pieces[-1].get("cycle_used_after")
        if cycle_at_end is None:
            cycle_at_end = start_cycle_hours + sum(on_duty_by_day.values())

        last_five = [on_duty_by_day[d] for d in sorted(on_duty_by_day)[-5:]]
        locations = [p.get("location") for p in pieces if p.get("location")]
        from_place = (locations[0] if locations else "").split(",")[0]
        to_place = (locations[-1] if locations else "").split(",")[0]

        logs.append(
            {
                "date": day.isoformat(),
                "from": from_place,
                "to": to_place,
                "total_miles": round(miles, 1),
                "grid": grid,
                "remarks": remarks,
                "totals": {
                    "off_duty": round(totals[OFF_DUTY] / 60.0, 2),
                    "sleeper": round(totals[SLEEPER] / 60.0, 2),
                    "driving": round(totals[DRIVING] / 60.0, 2),
                    "on_duty": round(totals[ON_DUTY] / 60.0, 2),
                },
                "recap": {
                    "a": round(cycle_at_end, 2),
                    "b": round(max(0, 70 - cycle_at_end), 2),
                    "c": round(sum(last_five), 2),
                },
            }
        )
    return logs


def plan_hos(route, locations, cycle_used_hours, start=None):
    start = start or datetime.combine(datetime.now().date(), dt_time(hour=6))
    current, pickup, dropoff = locations["current"], locations["pickup"], locations["dropoff"]
    to_pickup, to_dropoff = route["legs"]
    planner = HosPlanner(start, cycle_used_hours, current)

    planner.drive_leg(
        to_pickup["miles"],
        to_pickup["minutes"],
        to_pickup["coordinates"],
        pickup["label"],
        pickup["lat"],
        pickup["lng"],
    )
    planner.on_duty_stop(
        PICKUP_MIN,
        "Pickup / loading (1 hour)",
        "pickup",
        "Pickup",
        pickup["lat"],
        pickup["lng"],
        pickup["label"],
    )
    planner.drive_leg(
        to_dropoff["miles"],
        to_dropoff["minutes"],
        to_dropoff["coordinates"],
        dropoff["label"],
        dropoff["lat"],
        dropoff["lng"],
    )
    planner.on_duty_stop(
        DROPOFF_MIN,
        "Dropoff / unloading (1 hour)",
        "dropoff",
        "Dropoff",
        dropoff["lat"],
        dropoff["lng"],
        dropoff["label"],
    )

    daily_logs = build_daily_logs(planner.events, cycle_used_hours)
    duty_events = [e for e in planner.events if e["status"] in (DRIVING, ON_DUTY, SLEEPER) or "break" in e["remark"].lower()]
    return {
        "start_time": _iso(start),
        "events": planner.events,
        "stops": planner.stops,
        "daily_logs": daily_logs,
        "summary": {
            "total_miles": round(planner.total_miles, 1),
            "driving_hours": round(sum(e["minutes"] for e in planner.events if e["status"] == DRIVING) / 60.0, 2),
            "on_duty_hours": round(
                sum(e["minutes"] for e in planner.events if e["status"] in (DRIVING, ON_DUTY)) / 60.0,
                2,
            ),
            "days": len(daily_logs),
            "fuel_stops": sum(1 for s in planner.stops if s["type"] == "fuel"),
            "rest_stops": sum(1 for s in planner.stops if s["type"] in ("rest", "restart")),
            "breaks": sum(1 for s in planner.stops if s["type"] == "break"),
            "ending_cycle_used": round(planner.cycle_min / 60.0, 2),
            "cycle_remaining": round(max(0, 70 - planner.cycle_min / 60.0), 2),
        },
        "timeline": duty_events,
    }
