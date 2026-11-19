"""Point-in-polygon lookup for Kraków's districts (dzielnice).

Polygons come from OSM boundary relations (fetch_osm.py -> osm_districts.json)
in the form: polygons = [ [outer_ring, hole_ring, ...], ... ], each ring a
list of [lon, lat] points.
"""
from __future__ import annotations


def point_in_ring(lon: float, lat: float, ring) -> bool:
    """Ray casting. Points exactly on an edge may fall either way."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat):
            x_cross = xi + (lat - yi) * (xj - xi) / (yj - yi)
            if lon < x_cross:
                inside = not inside
        j = i
    return inside


def point_in_polygons(lon: float, lat: float, polygons) -> bool:
    for rings in polygons:
        if rings and point_in_ring(lon, lat, rings[0]) and not any(
                point_in_ring(lon, lat, hole) for hole in rings[1:]):
            return True
    return False


class DistrictIndex:
    """Find which district a point lies in. Bounding boxes first, so the
    ~71k address lookups stay fast."""

    def __init__(self, districts):
        self.items = []
        for d in districts:
            pts = [p for rings in d["polygons"] for p in rings[0]]
            if not pts:
                continue
            bbox = (min(p[0] for p in pts), min(p[1] for p in pts),
                    max(p[0] for p in pts), max(p[1] for p in pts))
            self.items.append((bbox, d))

    def find(self, lat: float, lon: float):
        for (x0, y0, x1, y1), d in self.items:
            if x0 <= lon <= x1 and y0 <= lat <= y1 and point_in_polygons(lon, lat, d["polygons"]):
                return d
        return None
