import time

import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "DriverLog/1.0 (FMCSA HOS trip planner assessment)"


class GeocodeError(ValueError):
    pass


def _request(query, limit=1):
    response = requests.get(
        NOMINATIM_URL,
        params={
            "q": query,
            "format": "json",
            "limit": limit,
            "addressdetails": 1,
        },
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def geocode_place(query):
    query = (query or "").strip()
    if not query:
        raise GeocodeError("Location is required.")
    data = _request(query, limit=1)
    if not data:
        raise GeocodeError(f'Could not find "{query}". Try a city and state.')
    hit = data[0]
    return {
        "label": hit.get("display_name") or query,
        "query": query,
        "lat": float(hit["lat"]),
        "lng": float(hit["lon"]),
    }


def geocode_many(queries):
    results = []
    for index, query in enumerate(queries):
        results.append(geocode_place(query))
        if index < len(queries) - 1:
            time.sleep(1)
    return results


def suggest_places(query, limit=5):
    query = (query or "").strip()
    if len(query) < 3:
        return []
    data = _request(query, limit=limit)
    suggestions = []
    for hit in data:
        suggestions.append(
            {
                "label": hit.get("display_name") or query,
                "lat": float(hit["lat"]),
                "lng": float(hit["lon"]),
            }
        )
    return suggestions
