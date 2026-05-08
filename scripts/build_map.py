#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""
Build a map of places from Overture Maps within European municipal boundaries.

Search cities, pick categories, fetch places from Overture Maps
and save the result as a standalone HTML map.
"""

from __future__ import annotations

import csv
import json
import os
import platform
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

import duckdb

from categories import (
    build_color_map,
    get_category_color,
    load_categories,
    select_category_groups,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).parent
BASE_DIR = SCRIPTS_DIR.parent
DATA_DIR = SCRIPTS_DIR / "data"
INPUT_DIR = BASE_DIR / "input"
MAP_DIR = BASE_DIR / "output"
TEMPLATE_PATH = SCRIPTS_DIR / "template.html"
CATEGORIES_FILE = INPUT_DIR / "categories.txt"

DATA_DIR.mkdir(exist_ok=True)
MAP_DIR.mkdir(exist_ok=True)

# Eurostat GISCO LAU 2024, EPSG:4326.
BOUNDARIES_URL = (
    "https://gisco-services.ec.europa.eu/distribution/v2/lau/geojson/"
    "LAU_RG_01M_2024_4326.geojson"
)
BOUNDARIES_CACHE = DATA_DIR / "boundaries_cache.geojson"
BOUNDARIES_INDEX = DATA_DIR / "boundaries_index.csv"

# Eurostat GISCO country boundaries, EPSG:4326.
COUNTRIES_URL = (
    "https://gisco-services.ec.europa.eu/distribution/v2/countries/geojson/"
    "CNTR_RG_01M_2024_4326.geojson"
)
COUNTRIES_CACHE = DATA_DIR / "countries_cache.geojson"
COUNTRIES_INDEX = DATA_DIR / "countries_index.csv"

OVERTURE_RELEASE_DEFAULT = "2026-04-15.0"
OVERTURE_STAC_URL = "https://stac.overturemaps.org/catalog.json"


def detect_latest_overture_release() -> str | None:
    """Query the Overture STAC catalog for the latest release."""
    import re
    try:
        req = urllib.request.Request(
            OVERTURE_STAC_URL,
            headers={"User-Agent": "overture-eu-mapper"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        pattern = re.compile(r"\d{4}-\d{2}-\d{2}\.\d+")
        releases = []
        for link in data.get("links", []):
            m = pattern.search(link.get("href", ""))
            if m:
                releases.append(m.group())
        if releases:
            releases.sort(reverse=True)
            return releases[0]
    except Exception:
        pass
    return None


def select_overture_release() -> str:
    """Show the latest Overture release. User confirms or overrides."""
    latest = detect_latest_overture_release()
    default = latest or OVERTURE_RELEASE_DEFAULT

    print(f"\n  Default Overture Maps version: {default}")
    choice = input(f"  Press ENTER to use default, or type a different version: ").strip()
    return choice if choice else default


# ---------------------------------------------------------------------------
# Boundaries (Eurostat GISCO LAU + countries)
# ---------------------------------------------------------------------------

# European country names for search (ISO 3166-1 alpha-2 codes used by GISCO).
COUNTRY_NAMES: dict[str, str] = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria",
    "CH": "Switzerland", "CY": "Cyprus", "CZ": "Czechia",
    "DE": "Germany", "DK": "Denmark", "EE": "Estonia",
    "EL": "Greece", "ES": "Spain", "FI": "Finland",
    "FR": "France", "HR": "Croatia", "HU": "Hungary",
    "IE": "Ireland", "IS": "Iceland", "IT": "Italy",
    "LI": "Liechtenstein", "LT": "Lithuania", "LU": "Luxembourg",
    "LV": "Latvia", "ME": "Montenegro", "MK": "North Macedonia",
    "MT": "Malta", "NL": "Netherlands", "NO": "Norway",
    "PL": "Poland", "PT": "Portugal", "RO": "Romania",
    "RS": "Serbia", "SE": "Sweden", "SI": "Slovenia",
    "SK": "Slovakia", "TR": "Turkey", "UK": "United Kingdom",
    "AL": "Albania", "BA": "Bosnia and Herzegovina",
    "XK": "Kosovo",
}


def ensure_boundaries_cache() -> None:
    """Download the boundary file if not already cached locally."""
    if BOUNDARIES_CACHE.exists():
        return
    print("  Downloading boundaries (first run only)")
    print(f"  Source: {BOUNDARIES_URL}")
    print()
    urllib.request.urlretrieve(BOUNDARIES_URL, BOUNDARIES_CACHE)
    print("  Done.")
    print()


def ensure_countries_cache() -> None:
    """Download the country boundaries file if not already cached locally."""
    if COUNTRIES_CACHE.exists():
        return
    print("  Downloading country boundaries (first run only)")
    urllib.request.urlretrieve(COUNTRIES_URL, COUNTRIES_CACHE)
    print("  Done.")
    print()


def ensure_boundaries_index() -> None:
    """Build a lightweight index (GISCO_ID, LAU_NAME, CNTR_CODE) for fast lookup."""
    if BOUNDARIES_INDEX.exists():
        return
    ensure_boundaries_cache()
    print("  Building search index ...")
    con = duckdb.connect()
    con.install_extension("spatial")
    con.load_extension("spatial")
    con.execute(f"""
        COPY (
            SELECT GISCO_ID, LAU_NAME, CNTR_CODE
            FROM ST_Read('{BOUNDARIES_CACHE.as_posix()}')
            ORDER BY CNTR_CODE, LAU_NAME
        ) TO '{BOUNDARIES_INDEX.as_posix()}' (HEADER, DELIMITER ',');
    """)
    con.close()
    print("  Search index ready.")
    print()


def load_boundaries_index() -> list[dict]:
    """Load the search index into memory."""
    ensure_boundaries_index()
    rows: list[dict] = []
    with open(BOUNDARIES_INDEX, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


# ---------------------------------------------------------------------------
# Search (cities + countries)
# ---------------------------------------------------------------------------


def _try_import_terminal_menu():
    try:
        from simple_term_menu import TerminalMenu
        return TerminalMenu
    except Exception:
        return None


def _strip_accents(s: str) -> str:
    """Strip diacritics for broader matching."""
    import unicodedata
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)
    )


def _search_countries(query: str) -> list[dict]:
    """Search country names and codes, case-insensitive."""
    q = _strip_accents(query.strip().lower())
    if not q:
        return []
    results = []
    for code, name in COUNTRY_NAMES.items():
        if q in _strip_accents(name.lower()) or q == code.lower():
            results.append({
                "GISCO_ID": f"CNTR_{code}",
                "LAU_NAME": name,
                "CNTR_CODE": code,
                "_is_country": True,
            })
    results.sort(key=lambda r: r["LAU_NAME"])
    return results


def search_places(index: list[dict], query: str, limit: int = 20) -> list[dict]:
    """Search cities and countries, accent- and case-insensitive."""
    q = _strip_accents(query.strip().lower())
    if not q:
        return []

    # Countries first.
    countries = _search_countries(query)

    # Then cities.
    cities = [r for r in index if q in _strip_accents(r["LAU_NAME"].lower())]
    cities.sort(key=lambda r: (
        not _strip_accents(r["LAU_NAME"].lower()).startswith(q),
        r["LAU_NAME"],
    ))

    return countries + cities[:limit]


def select_places(index: list[dict]) -> list[dict]:
    """Search and select cities or countries in a loop."""
    TerminalMenu = _try_import_terminal_menu()
    selected: list[dict] = []

    print()
    print("  Select cities or countries")
    print("  Search by name. Repeat to add more.")
    print("  Press ENTER with no text when done.")
    print()

    while True:
        query = input("  Search (ENTER = done): ").strip()
        if not query:
            if not selected:
                print("  Select at least one city or country.")
                continue
            break

        matches = search_places(index, query)
        if not matches:
            print(f"  No matches for '{query}'.\n")
            continue

        labels = []
        for r in matches:
            if r.get("_is_country"):
                labels.append(f"{r['LAU_NAME']} (country)")
            else:
                labels.append(f"{r['LAU_NAME']} ({r['CNTR_CODE']})")

        if TerminalMenu:
            menu = TerminalMenu(
                labels,
                multi_select=True,
                show_multi_select_hint=True,
                multi_select_select_on_accept=False,
                title="  Select (SPACE = toggle, ENTER = confirm):",
            )
            sel = menu.show()
            if sel is None:
                indices = []
            elif isinstance(sel, int):
                indices = [sel]
            else:
                indices = list(sel)
        else:
            print("  Matches:")
            for i, label in enumerate(labels, 1):
                print(f"    {i}. {label}")
            raw = input("  Enter numbers (e.g. 1,3): ").strip()
            indices = []
            for part in raw.split(","):
                part = part.strip()
                if part.isdigit():
                    idx = int(part) - 1
                    if 0 <= idx < len(matches):
                        indices.append(idx)

        for i in indices:
            row = matches[i]
            if row["GISCO_ID"] not in {s["GISCO_ID"] for s in selected}:
                selected.append(row)
                if row.get("_is_country"):
                    print(f"  + {row['LAU_NAME']} (country)")
                else:
                    print(f"  + {row['LAU_NAME']} ({row['CNTR_CODE']})")

        print(f"\n  Selected so far: {len(selected)}")
        print()

    print()
    print("  Selected:")
    for s in selected:
        if s.get("_is_country"):
            print(f"    {s['LAU_NAME']} (country)")
        else:
            print(f"    {s['LAU_NAME']} ({s['CNTR_CODE']})")
    print()
    return selected


# ---------------------------------------------------------------------------
# Fetch places from Overture Maps
# ---------------------------------------------------------------------------


def query_overture(
    selected_places: list[dict],
    category_slugs: list[str],
    groups: dict[str, list[str]],
    overture_release: str = OVERTURE_RELEASE_DEFAULT,
) -> tuple[dict, dict]:
    """Fetch Overture Places within selected boundaries via DuckDB.

    Return (places_geojson, boundaries_geojson).
    """
    cities = [p for p in selected_places if not p.get("_is_country")]
    countries = [p for p in selected_places if p.get("_is_country")]
    cat_list_sql = ", ".join(f"'{c}'" for c in category_slugs)

    print("  Building map (this may take a few minutes) ...")
    print(f"    Places:     {len(selected_places)}")
    print(f"    Categories: {len(category_slugs)}")
    print()
    t0 = time.time()

    con = duckdb.connect()
    con.install_extension("httpfs")
    con.install_extension("spatial")
    con.load_extension("httpfs")
    con.load_extension("spatial")

    con.execute("SET s3_region='us-west-2';")
    con.execute("SET threads TO 4;")

    # Load boundaries: cities from LAU file, countries from country file.
    boundary_parts = []
    if cities:
        city_ids = ", ".join(f"'{c['GISCO_ID']}'" for c in cities)
        boundary_parts.append(f"""
            SELECT LAU_NAME AS city, geom
            FROM ST_Read('{BOUNDARIES_CACHE.as_posix()}')
            WHERE GISCO_ID IN ({city_ids})
        """)
    if countries:
        ensure_countries_cache()
        cntr_codes = ", ".join(f"'{c['CNTR_CODE']}'" for c in countries)
        boundary_parts.append(f"""
            SELECT NAME_ENGL AS city, geom
            FROM ST_Read('{COUNTRIES_CACHE.as_posix()}')
            WHERE CNTR_ID IN ({cntr_codes})
        """)
    con.execute(f"""
        CREATE TABLE boundaries AS
        {" UNION ALL ".join(boundary_parts)};
    """)

    # Compute per-city bounding boxes with margin. Using individual boxes
    # instead of one combined box avoids downloading data for the entire
    # region between far-apart cities (e.g. Paris and Stockholm).
    parquet_url = (
        f"s3://overturemaps-us-west-2/release/{overture_release}"
        f"/theme=places/type=place/*.parquet"
    )

    city_bboxes = con.execute("""
        SELECT city,
            ST_XMin(geom) - 0.1 AS xmin,
            ST_YMin(geom) - 0.1 AS ymin,
            ST_XMax(geom) + 0.1 AS xmax,
            ST_YMax(geom) + 0.1 AS ymax
        FROM boundaries;
    """).fetchall()

    parts = []
    for city, xmin, ymin, xmax, ymax in city_bboxes:
        print(f"    {city} ...")
        parts.append(f"""
            SELECT geometry, names, categories, websites
            FROM read_parquet('{parquet_url}')
            WHERE bbox.xmin >= {xmin}
              AND bbox.xmax <= {xmax}
              AND bbox.ymin >= {ymin}
              AND bbox.ymax <= {ymax}
              AND categories.primary IN ({cat_list_sql})
        """)

    con.execute(f"""
        CREATE TABLE places AS
        {" UNION ALL ".join(parts)};
    """)

    # Spatial join: keep only places that fall within a city boundary.
    con.execute("""
        CREATE TABLE result AS
        SELECT
            ST_AsGeoJSON(p.geometry) AS geojson_geom,
            p.names.primary AS name,
            p.categories.primary AS category,
            p.websites[1] AS website,
            b.city
        FROM places p
        JOIN boundaries b ON ST_Within(
            ST_GeomFromWKB(ST_AsWKB(p.geometry)),
            ST_GeomFromWKB(ST_AsWKB(b.geom))
        );
    """)

    rows = con.execute("SELECT * FROM result").fetchall()
    columns = ["geojson_geom", "name", "category", "website", "city"]

    elapsed = time.time() - t0
    print(f"    {len(rows)} places found in {elapsed:.0f}s.")
    print()

    # Build GeoJSON: places.
    all_cats = sorted({dict(zip(columns, r))["category"] for r in rows if dict(zip(columns, r))["category"]})
    build_color_map(all_cats)

    features = []
    for row in rows:
        rec = dict(zip(columns, row))
        geom = json.loads(rec["geojson_geom"])
        category = rec["category"] or "unknown"
        props = {
            "name": rec["name"] or "Unnamed",
            "category": category,
            "city": rec["city"] or "",
            "color": get_category_color(category, groups),
        }
        if rec["website"]:
            props["website"] = rec["website"]
        features.append({
            "type": "Feature",
            "geometry": geom,
            "properties": props,
        })

    places_fc = {"type": "FeatureCollection", "features": features}

    # Build GeoJSON: city boundaries.
    boundary_rows = con.execute(
        "SELECT city, ST_AsGeoJSON(geom) AS geojson_geom FROM boundaries"
    ).fetchall()

    boundary_features = []
    for city_name, geom_json in boundary_rows:
        boundary_features.append({
            "type": "Feature",
            "geometry": json.loads(geom_json),
            "properties": {"city": city_name},
        })

    boundary_fc = {"type": "FeatureCollection", "features": boundary_features}

    con.close()
    return places_fc, boundary_fc


# ---------------------------------------------------------------------------
# Load categories from file
# ---------------------------------------------------------------------------


def load_categories_file() -> list[str] | None:
    """Read category slugs from input/categories.txt.

    Return a list of slugs, or None if the file is missing or empty.
    """
    if not CATEGORIES_FILE.exists():
        return None
    slugs = []
    with open(CATEGORIES_FILE, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                slugs.append(line)
    return slugs if slugs else None


# ---------------------------------------------------------------------------
# Import from CSV
# ---------------------------------------------------------------------------


def find_input_csv() -> Path | None:
    """Return the most recently modified CSV file in input/, or None."""
    if not INPUT_DIR.is_dir():
        return None
    csvs = list(INPUT_DIR.glob("*.csv"))
    if not csvs:
        return None
    return max(csvs, key=lambda p: p.stat().st_mtime)


def load_csv_as_geojson(csv_path: Path, groups: dict[str, list[str]]) -> dict:
    """Read an exported CSV and return a places FeatureCollection."""
    print(f"  Loading: {csv_path.name}")

    # First pass: read all rows and collect categories.
    raw_rows = []
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat = row.get("lat", "").strip()
            lon = row.get("lon", "").strip()
            if not lat or not lon:
                continue
            raw_rows.append(row)

    all_cats = sorted({
        (r.get("category", "").strip() or "unknown") for r in raw_rows
    })
    build_color_map(all_cats)

    # Second pass: build features with colors.
    features = []
    for row in raw_rows:
        category = row.get("category", "unknown").strip() or "unknown"
        props = {
            "name": row.get("name", "Unnamed").strip() or "Unnamed",
            "category": category,
            "city": row.get("city", "").strip(),
            "color": get_category_color(category, groups),
        }
        website = row.get("website", "").strip()
        if website:
            props["website"] = website
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [float(row["lon"].strip()), float(row["lat"].strip())],
            },
            "properties": props,
            })
    print(f"  {len(features)} places loaded.")
    print()
    return {"type": "FeatureCollection", "features": features}


def lookup_boundaries_for_cities(city_names: list[str]) -> dict:
    """Look up boundary geometries for city names found in a CSV.

    For each city name, searches the boundary index. If multiple matches
    are found (same name in different countries), the user picks the
    correct one. Returns a FeatureCollection with boundary polygons.
    """
    ensure_boundaries_cache()
    index = load_boundaries_index()

    print("  Matching cities to boundaries ...")
    print()

    gisco_ids = []
    for name in city_names:
        norm_name = _strip_accents(name.lower())
        matches = [
            r for r in index
            if _strip_accents(r["LAU_NAME"].lower()) == norm_name
        ]

        if not matches:
            print(f"    {name}: no boundary found, skipping.")
            continue

        if len(matches) == 1:
            row = matches[0]
            gisco_ids.append(row["GISCO_ID"])
            print(f"    {name} ({row['CNTR_CODE']})")
            continue

        # Multiple matches — let the user choose.
        print(f"    Multiple matches for '{name}':")
        labels = [
            f"{r['LAU_NAME']} ({r['CNTR_CODE']})" for r in matches
        ]
        for i, label in enumerate(labels, 1):
            print(f"      {i}. {label}")
        raw = input("    Enter number (or ENTER to skip): ").strip()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(matches):
                row = matches[idx]
                gisco_ids.append(row["GISCO_ID"])
                print(f"    Selected: {row['LAU_NAME']} ({row['CNTR_CODE']})")
            else:
                print(f"    Invalid choice, skipping {name}.")
        else:
            print(f"    Skipping {name}.")

    print()

    if not gisco_ids:
        return {"type": "FeatureCollection", "features": []}

    id_list_sql = ", ".join(f"'{gid}'" for gid in gisco_ids)

    print(f"  Loading boundaries for {len(gisco_ids)} cities ...")
    con = duckdb.connect()
    con.install_extension("spatial")
    con.load_extension("spatial")

    rows = con.execute(f"""
        SELECT LAU_NAME AS city, ST_AsGeoJSON(geom) AS geojson_geom
        FROM ST_Read('{BOUNDARIES_CACHE.as_posix()}')
        WHERE GISCO_ID IN ({id_list_sql});
    """).fetchall()
    con.close()

    features = []
    for city_name, geom_json in rows:
        features.append({
            "type": "Feature",
            "geometry": json.loads(geom_json),
            "properties": {"city": city_name},
        })

    print(f"  {len(features)} boundaries loaded.")
    print()
    return {"type": "FeatureCollection", "features": features}


# ---------------------------------------------------------------------------
# Generate HTML
# ---------------------------------------------------------------------------


def generate_html(
    places_fc: dict,
    boundary_fc: dict,
    title: str,
) -> Path:
    """Inject data into the template and write to output/."""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    html = template.replace("__GEOJSON_DATA__", json.dumps(places_fc, ensure_ascii=False))
    html = html.replace("__BOUNDARY_DATA__", json.dumps(boundary_fc, ensure_ascii=False))
    html = html.replace("__TITLE__", title)
    html = html.replace("__TIMESTAMP__", timestamp)

    out_path = MAP_DIR / f"map-{timestamp}.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


def open_in_browser(path: Path) -> None:
    """Open the file in the default browser."""
    if platform.system() == "Darwin":
        subprocess.run(["open", str(path)])
    elif platform.system() == "Linux":
        subprocess.run(["xdg-open", str(path)])
    elif platform.system() == "Windows":
        os.startfile(str(path))


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------


def main() -> None:
    print()
    print("  Map Builder")
    print("  -----------")
    print()

    groups = load_categories(DATA_DIR)

    # Check for a CSV file in input/.
    csv_path = find_input_csv()

    if csv_path:
        # CSV import mode — skip city/category selection.
        print(f"  Found input file: {csv_path.name}")
        print()
        places_fc = load_csv_as_geojson(csv_path, groups)
        cities = sorted({
            f["properties"]["city"]
            for f in places_fc["features"]
            if f["properties"].get("city")
        })
        boundary_fc = lookup_boundaries_for_cities(cities)
        title = ", ".join(cities) if cities else csv_path.stem
    else:
        # Interactive mode — search cities/countries, pick categories, query Overture.
        ensure_boundaries_cache()

        index = load_boundaries_index()
        selected_places = select_places(index)

        category_slugs = load_categories_file()
        if category_slugs:
            print(f"  Loaded {len(category_slugs)} categories from {CATEGORIES_FILE.name}")
        else:
            category_slugs = select_category_groups(groups)
            if not category_slugs:
                print("  No categories selected.")
                sys.exit(0)

        print(f"\n  {len(category_slugs)} categories selected.\n")

        overture_release = select_overture_release()

        places_fc, boundary_fc = query_overture(
            selected_places, category_slugs, groups, overture_release,
        )
        title = ", ".join(c["LAU_NAME"] for c in selected_places)

    if not places_fc["features"]:
        print("  No places found.")
        sys.exit(0)

    # Generate map.
    out_path = generate_html(places_fc, boundary_fc, title)
    print(f"  Map saved: {out_path}")
    print(f"  {len(places_fc['features'])} places.")
    print()

    open_in_browser(out_path)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrupted.")
        sys.exit(0)
    except Exception as e:
        print(f"\n  Error: {e}", file=sys.stderr)
        sys.exit(1)
