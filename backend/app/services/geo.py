"""Approximate straight-line distance. This is NOT driving or travel time and must never be presented as such."""
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0088
COORD_DECIMALS = 2  # ~1.1 km: enough to filter by region, too coarse to locate a home


def round_coord(value: float | None) -> float | None:
    return None if value is None else round(value, COORD_DECIMALS)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = radians(lat1), radians(lat2)
    a = sin((p2 - p1) / 2) ** 2 + cos(p1) * cos(p2) * sin(radians(lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(a))


def distance_km(profile, competition) -> int | None:
    """Whole kilometres between the athlete's approximate location and the venue, or None if either is unknown."""
    if profile is None or profile.approx_lat is None or profile.approx_lon is None:
        return None
    if competition.latitude is None or competition.longitude is None:
        return None
    return round(haversine_km(profile.approx_lat, profile.approx_lon, competition.latitude, competition.longitude))
