# SPDX-License-Identifier: Apache-2.0
"""
Overture Maps categories: loading, caching, and interactive selection.

Fetch the official taxonomy CSV on first run and cache it locally.
Group categories by top-level group so the user can select broadly
and optionally drill down.
"""

from __future__ import annotations

import csv
import os
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CATEGORIES_URL = (
    "https://raw.githubusercontent.com/OvertureMaps/schema/main/"
    "docs/schema/concepts/by-theme/places/overture_categories.csv"
)

# Display names per top-level group.
GROUP_DISPLAY_NAMES: dict[str, str] = {
    "accommodation": "Accommodation",
    "active_life": "Active Life",
    "arts_and_entertainment": "Arts & Entertainment",
    "attractions_and_activities": "Attractions & Activities",
    "automotive": "Automotive",
    "beauty_and_spa": "Beauty & Spa",
    "business_to_business": "Business to Business",
    "eat_and_drink": "Eat & Drink",
    "education": "Education",
    "financial_service": "Financial Service",
    "health_and_medical": "Health & Medical",
    "home_service": "Home Service",
    "mass_media": "Mass Media",
    "pets": "Pets",
    "private_establishments_and_corporates": "Private Establishments",
    "professional_services": "Professional Services",
    "public_service_and_government": "Public Service & Government",
    "real_estate": "Real Estate",
    "religious_organization": "Religious Organization",
    "retail": "Retail",
    "structure_and_geography": "Structure & Geography",
    "travel": "Travel",
}

# One color per top-level group. Used for map markers.
GROUP_COLORS: dict[str, str] = {
    "accommodation": "#1f77b4",
    "active_life": "#ff7f0e",
    "arts_and_entertainment": "#2ca02c",
    "attractions_and_activities": "#d62728",
    "automotive": "#9467bd",
    "beauty_and_spa": "#e377c2",
    "business_to_business": "#7f7f7f",
    "eat_and_drink": "#8c564b",
    "education": "#17becf",
    "financial_service": "#bcbd22",
    "health_and_medical": "#ff9896",
    "home_service": "#aec7e8",
    "mass_media": "#ffbb78",
    "pets": "#98df8a",
    "private_establishments_and_corporates": "#c5b0d5",
    "professional_services": "#c49c94",
    "public_service_and_government": "#f7b6d2",
    "real_estate": "#dbdb8d",
    "religious_organization": "#9edae5",
    "retail": "#843c39",
    "structure_and_geography": "#7b4173",
    "travel": "#637939",
}

# ---------------------------------------------------------------------------
# Loading and caching
# ---------------------------------------------------------------------------

def _download_categories(cache_path: Path) -> None:
    """Download the Overture taxonomy CSV."""
    print("  Fetching Overture categories ...")
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(CATEGORIES_URL, cache_path)


def load_categories(cache_dir: Path) -> dict[str, list[str]]:
    """Return {top_group: [slug, ...]} from cached or downloaded CSV.

    Each top-level group contains all descendant slugs, sorted alphabetically.
    """
    cache_path = cache_dir / "overture_categories.csv"
    if not cache_path.exists():
        _download_categories(cache_path)

    groups: dict[str, list[str]] = {}
    with open(cache_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=";")
        next(reader, None)
        for row in reader:
            if len(row) < 2:
                continue
            slug = row[0].strip()
            taxonomy_raw = row[1].strip().strip("[]")
            parts = [p.strip() for p in taxonomy_raw.split(",") if p.strip()]
            if not parts:
                continue
            top = parts[0]
            groups.setdefault(top, [])
            if slug not in groups[top]:
                groups[top].append(slug)

    for g in groups:
        groups[g].sort()
    return groups


def get_level2_categories(cache_dir: Path, top_group: str) -> list[str]:
    """Return direct children (level 2) under a top-level group."""
    cache_path = cache_dir / "overture_categories.csv"
    level2: list[str] = []
    with open(cache_path, encoding="utf-8-sig") as f:
        reader = csv.reader(f, delimiter=";")
        next(reader, None)
        for row in reader:
            if len(row) < 2:
                continue
            slug = row[0].strip()
            taxonomy_raw = row[1].strip().strip("[]")
            parts = [p.strip() for p in taxonomy_raw.split(",") if p.strip()]
            if len(parts) == 2 and parts[0] == top_group:
                level2.append(slug)
    level2.sort()
    return level2


# ---------------------------------------------------------------------------
# Color mapping
# ---------------------------------------------------------------------------

_category_to_group_cache: dict[str, str] = {}


def _build_cat_to_group(groups: dict[str, list[str]]) -> None:
    for group, slugs in groups.items():
        for slug in slugs:
            _category_to_group_cache[slug] = group


