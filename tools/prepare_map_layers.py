"""Prepare the map layers in site/data/map/ (run once; re-run only to refresh).

Usage (from the repository root):
    python3 tools/prepare_map_layers.py \
        --gpkg  /path/to/prov_arequipa_arequipa.gpkg \
        --osm   /path/to/osm_layers.txt \
        --out   site/data/map

Inputs
  --gpkg  District boundaries of Arequipa province (INEI), from the perugeopkg
          repository: https://github.com/PaulESantos/perugeopkg  (file
          geo/prov_arequipa_arequipa.gpkg, licence CC BY-SA 4.0).
  --osm   Text produced by tools/map-layers-browser.js (roads, rivers, lakes,
          built-up area, volcano peaks and elevation bands, already simplified).

Outputs (GeoJSON, WGS84, 5 decimals)
  districts.geojson  29 districts: name, ubigeo, anchor (centre of the built-up
                     part, where the report circle goes), label point.
  context.geojson    roads, rivers, lakes, built-up area, peaks, places.
  province.geojson   outline of the province (outer edges of the districts).
  terrain.geojson    elevation bands (areas above 2000, 3000 m ... ).

Needs numpy, matplotlib and scipy (only this script; the site build does not).
"""
import argparse
import csv
import json
import math
import os
import sqlite3
import struct
import unicodedata

import numpy as np
from matplotlib.path import Path
from scipy import ndimage

LAT0 = -16.4
KX = 111320 * math.cos(math.radians(LAT0))
KY = 110574.0


def norm(s):
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', 'ignore').decode()
    return ' '.join(s.upper().split())


