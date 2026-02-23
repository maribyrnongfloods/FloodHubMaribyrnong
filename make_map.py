"""
make_map.py  —  Plot the 13 Maribyrnong gauge stations on a B&W basemap
                with the river network in blue.
Output: gauge_map.png  (suitable for pasting into email)
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import matplotlib.lines as mlines
import matplotlib.patches as mpatches
import geopandas as gpd
import contextily as ctx
import requests
from shapely.geometry import Point, LineString, shape

# ── gauge data ────────────────────────────────────────────────────────────────
# label_offset: (x, y) in points, and optional ha (horizontal alignment)
gauges = [
    {"id": "230100A", "name": "Darraweit",                  "lat": -37.4103, "lon": 144.9023, "type": "mainstem",   "loff": (-8,  5), "ha": "right"},
    {"id": "230211A", "name": "Clarkefield",                "lat": -37.4662, "lon": 144.7440, "type": "mainstem",   "loff": ( 7,  5), "ha": "left"},
    {"id": "230104A", "name": "Sunbury (mainstem)",         "lat": -37.5833, "lon": 144.7420, "type": "mainstem",   "loff": ( 7, -12), "ha": "left"},
    {"id": "230107A", "name": "Konagaderra Ck",             "lat": -37.5285, "lon": 144.8560, "type": "mainstem",   "loff": ( 7,  5), "ha": "left"},
    {"id": "230200",  "name": "Keilor",                     "lat": -37.7277, "lon": 144.8365, "type": "mainstem",   "loff": ( 7,  5), "ha": "left"},
    {"id": "230106A", "name": "Chifley Dr (tidal\u2020)",   "lat": -37.7659, "lon": 144.8950, "type": "tidal",      "loff": (-8,  5), "ha": "right"},
    {"id": "230210",  "name": "Bullengarook",               "lat": -37.4718, "lon": 144.5243, "type": "tributary",  "loff": ( 7,  5), "ha": "left"},
    {"id": "230206",  "name": "Gisborne",                   "lat": -37.4754, "lon": 144.5724, "type": "tributary",  "loff": ( 7, -12), "ha": "left"},
    {"id": "230202",  "name": "Sunbury (Jacksons Ck)",      "lat": -37.5832, "lon": 144.7421, "type": "tributary",  "loff": (-8, -12), "ha": "right"},
    {"id": "230205",  "name": "Bulla (Deep Ck)",            "lat": -37.6314, "lon": 144.8010, "type": "tributary",  "loff": ( 7,  5), "ha": "left"},
    {"id": "230209",  "name": "Barringo",                   "lat": -37.4105, "lon": 144.6261, "type": "tributary",  "loff": ( 7,  5), "ha": "left"},
    {"id": "230213",  "name": "Mt Macedon (Turritable Ck)", "lat": -37.4189, "lon": 144.5848, "type": "tributary",  "loff": ( 7, -12), "ha": "left"},
    {"id": "230227",  "name": "Kerrie (Main Ck)",           "lat": -37.3961, "lon": 144.6604, "type": "tributary",  "loff": ( 7,  5), "ha": "left"},
]

colour = {"mainstem": "#1565C0", "tributary": "#E65100", "tidal": "#7B1FA2"}

gdf = gpd.GeoDataFrame(
    gauges,
    geometry=[Point(g["lon"], g["lat"]) for g in gauges],
    crs="EPSG:4326",
).to_crs("EPSG:3857")

# ── download river network from OSM via Overpass API ─────────────────────────
print("Downloading river network from OSM Overpass...")
overpass_url = "https://overpass-api.de/api/interpreter"
query = """
[out:json][timeout:60];
(
  way["waterway"="river"](  -37.80,144.45,-37.35,144.96);
  way["waterway"="stream"]( -37.80,144.45,-37.35,144.96);
  way["waterway"="creek"](  -37.80,144.45,-37.35,144.96);
);
out geom;
"""
try:
    resp = requests.post(overpass_url, data={"data": query}, timeout=60)
    resp.raise_for_status()
    elements = resp.json()["elements"]
    print(f"  Got {len(elements)} waterway ways")

    rows = []
    for el in elements:
        if el["type"] != "way" or "geometry" not in el:
            continue
        coords = [(pt["lon"], pt["lat"]) for pt in el["geometry"]]
        if len(coords) < 2:
            continue
        rows.append({
            "waterway": el.get("tags", {}).get("waterway", "stream"),
            "name": el.get("tags", {}).get("name", ""),
            "geometry": LineString(coords),
        })

    water_gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326").to_crs("EPSG:3857")
    rivers  = water_gdf[water_gdf["waterway"] == "river"]
    streams = water_gdf[water_gdf["waterway"].isin(["stream", "creek"])]
    print(f"  {len(rivers)} river segments, {len(streams)} stream/creek segments")
    got_rivers = True
except Exception as e:
    print(f"  Could not download rivers: {e}")
    got_rivers = False

# ── figure ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(11, 12), dpi=150)

# 1. Plot points first to set axes bounds
for gtype, clr in colour.items():
    sub = gdf[gdf["type"] == gtype]
    sub.plot(ax=ax, color=clr, markersize=80, zorder=5,
             edgecolor="white", linewidth=0.8)

# 2. Pad extent (extra right pad for Darraweit label, extra bottom for legend)
pad = 4000
x0, y0, x1, y1 = gdf.total_bounds
ax.set_xlim(x0 - pad - 4000, x1 + pad + 2000)
ax.set_ylim(y0 - pad - 6000, y1 + pad)

# 3. B&W basemap (CartoDB Positron = white land, grey roads, no colour)
ctx.add_basemap(ax, source=ctx.providers.CartoDB.Positron, zoom=11, zorder=1)

# 4. River network overlay in blue
if got_rivers:
    if len(rivers) > 0:
        rivers.plot(ax=ax, color="#1976D2", linewidth=1.8, zorder=3, alpha=0.9)
    if streams is not None and len(streams) > 0:
        streams.plot(ax=ax, color="#64B5F6", linewidth=0.7, zorder=3, alpha=0.7)

# 5. Re-plot gauge points on top of rivers
for gtype, clr in colour.items():
    sub = gdf[gdf["type"] == gtype]
    sub.plot(ax=ax, color=clr, markersize=80, zorder=6,
             edgecolor="white", linewidth=0.8)

# 6. Labels
stroke = [pe.withStroke(linewidth=2.5, foreground="white")]
for _, row in gdf.iterrows():
    dx, dy = row["loff"]
    ax.annotate(
        row["name"],
        xy=(row.geometry.x, row.geometry.y),
        xytext=(dx, dy), textcoords="offset points",
        fontsize=7.5, fontweight="bold",
        ha=row["ha"], va="bottom",
        color="#111111",
        path_effects=stroke,
        zorder=7,
    )

# 7. Legend
handles = [
    mlines.Line2D([], [], marker="o", color="w", markerfacecolor="#1565C0",
                  markersize=9, label="Maribyrnong mainstem gauge"),
    mlines.Line2D([], [], marker="o", color="w", markerfacecolor="#E65100",
                  markersize=9, label="Tributary gauge"),
    mlines.Line2D([], [], marker="o", color="w", markerfacecolor="#7B1FA2",
                  markersize=9, label="Tidal / sparse data"),
    mlines.Line2D([], [], color="#1976D2", linewidth=2, label="River"),
    mlines.Line2D([], [], color="#64B5F6", linewidth=1, label="Creek / stream"),
]
ax.legend(handles=handles, loc="lower left", fontsize=9, framealpha=0.95)

ax.set_axis_off()
ax.set_title(
    "Maribyrnong River — 13 gauging stations contributed to Caravan",
    fontsize=12, fontweight="bold", pad=10,
)

fig.tight_layout(pad=0.5)
fig.savefig("gauge_map.png", dpi=150, bbox_inches="tight")
print("Saved: gauge_map.png")
