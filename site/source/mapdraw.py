"""Draw the report map (two views: city and province) as inline SVG.

Used by build.py. Standard library only. Reads ../data/map/*.geojson
(prepared once by tools/prepare_map_layers.py) and the report counts.

Layers, bottom to top: elevation bands, lakes, built-up area, rivers, roads,
(province view) a veil outside the province, district boundaries (also the
click targets), landmarks, district labels and report circles. The scale bar
and north arrow are HTML on top of the map, so they keep their size.

Bubbles, labels and landmarks are drawn inside <g transform="translate(x y)">
groups centred on their anchor, so the page script can shrink them a little
when the reader zooms in (scale(s)) without moving them.
"""
import json
import math
import os
from html import escape

# ---------------------------------------------------------------- settings
CITY = dict(key='city', west=-71.705, east=-71.395, south=-16.55, north=-16.285)
PROV = dict(key='prov', west=-72.33, east=-70.76, south=-16.84, north=-15.88)
W = 1000
R_MAX = {'city': 34.0, 'prov': 21.0}     # radius (units) of the biggest district total
FS = {'city': 16.0, 'prov': 15.0}        # label font size (units)
BADGE = {'city': 9.0, 'prov': 7.0}       # radius of the "confirmed" badge (units)
RAMP = [(1000, (246, 242, 234)), (2000, (241, 235, 223)), (2300, (236, 228, 213)), (2500, (230, 220, 202)),
        (2700, (224, 211, 190)), (3000, (216, 201, 176)), (3500, (207, 190, 162)), (4000, (198, 179, 148)),
        (4600, (189, 168, 134)), (4999, (186, 164, 130))]
SNOW = (250, 248, 244)


def ramp(level):
    if level >= 5000:
        return '#%02x%02x%02x' % SNOW
    for (e1, c1), (e2, c2) in zip(RAMP, RAMP[1:]):
        if level <= e2:
            t = max(0.0, min(1.0, (level - e1) / (e2 - e1)))
            return '#%02x%02x%02x' % tuple(round(a + (b - a) * t) for a, b in zip(c1, c2))
    return '#%02x%02x%02x' % RAMP[-1][1]


# ---------------------------------------------------------------- geometry
class View:
    def __init__(self, key, west, east, south, north):
        self.key = key
        lat0 = (south + north) / 2
        mx = 111320 * math.cos(math.radians(lat0))
        my = 110574.0
        self.mpu = (east - west) * mx / W                 # metres per unit
        self.ux, self.uy = mx / self.mpu, my / self.mpu
        self.west, self.north = west, north
        self.W, self.H = W, round((north - south) * self.uy)
        m = 40
        self.box = (-m, -m, self.W + m, self.H + m)

    def xy(self, p):
        return ((p[0] - self.west) * self.ux, (self.north - p[1]) * self.uy)

    def inside(self, p, pad=0.0):
        x, y = self.xy(p)
        return -pad <= x <= self.W + pad and -pad <= y <= self.H + pad