# ---------- geometry helpers ----------
def dp(pts, tol):
    """Douglas-Peucker in metres (pts: list of (lon, lat))."""
    if len(pts) < 3:
        return list(pts)
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = pts[a][0] * KX, pts[a][1] * KY
        bx, by = pts[b][0] * KX, pts[b][1] * KY
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        mi, md = -1, tol * tol
        for i in range(a + 1, b):
            px, py = pts[i][0] * KX, pts[i][1] * KY
            t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
            d = (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2
            if d > md:
                mi, md = i, d
        if mi >= 0:
            keep[mi] = True
            stack += [(a, mi), (mi, b)]
    return [p for p, k in zip(pts, keep) if k]


def dp_ring(r, tol):
    if r[0] == r[-1]:
        r = r[:-1]
    if len(r) < 4:
        return r + [r[0]]
    far = max(range(len(r)), key=lambda i: (r[i][0] - r[0][0]) ** 2 * KX * KX + (r[i][1] - r[0][1]) ** 2 * KY * KY)
    a = dp(r[:far + 1], tol)
    b = dp(r[far:] + [r[0]], tol)
    out = a + b[1:]
    return out


def rnd(r):
    return [[round(x, 5), round(y, 5)] for x, y in r]


def ring_area(r):
    a = 0.0
    for i in range(len(r)):
        x1, y1 = r[i]
        x2, y2 = r[(i + 1) % len(r)]
        a += x1 * KX * y2 * KY - x2 * KX * y1 * KY
    return a / 2


def point_in_ring(p, r):
    x, y = p
    inside = False
    for i in range(len(r)):
        x1, y1 = r[i]
        x2, y2 = r[(i + 1) % len(r)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            inside = not inside
    return inside


def nest(rings):
    """Rings with no structure -> MultiPolygon coordinates (outer + holes) by nesting depth."""
    rings = [r for r in rings if len(r) >= 4]
    order = sorted(range(len(rings)), key=lambda i: -abs(ring_area(rings[i])))
    parent = {}
    depth = {}
    for k, i in enumerate(order):
        depth[i], parent[i] = 0, None
        for j in reversed(order[:k]):
            if point_in_ring(rings[i][0], rings[j]):
                depth[i], parent[i] = depth[j] + 1, j
                break
    polys = {}
    for i in order:
        if depth[i] % 2 == 0:
            polys[i] = [rings[i]]
        else:
            polys[parent[i]].append(rings[i])
    return [polys[i] for i in order if i in polys]


def evenodd_mask(rings, X, Y):
    pts = np.column_stack([X.ravel(), Y.ravel()])
    m = np.zeros(len(pts), bool)
    for r in rings:
        m ^= Path(np.asarray(r)).contains_points(pts)
    return m.reshape(X.shape)


# ---------- inputs ----------
def read_gpkg(path):
    def wkb(b, off):
        e = '<' if b[off] == 1 else '>'
        off += 1
        (t,) = struct.unpack_from(e + 'I', b, off)
        off += 4
        base, dims = t % 1000, 3 if (t // 1000) in (1, 3) else 2
        if base == 3:
            (nr,) = struct.unpack_from(e + 'I', b, off)
            off += 4
            rings = []
            for _ in range(nr):
                (n,) = struct.unpack_from(e + 'I', b, off)
                off += 4
                ring = []
                for _ in range(n):
                    xy = struct.unpack_from(e + 'd' * dims, b, off)
                    off += 8 * dims
                    ring.append((xy[0], xy[1]))
                rings.append(ring)
            return [rings], off
        if base == 6:
            (n,) = struct.unpack_from(e + 'I', b, off)
            off += 4
            polys = []
            for _ in range(n):
                p, off = wkb(b, off)
                polys += p
            return polys, off
        raise ValueError(t)

    con = sqlite3.connect(path)
    (table,) = con.execute("select table_name from gpkg_contents where data_type='features'").fetchone()
    out = {}
    for geom, dist in con.execute(f"select geom, distrito from '{table}'"):
        flags = geom[3]
        env = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(flags >> 1) & 7]
        polys, _ = wkb(geom, 8 + env)
        out[norm(dist)] = polys
    return out


CONT = "ABCDEFGHIJKLMNOPQRSTUVWXYZ012345"
TERM = "abcdefghijklmnopqrstuvwxyz6789-_"


def decode(s):
    vals, n, shift = [], 0, 0
    for ch in s:
        if ch in CONT:
            n += CONT.index(ch) << shift
            shift += 5
        else:
            n += TERM.index(ch) << shift
            vals.append(n // 2 if n % 2 == 0 else -((n + 1) // 2))
            n, shift = 0, 0
    pts, x, y = [], 0, 0
    for i in range(0, len(vals), 2):
        x += vals[i]
        y += vals[i + 1]
        pts.append((round(x / 1e4 - 73, 4), round(y / 1e4 - 17, 4)))
    return pts


def read_osm(path):
    roads, rivers, lakes, urban, peaks, places = [], [], [], [], [], []
    terrain = {}
    ROAD = {'t': 'trunk', 'p': 'primary', 's': 'secondary'}
    for line in open(path, encoding='utf-8').read().split('\n'):
        f = line.split('|')
        k = f[0]
        if k == 'R':
            scope = 'city' if f[1][0] == 'c' else 'province'
            roads.append((scope, ROAD[f[1][1]], decode(f[2])))
        elif k == 'V':
            rivers.append(('city' if f[1] == 'c' else 'province', f[2], decode(f[3])))
        elif k == 'W':
            lakes.append(decode(f[2]))
        elif k == 'U':
            urban.append(decode(f[2]))
        elif k == 'K':
            peaks.append((f[2], int(f[3]) if f[3] else None, decode(f[4])[0]))
        elif k == 'T':
            places.append((f[1], f[2], decode(f[3])[0]))
        elif k == 'C':
            terrain.setdefault(('city' if f[1] == 'c' else 'province', int(f[2])), []).append(decode(f[3]))
    return roads, rivers, lakes, urban, peaks, places, terrain


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gpkg', required=True)
    ap.add_argument('--osm', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--districts', default='site/data/districts.csv')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    roads, rivers, lakes, urban, peaks, places, terrain = read_osm(a.osm)
    urban_rings = [r for r in urban]

    gp = read_gpkg(a.gpkg)
    rows = list(csv.DictReader(open(a.districts, encoding='utf-8')))
    feats = []
    cell = 60.0  # metres
    for r in rows:
        polys = gp[norm(r['district'])]
        rings = [ring for poly in polys for ring in poly]
        xs = [p[0] for ring in rings for p in ring]
        ys = [p[1] for ring in rings for p in ring]
        gx = np.arange(min(xs), max(xs), cell / KX)
        gy = np.arange(min(ys), max(ys), cell / KY)
        X, Y = np.meshgrid(gx, gy)
        inside = evenodd_mask(rings, X, Y)
        built = inside & evenodd_mask(urban_rings, X, Y)

        def centre(mask):
            d = ndimage.distance_transform_edt(np.pad(mask, 1))[1:-1, 1:-1]
            i = np.unravel_index(np.argmax(d), d.shape)
            return [round(float(X[i]), 5), round(float(Y[i]), 5)]

        def mass_centre(mask):
            # built-up cell nearest to the centre of mass of the built-up cells
            iy, ix = np.nonzero(mask)
            cy, cx = iy.mean(), ix.mean()
            k = np.argmin((iy - cy) ** 2 + (ix - cx) ** 2)
            return [round(float(X[iy[k], ix[k]]), 5), round(float(Y[iy[k], ix[k]]), 5)]

        label_pt = centre(inside)
        built_km2 = built.sum() * cell * cell / 1e6
        anchor = mass_centre(built) if built_km2 >= 0.3 else label_pt
        geom = [[rnd(dp_ring(list(ring), 6.0)) for ring in poly] for poly in polys]
        feats.append({'type': 'Feature', 'properties': {
            'district': r['district'], 'ubigeo': r['ubigeo'], 'anchor': anchor, 'label_pt': label_pt,
            'built_km2': round(built_km2, 2)},
            'geometry': {'type': 'MultiPolygon', 'coordinates': geom}})
        print(f"{r['district']:<32} anchor={anchor} built={built_km2:.1f} km2")

    edges = {}
    for polys in (gp[norm(r['district'])] for r in rows):
        for poly in polys:
            for ring in poly:
                for i in range(len(ring) - 1):
                    a_, b_ = (round(ring[i][0], 7), round(ring[i][1], 7)), (round(ring[i + 1][0], 7), round(ring[i + 1][1], 7))
                    if a_ == b_:
                        continue
                    k = (a_, b_) if a_ < b_ else (b_, a_)
                    edges[k] = edges.get(k, 0) + 1
    single = [k for k, n in edges.items() if n == 1]
    nxt = {}
    for a_, b_ in single:
        nxt.setdefault(a_, []).append(b_)
        nxt.setdefault(b_, []).append(a_)
    used, outline = set(), []
    for a_, b_ in single:
        if (a_, b_) in used or (b_, a_) in used:
            continue
        ring, prev, cur = [a_], a_, b_
        used.add((a_, b_))
        while cur != a_:
            ring.append(cur)
            cand = [c for c in nxt[cur] if (cur, c) not in used and (c, cur) not in used]
            if not cand:
                break
            used.add((cur, cand[0]))
            prev, cur = cur, cand[0]
        if len(ring) > 20:
            outline.append(rnd(dp_ring(ring + [ring[0]], 20.0)))
    print('province outline rings:', len(outline), [len(r) for r in outline], 'single edges:', len(single), 'of', len(edges))

    def fc(features, note):
        return {'type': 'FeatureCollection', 'note': note, 'features': features}

    json.dump(fc(feats, 'District boundaries: INEI, via perugeopkg (Paul E. Santos Andrade), CC BY-SA 4.0. '
                        'Simplified (6 m). anchor = centre of the built-up part of the district (OpenStreetMap), '
                        'label_pt = visual centre of the district.'),
              open(os.path.join(a.out, 'districts.geojson'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

    json.dump(fc([{'type': 'Feature', 'properties': {'name': 'Provincia de Arequipa'},
                   'geometry': {'type': 'MultiPolygon', 'coordinates': [[r] for r in outline]}}],
                 'Outline of Arequipa province = outer edges of the 29 INEI districts (CC BY-SA 4.0).'),
              open(os.path.join(a.out, 'province.geojson'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

    ctx = []
    for scope, cls, pts in roads:
        ctx.append({'type': 'Feature', 'properties': {'kind': 'road', 'scope': scope, 'class': cls},
                    'geometry': {'type': 'LineString', 'coordinates': rnd(pts)}})
    for scope, name, pts in rivers:
        ctx.append({'type': 'Feature', 'properties': {'kind': 'river', 'scope': scope, 'name': name},
                    'geometry': {'type': 'LineString', 'coordinates': rnd(pts)}})
    for poly in nest(lakes):
        ctx.append({'type': 'Feature', 'properties': {'kind': 'lake'},
                    'geometry': {'type': 'Polygon', 'coordinates': [rnd(r) for r in poly]}})
    ctx.append({'type': 'Feature', 'properties': {'kind': 'urban'},
                'geometry': {'type': 'MultiPolygon', 'coordinates': [[rnd(r) for r in poly] for poly in nest(urban)]}})
    for name, ele, p in peaks:
        ctx.append({'type': 'Feature', 'properties': {'kind': 'peak', 'name': name, 'ele': ele},
                    'geometry': {'type': 'Point', 'coordinates': [round(p[0], 5), round(p[1], 5)]}})
    for cls, name, p in places:
        ctx.append({'type': 'Feature', 'properties': {'kind': 'place', 'class': cls, 'name': name},
                    'geometry': {'type': 'Point', 'coordinates': [round(p[0], 5), round(p[1], 5)]}})
    json.dump(fc(ctx, '(c) OpenStreetMap contributors, ODbL 1.0 (via OpenFreeMap vector tiles and Nominatim). '
                      'Simplified; built-up area derived from street density and land use.'),
              open(os.path.join(a.out, 'context.geojson'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

    ter = []
    for (scope, level), rings in sorted(terrain.items()):
        ter.append({'type': 'Feature', 'properties': {'scope': scope, 'level': level},
                    'geometry': {'type': 'MultiPolygon', 'coordinates': [[rnd(r) for r in poly] for poly in nest(rings)]}})
    json.dump(fc(ter, 'Areas above each elevation (m). From Terrain Tiles on AWS Open Data (SRTM and other sources), '
                      'contoured and simplified.'),
              open(os.path.join(a.out, 'terrain.geojson'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    for n in ('districts', 'province', 'context', 'terrain'):
        print(n, os.path.getsize(os.path.join(a.out, n + '.geojson')) // 1024, 'KB')


if __name__ == '__main__':
    main()
