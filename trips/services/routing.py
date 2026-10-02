import math

import requests

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
METERS_PER_MILE = 1609.344


class RoutingError(ValueError):
    pass


def haversine_miles(lat1, lng1, lat2, lng2):
    radius = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def point_along(coords, fraction):
    """Return (lat, lng) at a fraction of distance along a GeoJSON LineString."""
    if not coords:
        return None
    if fraction <= 0:
        return coords[0][1], coords[0][0]
    if fraction >= 1:
        return coords[-1][1], coords[-1][0]

    segments = []
    total = 0.0
    for start, end in zip(coords, coords[1:]):
        miles = haversine_miles(start[1], start[0], end[1], end[0])
        segments.append((start, end, miles))
        total += miles
    if total == 0:
        return coords[-1][1], coords[-1][0]

    target = total * fraction
    walked = 0.0
    for start, end, miles in segments:
        if walked + miles >= target:
            part = 0 if miles == 0 else (target - walked) / miles
            lng = start[0] + (end[0] - start[0]) * part
            lat = start[1] + (end[1] - start[1]) * part
            return lat, lng
        walked += miles
    return coords[-1][1], coords[-1][0]


def _leg_from_osrm(leg, origin, destination):
    meters = float(leg.get("distance") or 0)
    seconds = float(leg.get("duration") or 0)
    miles = meters / METERS_PER_MILE
    hours = seconds / 3600.0
    if miles > 0.2 and hours < 0.05:
        hours = miles / 55.0
    return {
        "from": origin,
        "to": destination,
        "miles": round(miles, 1),
        "minutes": hours * 60,
        "hours": hours,
    }


def build_route(current, pickup, dropoff):
    coords = ";".join(
        f"{place['lng']},{place['lat']}" for place in (current, pickup, dropoff)
    )
    response = requests.get(
        f"{OSRM_URL}/{coords}",
        params={"overview": "full", "geometries": "geojson", "steps": "false"},
        timeout=30,
    )
    if response.status_code != 200:
        raise RoutingError("Could not calculate a driving route for those locations.")
    payload = response.json()
    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise RoutingError("No driving route found. Try more specific US city names.")

    route = payload["routes"][0]
    osrm_legs = route.get("legs") or []
    if len(osrm_legs) < 2:
        raise RoutingError("Route is missing pickup or dropoff legs.")

    geometry = route["geometry"]
    coordinates = geometry.get("coordinates") or []
    to_pickup = _leg_from_osrm(osrm_legs[0], current, pickup)
    to_dropoff = _leg_from_osrm(osrm_legs[1], pickup, dropoff)

    total_miles = to_pickup["miles"] + to_dropoff["miles"]
    pickup_fraction = 0 if total_miles == 0 else to_pickup["miles"] / total_miles
    split_index = max(1, int(len(coordinates) * pickup_fraction))
    pickup_coords = coordinates[: split_index + 1] or coordinates[:1]
    dropoff_coords = coordinates[split_index:] or coordinates[-1:]

    to_pickup["coordinates"] = pickup_coords
    to_dropoff["coordinates"] = dropoff_coords

    return {
        "geometry": geometry,
        "legs": [to_pickup, to_dropoff],
        "total_miles": round(total_miles, 1),
        "total_drive_hours": round(to_pickup["hours"] + to_dropoff["hours"], 2),
    }
