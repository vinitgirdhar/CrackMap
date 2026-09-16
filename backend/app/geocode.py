"""Real-world geocoding via OpenStreetMap Nominatim.

Server-side rather than browser-side so we can honour Nominatim's usage policy
in one place: an identifying User-Agent, at most one request per second, and a
cache so panning around the same spot does not re-query.

Stdlib only — no new dependency for two HTTP GETs.
"""

import json
import threading
import time
import urllib.parse
import urllib.request
from functools import lru_cache
from typing import Any, Dict, List, Optional

NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
USER_AGENT = "CrackMap/1.0 (civic road-damage inspection pipeline)"
TIMEOUT_SECONDS = 8.0
MIN_INTERVAL_SECONDS = 1.1  # Nominatim policy: max 1 request/second.

_rate_lock = threading.Lock()
_last_request_at = 0.0


class GeocodeError(RuntimeError):
    pass


def _get(path: str, params: Dict[str, Any]) -> Any:
    global _last_request_at

    # ponytail: one global lock. Fine for a single-process demo backend; move to
    # a token bucket per worker if this ever runs multi-process.
    with _rate_lock:
        wait = MIN_INTERVAL_SECONDS - (time.time() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.time()

    url = f"{NOMINATIM_BASE}{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # network down, rate limited, malformed payload
        raise GeocodeError(f"Nominatim request failed: {exc}") from exc


def _road_label(address: Dict[str, Any]) -> str:
    """Best available street-level name, falling back down the address tree."""
    for key in ("road", "pedestrian", "footway", "neighbourhood", "suburb", "village", "town", "city"):
        value = address.get(key)
        if value:
            return value
    return "Unnamed road"


def _area_label(address: Dict[str, Any]) -> str:
    for key in ("suburb", "neighbourhood", "city_district", "county", "town", "city"):
        value = address.get(key)
        if value:
            return value
    return ""


def _shape(payload: Dict[str, Any]) -> Dict[str, Any]:
    address = payload.get("address") or {}
    road = _road_label(address)
    area = _area_label(address)
    return {
        "road_name": f"{road}, {area}" if area and area != road else road,
        "road": road,
        "ward": area,
        "city": address.get("city") or address.get("town") or address.get("state_district") or "",
        "state": address.get("state") or "",
        "postcode": address.get("postcode") or "",
        "country": address.get("country") or "",
        "display_name": payload.get("display_name") or "",
        "osm_road_type": payload.get("type") or "",
        "lat": float(payload["lat"]) if payload.get("lat") else None,
        "lon": float(payload["lon"]) if payload.get("lon") else None,
    }


# Rounded to ~11 m so repeated lookups from a jittery GPS fix share a cache slot.
@lru_cache(maxsize=512)
def _reverse_cached(lat_key: float, lon_key: float) -> Dict[str, Any]:
    payload = _get(
        "/reverse",
        {"lat": lat_key, "lon": lon_key, "format": "jsonv2", "zoom": 17, "addressdetails": 1},
    )
    if not isinstance(payload, dict) or "address" not in payload:
        raise GeocodeError("Nominatim returned no address for this coordinate")
    return _shape(payload)


def reverse(lat: float, lon: float) -> Dict[str, Any]:
    """Coordinate -> real street name, ward, city and OSM road classification."""
    return _reverse_cached(round(lat, 4), round(lon, 4))


@lru_cache(maxsize=256)
def _search_cached(query: str, limit: int) -> List[Dict[str, Any]]:
    payload = _get(
        "/search", {"q": query, "format": "jsonv2", "addressdetails": 1, "limit": limit}
    )
    if not isinstance(payload, list):
        raise GeocodeError("Nominatim returned an unexpected search payload")
    return [_shape(item) for item in payload]


def search(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Place / road name -> candidate coordinates."""
    cleaned = query.strip()
    if not cleaned:
        return []
    return _search_cached(cleaned, max(1, min(10, limit)))


def demo_self_check() -> None:
    """Offline check of the payload shaping; the network calls are not exercised."""
    shaped = _shape(
        {
            "lat": "19.0596",
            "lon": "72.8295",
            "type": "secondary",
            "display_name": "Hill Road, Bandra West, Mumbai, Maharashtra, 400050, India",
            "address": {
                "road": "Hill Road",
                "suburb": "Bandra West",
                "city": "Mumbai",
                "state": "Maharashtra",
                "postcode": "400050",
                "country": "India",
            },
        }
    )
    assert shaped["road_name"] == "Hill Road, Bandra West", shaped
    assert shaped["osm_road_type"] == "secondary"
    assert shaped["lat"] == 19.0596

    bare = _shape({"address": {"city": "Mumbai"}})
    assert bare["road_name"] == "Mumbai", bare
    assert _shape({"address": {}})["road_name"] == "Unnamed road"
    print("geocode.py self-check OK")


if __name__ == "__main__":
    demo_self_check()