def get_group_for_category(cat: str, groups: dict[str, list[str]]) -> str:
    """Return the top-level group for a category."""
    if not _category_to_group_cache:
        _build_cat_to_group(groups)
    return _category_to_group_cache.get(cat, "")


def _hsl_to_hex(h: float, s: float, l: float) -> str:
    """Convert HSL (h: 0-360, s/l: 0-100) to hex color."""
    s_f = s / 100
    l_f = l / 100
    c = (1 - abs(2 * l_f - 1)) * s_f
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l_f - c / 2
    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x
    ri = int((r + m) * 255)
    gi = int((g + m) * 255)
    bi = int((b + m) * 255)
    return f"#{ri:02x}{gi:02x}{bi:02x}"


_color_map: dict[str, str] = {}


def build_color_map(categories: list[str]) -> None:
    """Assign maximally spread colors to a list of categories.

    Call once after data is loaded, before generating the map.
    """
    _color_map.clear()
    n = len(categories)
    for i, cat in enumerate(sorted(categories)):
        hue = (i * 360 / n) % 360
        _color_map[cat] = _hsl_to_hex(hue, 70, 45)


def get_category_color(cat: str, groups: dict[str, list[str]]) -> str:
    """Return color for a category. Requires build_color_map() first."""
    return _color_map.get(cat, "#999999")


# ---------------------------------------------------------------------------
# Interactive selection
# ---------------------------------------------------------------------------

def _try_import_terminal_menu():
    try:
        from simple_term_menu import TerminalMenu
        return TerminalMenu
    except Exception:
        return None


def _fallback_multi_select(options: list[str], prompt: str) -> list[int]:
    """Numbered list fallback when simple-term-menu is not installed."""
    print(prompt)
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    print()
    raw = input("  Enter numbers, comma-separated (e.g. 1,3,5): ").strip()
    if not raw:
        return []
    indices = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(options):
                indices.append(idx)
    return indices


def select_category_groups(groups: dict[str, list[str]]) -> list[str]:
    """Select category groups interactively.

    Return a flat list of all selected category slugs.
    """
    TerminalMenu = _try_import_terminal_menu()
    sorted_keys = sorted(groups.keys())
    labels = [
        f"{GROUP_DISPLAY_NAMES.get(k, k)}  ({len(groups[k])} categories)"
        for k in sorted_keys
    ]

    print()
    print("  Select category groups")
    print(f"  Full list: {CATEGORIES_URL}")
    print("  Arrow keys = move, SPACE = toggle, ENTER = confirm.")
    print()

    if TerminalMenu:
        menu = TerminalMenu(
            labels,
            multi_select=True,
            show_multi_select_hint=True,
            multi_select_select_on_accept=False,
            title="  Category groups (SPACE + ENTER):",
        )
        selection = menu.show()
        if selection is None:
            selected_indices = []
        elif isinstance(selection, int):
            selected_indices = [selection]
        else:
            selected_indices = list(selection)
    else:
        selected_indices = _fallback_multi_select(labels, "  Category groups:")

    if not selected_indices:
        print("  No groups selected.")
        return []

    selected_keys = [sorted_keys[i] for i in selected_indices]
    print(f"\n  Selected: {', '.join(GROUP_DISPLAY_NAMES.get(k, k) for k in selected_keys)}")

    answer = input("\n  Select individual categories? (y/N): ").strip().lower()
    if answer in ("y", "yes"):
        return _drill_down(groups, selected_keys, TerminalMenu)

    all_slugs: list[str] = []
    for k in selected_keys:
        all_slugs.extend(groups[k])
    return sorted(set(all_slugs))


def _drill_down(
    groups: dict[str, list[str]],
    selected_keys: list[str],
    TerminalMenu,
) -> list[str]:
    """Select individual categories within each chosen group."""
    all_slugs: list[str] = []

    for key in selected_keys:
        slugs = groups[key]
        display_name = GROUP_DISPLAY_NAMES.get(key, key)
        print(f"\n  {display_name}")

        labels = [s.replace("_", " ").title() for s in slugs]

        if TerminalMenu:
            menu = TerminalMenu(
                labels,
                multi_select=True,
                show_multi_select_hint=True,
                multi_select_select_on_accept=False,
                title=f"  {display_name} (MELLANSLAG + ENTER):",
            )
            selection = menu.show()
            if selection is None:
                indices = []
            elif isinstance(selection, int):
                indices = [selection]
            else:
                indices = list(selection)
        else:
            indices = _fallback_multi_select(labels, f"  {display_name}:")

        for i in indices:
            all_slugs.append(slugs[i])

    return sorted(set(all_slugs))
