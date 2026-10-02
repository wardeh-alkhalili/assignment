import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from .models import Trip
from .services.geocoding import GeocodeError, geocode_many, suggest_places
from .services.hos import plan_hos
from .services.routing import RoutingError, build_route


def _error(message, status=400):
    return JsonResponse({"error": message}, status=status)


@require_GET
def health(_request):
    return JsonResponse({"ok": True, "service": "driverlog"})


@require_GET
def geocode(request):
    query = request.GET.get("q", "")
    try:
        return JsonResponse({"results": suggest_places(query)})
    except Exception:
        return _error("Location lookup failed. Try again in a moment.", 502)


@csrf_exempt
@require_http_methods(["POST"])
def plan_trip(request):
    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _error("Request body must be JSON.")

    current_q = (payload.get("current_location") or "").strip()
    pickup_q = (payload.get("pickup_location") or "").strip()
    dropoff_q = (payload.get("dropoff_location") or "").strip()
    try:
        cycle_used = float(payload.get("current_cycle_used", 0))
    except (TypeError, ValueError):
        return _error("Current cycle used must be a number of hours.")

    if not current_q or not pickup_q or not dropoff_q:
        return _error("Current, pickup, and dropoff locations are required.")
    if cycle_used < 0 or cycle_used > 70:
        return _error("Current cycle used must be between 0 and 70 hours.")

    try:
        current, pickup, dropoff = geocode_many([current_q, pickup_q, dropoff_q])
        route = build_route(current, pickup, dropoff)
        plan = plan_hos(
            route,
            {"current": current, "pickup": pickup, "dropoff": dropoff},
            cycle_used,
        )
    except GeocodeError as exc:
        return _error(str(exc))
    except RoutingError as exc:
        return _error(str(exc))
    except Exception:
        return _error("Could not plan this trip. Check the locations and try again.", 500)

    result = {
        "inputs": {
            "current_location": current_q,
            "pickup_location": pickup_q,
            "dropoff_location": dropoff_q,
            "current_cycle_used": cycle_used,
        },
        "locations": {"current": current, "pickup": pickup, "dropoff": dropoff},
        "route": {
            "geometry": route["geometry"],
            "legs": [
                {
                    "from": leg["from"]["label"],
                    "to": leg["to"]["label"],
                    "miles": leg["miles"],
                    "hours": round(leg["hours"], 2),
                }
                for leg in route["legs"]
            ],
            "stops": plan["stops"],
        },
        "summary": plan["summary"],
        "events": plan["events"],
        "timeline": plan["timeline"],
        "daily_logs": plan["daily_logs"],
    }

    Trip.objects.create(
        current_location=current_q,
        pickup_location=pickup_q,
        dropoff_location=dropoff_q,
        current_cycle_used=cycle_used,
        result=result,
    )
    return JsonResponse(result)
