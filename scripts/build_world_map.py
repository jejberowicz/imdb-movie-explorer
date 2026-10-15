"""Build the world map of the countries page from Natural Earth (public domain).

    python scripts/build_world_map.py

Writes two files in frontend/src/features/countries/:

- world-110m.json: the country shapes at 1:110m, with coordinates rounded to 2 decimals (about 1 km).
- small-countries.json: a point for each country too small for that scale (Hong Kong, Singapore, Malta...),
  so the map can still show it as a dot.

The sources are pinned to Natural Earth 5.1.2, so running the script again gives the same files.
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

SOURCE = "https://cdn.jsdelivr.net/gh/nvkelso/natural-earth-vector@v5.1.2/geojson/"
SHAPES = SOURCE + "ne_110m_admin_0_countries.geojson"
TINY = SOURCE + "ne_50m_admin_0_tiny_countries.geojson"
UNITS = SOURCE + "ne_50m_admin_0_map_units.geojson"
TARGET = Path(__file__).resolve().parent.parent / "frontend" / "src" / "features" / "countries"
ISO_CODE = re.compile(r"[A-Z]{2}")


def download(url: str) -> dict:
    if not url.startswith("https://"):
        raise ValueError(f"not an https URL: {url}")
    with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310 (fixed https URLs)
        return json.load(response)


def code_of(properties: dict) -> str | None:
    """The ISO code of a feature; Natural Earth uses -99 when there is none (France and Norway only in ISO_A2)."""
    for key in ("ISO_A2_EH", "ISO_A2"):
        value = properties.get(key)
        if value and ISO_CODE.fullmatch(value):
            return value
    return None


def rounded(coordinates):
    if isinstance(coordinates[0], int | float):
        return [round(coordinates[0], 2), round(coordinates[1], 2)]
    return [rounded(item) for item in coordinates]


def shapes(collection: dict) -> dict:
    features = [
        {
            "type": "Feature",
            "properties": {"code": code_of(feature["properties"]) or "-99", "name": feature["properties"]["NAME"]},
            "geometry": {
                "type": feature["geometry"]["type"],
                "coordinates": rounded(feature["geometry"]["coordinates"]),
            },
        }
        for feature in collection["features"]
    ]
    return {"type": "FeatureCollection", "features": features}


def small_countries(drawn: set[str], tiny: dict, units: dict) -> list[dict]:
    """A point for each country that the 1:110m shapes leave out: the tiny-countries point if Natural Earth has
    one, otherwise the label point of its 1:50m map unit."""
    points: dict[str, dict] = {}
    for feature in tiny["features"]:
        code = code_of(feature["properties"])
        if code and code not in drawn:
            points[code] = {
                "code": code,
                "name": feature["properties"]["NAME"],
                "coordinates": rounded(feature["geometry"]["coordinates"]),
            }
    for feature in units["features"]:
        properties = feature["properties"]
        code = code_of(properties)
        if code and code not in drawn and code not in points:
            points[code] = {
                "code": code,
                "name": properties["NAME"],
                "coordinates": rounded([properties["LABEL_X"], properties["LABEL_Y"]]),
            }
    return sorted(points.values(), key=lambda point: point["code"])


def write(name: str, data) -> int:
    text = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    (TARGET / name).write_text(text, encoding="utf-8")
    return len(text.encode())


def main() -> int:
    world = shapes(download(SHAPES))
    drawn = {feature["properties"]["code"] for feature in world["features"]}
    points = small_countries(drawn, download(TINY), download(UNITS))
    print(f"world-110m.json: {len(world['features'])} shapes, {write('world-110m.json', world) // 1000} KB")
    print(f"small-countries.json: {len(points)} points, {write('small-countries.json', points) // 1000} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