def dp(pts, tol):
    if len(pts) < 3:
        return list(pts)
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    t2 = tol * tol
    while stack:
        a, b = stack.pop()
        ax, ay = pts[a]
        bx, by = pts[b]
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy
        mi, md = -1, t2
        for i in range(a + 1, b):
            px, py = pts[i]
            t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
            d = (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2
            if d > md:
                mi, md = i, d
        if mi >= 0:
            keep[mi] = True
            stack += [(a, mi), (mi, b)]
    return [p for p, k in zip(pts, keep) if k]


def clip_poly(pts, box):
    x0, y0, x1, y1 = box

    def clip(pts, inside, cross):
        out = []
        if not pts:
            return out
        prev = pts[-1]
        for cur in pts:
            if inside(cur):
                if not inside(prev):
                    out.append(cross(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(cross(prev, cur))
            prev = cur
        return out

    def at_x(a, b, x):
        t = (x - a[0]) / (b[0] - a[0])
        return (x, a[1] + t * (b[1] - a[1]))

    def at_y(a, b, y):
        t = (y - a[1]) / (b[1] - a[1])
        return (a[0] + t * (b[0] - a[0]), y)

    pts = clip(pts, lambda p: p[0] >= x0, lambda a, b: at_x(a, b, x0))
    pts = clip(pts, lambda p: p[0] <= x1, lambda a, b: at_x(a, b, x1))
    pts = clip(pts, lambda p: p[1] >= y0, lambda a, b: at_y(a, b, y0))
    pts = clip(pts, lambda p: p[1] <= y1, lambda a, b: at_y(a, b, y1))
    return pts


def clip_line(pts, box):
    x0, y0, x1, y1 = box
    ins = [x0 <= x <= x1 and y0 <= y <= y1 for x, y in pts]
    runs, cur = [], []
    for i, p in enumerate(pts):
        if ins[i] or (i and ins[i - 1]) or (i + 1 < len(pts) and ins[i + 1]):
            cur.append(p)
        else:
            if len(cur) >= 2:
                runs.append(cur)
            cur = []
    if len(cur) >= 2:
        runs.append(cur)
    return runs


def num(v):
    s = f'{v:.1f}'
    if s.endswith('.0'):
        s = s[:-2]
    if s.startswith('0.'):
        s = s[1:]
    elif s.startswith('-0.'):
        s = '-' + s[2:]
    return '0' if s in ('-0', '') else s


def seq(vals):
    out = ''
    for v in vals:
        t = num(v)
        if out and not t.startswith('-'):
            out += ' '
        out += t
    return out


def path(view, rings, closed=True, tol=0.35):
    parts = []
    for ring in rings:
        pts = [view.xy(p) for p in ring]
        if closed:
            if len(pts) > 1 and pts[0] == pts[-1]:
                pts = pts[:-1]
            runs = [clip_poly(pts, view.box)]
        else:
            runs = clip_line(pts, view.box)
        for run in runs:
            if closed:
                run = run + run[:1]
            run = dp(run, tol)
            if len(run) < (4 if closed else 2):
                continue
            q = [(round(x, 1), round(y, 1)) for x, y in run]
            rel, (px, py) = [], q[0]
            for x, y in q[1:]:
                dx, dy = round(x - px, 1), round(y - py, 1)
                if dx or dy:
                    rel += [dx, dy]
                    px, py = x, y
            if not rel:
                continue
            parts.append('M' + seq(q[0]) + 'l' + seq(rel) + ('z' if closed else ''))
    return ''.join(parts)


def rings_of(geom):
    t, c = geom['type'], geom['coordinates']
    if t == 'Polygon':
        return c
    if t == 'MultiPolygon':
        return [r for poly in c for r in poly]
    if t == 'LineString':
        return [c]
    raise ValueError(t)


# ---------------------------------------------------------------- labels
def text_box(x, y, lines, fs, anchor):
    w = max(len(s) for s in lines) * fs * 0.56
    h = len(lines) * fs * 1.12
    x0 = x - w / 2 if anchor == 'middle' else (x if anchor == 'start' else x - w)
    return (x0, y - fs * 0.85, x0 + w, y - fs * 0.85 + h)


def overlap(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if w > 0 and h > 0 else 0.0


def district_cands(r, n, fs):
    gap = 3
    return [
        ('middle', 0, r + gap + fs * 0.85),                          # below
        ('middle', 0, -r - gap - fs * 1.12 * (n - 1) - fs * 0.25),   # above
        ('start', r + gap + 2, fs * 0.3 - fs * 0.56 * (n - 1)),      # right
        ('end', -r - gap - 2, fs * 0.3 - fs * 0.56 * (n - 1)),       # left
    ]


def symbol_cands(fs):
    return [('start', 12, fs * 0.35), ('end', -12, fs * 0.35), ('middle', 0, -13), ('middle', 0, 13 + fs * 0.85)]


def place_labels(items, obstacles, bounds):
    """Greedy placement, heaviest first. items: x, y, lines, fs, cands, weight."""
    placed = []
    for it in sorted(items, key=lambda i: -i['weight']):
        best = None
        for anchor, dx, dy in it['cands']:
            box = text_box(it['x'] + dx, it['y'] + dy, it['lines'], it['fs'], anchor)
            cost = sum(overlap(box, q) for q in placed) * 3 + sum(overlap(box, o) for o in obstacles)
            if box[0] < bounds[0] or box[2] > bounds[2] or box[1] < bounds[1] or box[3] > bounds[3]:
                cost += 1e6
            if best is None or cost < best[0] - 1e-9:
                best = (cost, anchor, dx, dy, box)
            if cost == 0:
                break
        _, anchor, dx, dy, box = best
        placed.append(box)
        it.update(anchor=anchor, dx=dx, dy=dy)
    return items


# ---------------------------------------------------------------- drawing
def badge_offset(r, rb):
    # the badge sits on the lower-right edge; on small circles it moves out so the circle stays visible
    return r * 0.72 + (rb * 0.55 if r < rb * 1.5 else 0)


def bubble_r(n, key, nmax):
    if n <= 0:
        return 0.0
    return max(3.2, R_MAX[key] * math.sqrt(n / nmax))


def draw(view, D, totals, nmax, labels_map):
    districts, province, context, terrain = D
    v, key = view, view.key
    s = []
    title = ('⟦Mapa de reportes de chirimachas en la ciudad de Arequipa, por distrito||Map of chirimacha reports in the city of Arequipa, by district⟧'
             if key == 'city' else
             '⟦Mapa de reportes de chirimachas en la provincia de Arequipa, por distrito||Map of chirimacha reports in Arequipa province, by district⟧')
    s.append(f'<svg class="msvg v-{key}" viewBox="0 0 {v.W} {v.H}" data-w="{v.W}" data-h="{v.H}" data-view="{key}" '
             f'role="group" aria-labelledby="mt-{key}"><title id="mt-{key}">{title}</title>')

    # elevation bands
    scope = 'city' if key == 'city' else 'province'
    levels = sorted(f['properties']['level'] for f in terrain['features'] if f['properties']['scope'] == scope)
    s.append(f'<rect class="m-base" width="{v.W}" height="{v.H}" fill="{ramp(levels[0] - 400)}"/>')
    s.append('<g class="m-terr" aria-hidden="true">')
    for f in sorted((f for f in terrain['features'] if f['properties']['scope'] == scope), key=lambda f: f['properties']['level']):
        lv = f['properties']['level']
        d = path(v, rings_of(f['geometry']), tol=0.6)
        if d:
            snow = ' class="snow"' if lv >= 5000 else ''
            s.append(f'<path{snow} d="{d}" fill="{ramp(lv)}" fill-rule="evenodd"/>')
    s.append('</g>')

    ctx = context['features']
    if key == 'prov':
        lakes = [f for f in ctx if f['properties']['kind'] == 'lake']
        d = path(v, [r for f in lakes for r in rings_of(f['geometry'])], tol=0.5)
        if d:
            s.append(f'<path class="m-lake" d="{d}" fill-rule="evenodd" aria-hidden="true"/>')
    urb = [f for f in ctx if f['properties']['kind'] == 'urban']
    d = path(v, [r for f in urb for r in rings_of(f['geometry'])], tol=0.5 if key == 'prov' else 0.35)
    s.append(f'<path class="m-urb" d="{d}" fill-rule="evenodd" aria-hidden="true"/>')

    s.append('<g class="m-riv" aria-hidden="true">')
    chili = []
    for f in ctx:
        p = f['properties']
        if p['kind'] == 'river' and p['scope'] == scope:
            d = path(v, rings_of(f['geometry']), closed=False, tol=0.45)
            if d:
                big = 'Chili' in p['name']
                if big:
                    chili.append(f['geometry']['coordinates'])
                s.append(f'<path class="{"big" if big else ""}" d="{d}"/>')
    s.append('</g>')

    s.append('<g class="m-road" aria-hidden="true">')
    order = {'secondary': 0, 'primary': 1, 'trunk': 2}
    for f in sorted((f for f in ctx if f['properties']['kind'] == 'road' and f['properties']['scope'] == scope),
                    key=lambda f: order[f['properties']['class']]):
        d = path(v, rings_of(f['geometry']), closed=False, tol=0.45)
        if d:
            s.append(f'<path class="{f["properties"]["class"][0]}" d="{d}"/>')
    s.append('</g>')

    prov_rings = [r for f in province['features'] for r in rings_of(f['geometry'])]
    if key == 'prov':
        frame = f'M-60 -60H{v.W + 60}V{v.H + 60}H-60z'
        s.append(f'<path class="m-veil" d="{frame}{path(v, prov_rings, tol=0.4)}" fill-rule="evenodd" aria-hidden="true"/>')

    # districts: boundaries + click targets
    s.append('<g class="m-dist">')
    for f in districts['features']:
        p = f['properties']
        d = path(v, rings_of(f['geometry']), tol=0.3)
        if d:
            s.append(f'<path class="dist" data-d="{escape(p["district"])}" d="{d}"/>')
    s.append('</g>')
    s.append(f'<path class="m-prov" d="{path(v, prov_rings, tol=0.3)}" aria-hidden="true"/>')

    # ---- landmarks, district labels and bubbles: place all labels together
    fs = FS[key]
    obstacles, lm_items, items, chili_box = [], [], [], None
    bubbles = []
    for f in districts['features']:
        p = f['properties']
        n, k = totals[p['district']]
        x, y = v.xy(p['anchor'])
        if -10 <= x <= v.W + 10 and -10 <= y <= v.H + 10:
            r = bubble_r(n, key, nmax)
            bubbles.append((n, k, p['district'], x, y, r))
            if n:
                e = r + (BADGE[key] * 0.6 if k else 0)
                obstacles.append((x - r, y - r, x + e, y + e))
    for f in ctx:
        p = f['properties']
        lon, lat = f['geometry']['coordinates'] if p['kind'] in ('peak', 'place') else (None, None)
        if p['kind'] == 'peak' and v.inside((lon, lat), -12):
            x, y = v.xy((lon, lat))
            name = {'Chachani volcano': 'Chachani', 'El Misti': 'Misti'}.get(p['name'], p['name'])
            lab = name + (f' · {p["ele"]} m' if p['ele'] and key == 'city' else '')
            lm_items.append({'kind': 'pk', 'x': x, 'y': y, 'lines': [lab], 'fs': 13, 'cands': symbol_cands(13), 'weight': 1e6})
            obstacles.append((x - 9, y - 9, x + 9, y + 8))
        elif p['kind'] == 'place' and p['class'] == 'plaza' and key == 'city':
            x, y = v.xy((lon, lat))
            lm_items.append({'kind': 'pl', 'x': x, 'y': y, 'lines': ['Plaza de Armas'], 'fs': 12, 'cands': symbol_cands(12), 'weight': 2e6})
            obstacles.append((x - 7, y - 7, x + 7, y + 7))
    if chili and key == 'city':
        best = None
        for line in chili:
            for a_, b_ in zip(line, line[1:]):
                if not (v.inside(a_, -60) and v.inside(b_, -60)):
                    continue
                x1, y1 = v.xy(a_)
                x2, y2 = v.xy(b_)
                seg = math.hypot(x2 - x1, y2 - y1)
                if 150 < (y1 + y2) / 2 < 330 and seg > 14 and (best is None or seg > best[0]):
                    best = (seg, (x1 + x2) / 2, (y1 + y2) / 2, math.degrees(math.atan2(y2 - y1, x2 - x1)))
        if best:
            _, x, y, ang = best
            ang = ang - 180 if ang > 90 else (ang + 180 if ang < -90 else ang)
            chili_box = (x, y, ang)
            obstacles.append((x - 32, y - 32, x + 32, y + 32))
    if key == 'prov':
        x0, y0 = v.xy((CITY['west'], CITY['north']))
        x1, _ = v.xy((CITY['east'], CITY['south']))
        obstacles.append((x0, y0 - 26, x1, y0 - 2))
    for f in districts['features']:
        p = f['properties']
        name = p['district']
        n, k = totals[name]
        if key == 'prov' and CITYV.inside(p['anchor']):
            continue          # city districts are labelled in the city view; here they form the cluster
        on_bubble = not (key == 'prov' and n == 0)
        lx, ly = v.xy(p['anchor'] if on_bubble else p['label_pt'])
        if not (0 <= lx <= v.W and 0 <= ly <= v.H):
            continue
        r = bubble_r(n, key, nmax) if on_bubble else 0
        lines = labels_map[name].split('|')
        items.append({'kind': 'd', 'd': name, 'x': lx, 'y': ly, 'lines': lines, 'fs': fs, 'n': n,
                      'cands': district_cands(r, len(lines), fs), 'weight': n + (0.5 if n else 0)})
    place_labels(lm_items + items, obstacles, (4, 4, v.W - 4, v.H - 4))

    s.append('<g class="m-lm" aria-hidden="true">')
    for it in lm_items:
        sym = '<path d="M0 -9 9 7H-9z"/>' if it['kind'] == 'pk' else '<path d="M0 -7 2 -2 7 -2 3 1 4.6 6.5 0 3.3 -4.6 6.5 -3 1 -7 -2 -2 -2z"/>'
        s.append(f'<g class="{it["kind"]}" transform="translate({it["x"]:.1f} {it["y"]:.1f})">{sym}'
                 f'<text x="{it["dx"]:.1f}" y="{it["dy"]:.1f}" text-anchor="{it["anchor"]}" style="font-size:{it["fs"]}px">{escape(it["lines"][0])}</text></g>')
    if chili_box:
        x, y, ang = chili_box
        s.append(f'<g class="rv" transform="translate({x:.1f} {y:.1f})"><text transform="rotate({ang:.0f}) translate(0 -6)" text-anchor="middle">Río Chili</text></g>')
    s.append('</g>')

    s.append(f'<g class="m-lab" aria-hidden="true" style="font-size:{fs}px">')
    for it in items:
        minor = ' minor' if it['n'] < 3 else ''
        tsp = ''.join(f'<tspan x="{it["dx"]:.1f}" dy="{0 if i == 0 else 1.12}em">{escape(t)}</tspan>' for i, t in enumerate(it['lines']))
        s.append(f'<g class="lb{minor}" data-d="{escape(it["d"])}" transform="translate({it["x"]:.1f} {it["y"]:.1f})">'
                 f'<text y="{it["dy"]:.1f}" text-anchor="{it["anchor"]}">{tsp}</text></g>')
    s.append('</g>')

    s.append('<g class="m-bub">')
    rb = BADGE[key]
    for n, k, name, x, y, r in sorted(bubbles, key=lambda b: -b[0]):
        hide = ' hidden' if n == 0 else ''
        es = f'{name}: {n} reporte{"" if n == 1 else "s"}, {k} chirimacha{"" if k == 1 else "s"} confirmada{"" if k == 1 else "s"}'
        en = f'{name}: {n} report{"" if n == 1 else "s"}, {k} confirmed chirimacha{"" if k == 1 else "s"}'
        bx = badge_offset(r, rb)
        s.append(f'<g class="bub"{hide} data-d="{escape(name)}" transform="translate({x:.1f} {y:.1f})" tabindex="0" role="button" '
                 f'aria-label="⟦{escape(es)}||{escape(en)}⟧"><circle class="br" r="{r:.1f}"/>'
                 f'<text class="bn" dy=".36em" style="font-size:{max(9.0, r * 0.8):.1f}px">{n if r >= 8 else ""}</text>'
                 f'<g class="bk"{"" if k else " hidden"} transform="translate({bx:.1f} {bx:.1f})"><circle r="{rb}"/>'
                 f'<text dy=".36em" style="font-size:{rb * 1.25:.1f}px">{k}</text></g></g>')
    s.append('</g>')

    if key == 'prov':
        x0, y0 = v.xy((CITY['west'], CITY['north']))
        x1, y1 = v.xy((CITY['east'], CITY['south']))
        s.append(f'<g class="m-goto" data-goto="city" tabindex="0" role="button" aria-label="⟦Ver la ciudad de Arequipa de cerca||Zoom in on the city of Arequipa⟧">'
                 f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{x1 - x0:.1f}" height="{y1 - y0:.1f}" rx="4"/>'
                 f'<text x="{x0 + (x1 - x0) / 2:.1f}" y="{y0 - 9:.1f}" text-anchor="middle">⟪Ciudad de Arequipa · ver de cerca||City of Arequipa · zoom in⟫</text></g>')

    s.append('</svg>')
    return ''.join(s)


CITYV = View(**CITY)


def build_map(map_dir, totals, labels_map):
    D = tuple(json.load(open(os.path.join(map_dir, n + '.geojson'), encoding='utf-8'))
              for n in ('districts', 'province', 'context', 'terrain'))
    nmax = max(n for n, _ in totals.values())
    city = draw(View(**CITY), D, totals, nmax, labels_map)
    prov = draw(View(**PROV), D, totals, nmax, labels_map)
    pv = View(**PROV)
    meta = {'nmax': nmax, 'rmax': R_MAX, 'badge': BADGE,
            'views': {'city': {'w': CITYV.W, 'h': CITYV.H, 'mpu': round(CITYV.mpu, 3)},
                      'prov': {'w': pv.W, 'h': pv.H, 'mpu': round(pv.mpu, 3)}}}
    return city, prov, meta
