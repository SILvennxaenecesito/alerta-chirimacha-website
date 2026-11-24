/*
  Map layers for the Alerta Chirimacha site: roads, rivers, lakes, built-up
  area, volcano peaks and elevation bands around Arequipa.

  How to run (any recent Chrome or Firefox, about one minute):
    1. Open https://tiles.openfreemap.org/planet in a browser tab.
    2. Open the developer console (F12), paste this whole file and press Enter.
    3. The browser saves osm_layers.txt (about 50 KB).
    4. Turn it into the site's GeoJSON files:
         python3 tools/prepare_map_layers.py --gpkg prov_arequipa_arequipa.gpkg \
             --osm osm_layers.txt --out site/data/map

  Data and licences
    * Vector tiles from OpenFreeMap (OpenMapTiles schema): (c) OpenStreetMap
      contributors, ODbL. Credit OpenStreetMap wherever the map is shown.
    * Elevation from Terrain Tiles on AWS Open Data (Terrarium encoding;
      SRTM and other sources).
    * Plaza de Armas position from Nominatim (OpenStreetMap). One request.
  Please keep the number of requests small (this script makes about 115).

  Output format: one record per line, fields separated by "|".
    R|c{t,p,s}|...      city roads (trunk, primary, secondary)
    R|pt|...            province trunk roads
    V|c|name|...        city rivers;  V|p|name|... province rivers (named)
    W|p|...             lakes (rings)
    U|c|...             built-up area (rings, from street density + land use)
    K|class|name|ele|.. peaks;  T|class|name|... places
    C|p|level|...       elevation bands, province (2000/3000/4000/5000 m)
    C|c|level|...       elevation bands, city (2300 ... 5000 m)
  Coordinates: 1e-4 degree grid relative to (73 W, 17 S), delta + zigzag
  coded with a 64-letter alphabet. tools/prepare_map_layers.py decodes them.
*/
(async () => {
const AC = window.AC = {};
const tj = await (await fetch('https://tiles.openfreemap.org/planet')).json();
AC.cfg = { ofm: tj.tiles[0], ter: 'https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png',
  prov: {w: -72.32, e: -70.78, s: -16.83, n: -15.89}, city: {w: -71.70, e: -71.38, s: -16.54, n: -16.27} };
AC.lon2x = (lon, z) => (lon + 180) / 360 * 2 ** z;
AC.lat2y = (lat, z) => { const r = lat * Math.PI / 180; return (1 - Math.asinh(Math.tan(r)) / Math.PI) / 2 * 2 ** z; };
AC.x2lon = (x, z) => x / 2 ** z * 360 - 180;
AC.y2lat = (y, z) => { const n = Math.PI * (1 - 2 * y / 2 ** z); return Math.atan(Math.sinh(n)) * 180 / Math.PI; };
AC.range = (b, z) => ({x0: Math.floor(AC.lon2x(b.w, z)), x1: Math.floor(AC.lon2x(b.e, z)), y0: Math.floor(AC.lat2y(b.n, z)), y1: Math.floor(AC.lat2y(b.s, z))});
const [VT, PBFm, D3C] = await Promise.all([
  import('https://cdn.jsdelivr.net/npm/@mapbox/vector-tile@2.0.3/+esm'),
  import('https://cdn.jsdelivr.net/npm/pbf@4.0.1/+esm'),
  import('https://cdn.jsdelivr.net/npm/d3-contour@4.0.2/+esm')]);
AC.VectorTile = VT.VectorTile; AC.Pbf = PBFm.default || PBFm.Pbf; AC.contours = D3C.contours;

/* ---- fetch tiles ---- */
const fetchAll = async (jobs, conc) => { let i = 0; const out = new Array(jobs.length); const w = async () => { while (i < jobs.length) { const k = i++; try { out[k] = await jobs[k](); } catch (e) { out[k] = {err: String(e)}; } } }; await Promise.all(Array.from({length: conc}, w)); return out; };
const vtJob = (z, x, y) => async () => { const r = await fetch(AC.cfg.ofm.replace('{z}', z).replace('{x}', x).replace('{y}', y)); if (!r.ok) throw new Error('vt ' + r.status); return {z, x, y, buf: await r.arrayBuffer()}; };
const terJob = (z, x, y) => async () => { const r = await fetch(AC.cfg.ter.replace('{z}', z).replace('{x}', x).replace('{y}', y)); if (!r.ok) throw new Error('ter ' + r.status);
  const bmp = await createImageBitmap(await r.blob(), {colorSpaceConversion: 'none', premultiplyAlpha: 'none'}); const c = new OffscreenCanvas(256, 256); const ctx = c.getContext('2d', {willReadFrequently: true}); ctx.drawImage(bmp, 0, 0);
  const d = ctx.getImageData(0, 0, 256, 256).data; const e = new Float32Array(65536); for (let i = 0; i < 65536; i++) e[i] = d[i * 4] * 256 + d[i * 4 + 1] + d[i * 4 + 2] / 256 - 32768; return {z, x, y, e}; };
AC.tiles = {vtc: [], vtp: [], tep: [], tec: []};
{ const jobs = [], tags = []; const add = (kind, z, b, mk) => { const r = AC.range(b, z); for (let x = r.x0; x <= r.x1; x++) for (let y = r.y0; y <= r.y1; y++) { jobs.push(mk(z, x, y)); tags.push(kind); } };
  add('vtc', 13, AC.cfg.city, vtJob); add('vtp', 10, AC.cfg.prov, vtJob); add('tep', 10, AC.cfg.prov, terJob); add('tec', 12, AC.cfg.city, terJob);
  const res = await fetchAll(jobs, 8); res.forEach((r, i) => { if (r && !r.err) AC.tiles[tags[i]].push(r); else console.warn(tags[i], r && r.err); }); }
const nom = await fetch('https://nominatim.openstreetmap.org/search?q=Plaza%20de%20Armas%2C%20Arequipa%2C%20Peru&format=jsonv2&limit=1').then(r => r.json()).catch(() => []);
AC.plaza = nom && nom[0] ? [+nom[0].lon, +nom[0].lat] : null;

/* ---- helpers ---- */
const LON0 = -73, LAT0 = -17, Q = 1e4;
const CONT = "ABCDEFGHIJKLMNOPQRSTUVWXYZ012345", TERM = "abcdefghijklmnopqrstuvwxyz6789-_";
AC.encInt = v => { let n = v < 0 ? (-v * 2 - 1) : v * 2; let s = ''; while (n >= 32) { s += CONT[n & 31]; n = Math.floor(n / 32); } return s + TERM[n]; };
AC.enc = pts => { let s = '', px = 0, py = 0, first = true; for (const p of pts) { const x = Math.round((p[0] - LON0) * Q), y = Math.round((p[1] - LAT0) * Q); if (!first && x === px && y === py) continue; s += AC.encInt(x - px) + AC.encInt(y - py); px = x; py = y; first = false; } return s; };
const K = 111320 * Math.cos(16.4 * Math.PI / 180), KY = 110574;
AC.dp = (pts, tol) => { if (pts.length < 3) return pts.slice(); const keep = new Uint8Array(pts.length); keep[0] = keep[pts.length - 1] = 1; const st = [[0, pts.length - 1]]; const t2 = tol * tol;
  while (st.length) { const [a, b] = st.pop(); const ax = pts[a][0] * K, ay = pts[a][1] * KY, bx = pts[b][0] * K, by = pts[b][1] * KY, dx = bx - ax, dy = by - ay, L2 = dx * dx + dy * dy; let mi = -1, md = t2;
    for (let i = a + 1; i < b; i++) { const px = pts[i][0] * K, py = pts[i][1] * KY; let t = L2 ? ((px - ax) * dx + (py - ay) * dy) / L2 : 0; t = Math.max(0, Math.min(1, t)); const d = (px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2; if (d > md) { md = d; mi = i; } }
    if (mi >= 0) { keep[mi] = 1; st.push([a, mi], [mi, b]); } }
  return pts.filter((_, i) => keep[i]); };
AC.dpRing = (r, tol) => { const n = r.length; if (n < 5) return r; let far = 0, fd = -1; for (let i = 1; i < n; i++) { const d = ((r[i][0] - r[0][0]) * K) ** 2 + ((r[i][1] - r[0][1]) * KY) ** 2; if (d > fd) { fd = d; far = i; } } const a = AC.dp(r.slice(0, far + 1), tol), b = AC.dp(r.slice(far), tol); return a.concat(b.slice(1)); };
AC.areaKm2 = r => { let a = 0; for (let i = 0, n = r.length; i < n; i++) { const p = r[i], q = r[(i + 1) % n]; a += p[0] * K * q[1] * KY - q[0] * K * p[1] * KY; } return Math.abs(a) / 2e6; };
AC.lenM = l => { let s = 0; for (let i = 1; i < l.length; i++) s += Math.hypot((l[i][0] - l[i - 1][0]) * K, (l[i][1] - l[i - 1][1]) * KY); return s; };
AC.clipSeg = (p, q, x0, y0, x1, y1) => { let t0 = 0, t1 = 1; const dx = q.x - p.x, dy = q.y - p.y; const P = [-dx, dx, -dy, dy], R = [p.x - x0, x1 - p.x, p.y - y0, y1 - p.y]; for (let k = 0; k < 4; k++) { if (P[k] === 0) { if (R[k] < 0) return null; } else { const r = R[k] / P[k]; if (P[k] < 0) { if (r > t1) return null; if (r > t0) t0 = r; } else { if (r < t0) return null; if (r < t1) t1 = r; } } } return [t0 === 0 ? p : {x: p.x + t0 * dx, y: p.y + t0 * dy}, t1 === 1 ? q : {x: p.x + t1 * dx, y: p.y + t1 * dy}]; };
AC.clipLine = (pts, ext) => { const out = []; let cur = null; for (let i = 0; i < pts.length - 1; i++) { const s = AC.clipSeg(pts[i], pts[i + 1], 0, 0, ext, ext); if (!s) { if (cur) { out.push(cur); cur = null; } continue; } const [a, b] = s; if (!cur) cur = [a, b]; else { const l = cur[cur.length - 1]; if (l.x === a.x && l.y === a.y) cur.push(b); else { out.push(cur); cur = [a, b]; } } if (b !== pts[i + 1]) { out.push(cur); cur = null; } } if (cur) out.push(cur); return out; };
AC.merge = (lines, tolM) => { const cell = 0.0005, tl = tolM / K, tt = tolM / KY, grid = new Map(), used = new Uint8Array(lines.length); const kf = p => Math.floor(p[0] / cell) + ',' + Math.floor(p[1] / cell);
  lines.forEach((l, i) => { for (const w of [0, 1]) { const p = w ? l[l.length - 1] : l[0]; const k = kf(p); if (!grid.has(k)) grid.set(k, []); grid.get(k).push([i, w]); } });
  const near = p => { const cx = Math.floor(p[0] / cell), cy = Math.floor(p[1] / cell); for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) { const arr = grid.get((cx + dx) + ',' + (cy + dy)); if (!arr) continue; for (const [j, w] of arr) { if (used[j]) continue; const q = w ? lines[j][lines[j].length - 1] : lines[j][0]; if (Math.abs(q[0] - p[0]) <= tl && Math.abs(q[1] - p[1]) <= tt) return [j, w]; } } return null; };
  const out = []; for (let i = 0; i < lines.length; i++) { if (used[i]) continue; used[i] = 1; let cur = lines[i].slice();
    for (;;) { const m = near(cur[cur.length - 1]); if (!m) break; const [j, w] = m; used[j] = 1; const l = lines[j]; cur = w === 0 ? cur.concat(l.slice(1)) : cur.concat(l.slice(0, -1).reverse()); }
    for (;;) { const m = near(cur[0]); if (!m) break; const [j, w] = m; used[j] = 1; const l = lines[j]; cur = w === 1 ? l.slice(0, -1).concat(cur) : l.slice(1).reverse().concat(cur); }
    out.push(cur); } return out; };
AC.vt = t => t.vt || (t.vt = new AC.VectorTile(new AC.Pbf(new Uint8Array(t.buf))));
AC.ll = (t, ext, p) => [AC.x2lon(t.x + p.x / ext, t.z), AC.y2lat(t.y + p.y / ext, t.z)];
AC.lines = (tiles, layer, cls) => { const out = {}; for (const t of tiles) { const L = AC.vt(t).layers[layer]; if (!L) continue; const ext = L.extent; for (let i = 0; i < L.length; i++) { const f = L.feature(i); if (f.type !== 2) continue; const c = cls(f.properties); if (!c) continue; for (const line of f.loadGeometry()) for (const pc of AC.clipLine(line, ext)) (out[c] = out[c] || []).push(pc.map(p => AC.ll(t, ext, p))); } } return out; };
AC.polys = (tiles, layer, ok) => { const out = []; for (const t of tiles) { const L = AC.vt(t).layers[layer]; if (!L) continue; const ext = L.extent; for (let i = 0; i < L.length; i++) { const f = L.feature(i); if (f.type !== 3 || !ok(f.properties)) continue; for (const r of f.loadGeometry()) out.push(r.map(p => AC.ll(t, ext, p))); } } return out; };
AC.points = (tiles, layer, ok) => { const out = [], seen = new Set(); for (const t of tiles) { const L = AC.vt(t).layers[layer]; if (!L) continue; const ext = L.extent; for (let i = 0; i < L.length; i++) { const f = L.feature(i); if (f.type !== 1 || !ok(f.properties)) continue; for (const g of f.loadGeometry()) for (const p of g) { if (p.x < 0 || p.y < 0 || p.x > ext || p.y > ext) continue; const ll = AC.ll(t, ext, p); const k = (f.properties.name || '') + '@' + Math.round(ll[0] * 500) + ',' + Math.round(ll[1] * 500); if (seen.has(k)) continue; seen.add(k); out.push({pr: f.properties, ll}); } } } return out; };
AC.mosaic = tiles => { const xs = tiles.map(t => t.x), ys = tiles.map(t => t.y), x0 = Math.min(...xs), y0 = Math.min(...ys), W = (Math.max(...xs) - x0 + 1) * 256, H = (Math.max(...ys) - y0 + 1) * 256; const v = new Float64Array(W * H); for (const t of tiles) { const ox = (t.x - x0) * 256, oy = (t.y - y0) * 256; for (let r = 0; r < 256; r++) for (let c = 0; c < 256; c++) v[(oy + r) * W + ox + c] = t.e[r * 256 + c]; } return {v, W, H, x0, y0, z: tiles[0].z, scale: 256}; };
AC.rings = (D, levels, tol, minKm2) => { const out = []; for (const g of AC.contours().size([D.W, D.H]).thresholds(levels)(D.v)) { for (const poly of g.coordinates) for (const ring of poly) { const ll = ring.map(([gx, gy]) => [AC.x2lon(D.x0 + gx / D.scale, D.z), AC.y2lat(D.y0 + gy / D.scale, D.z)]); if (AC.areaKm2(ll) < minKm2) continue; const s = AC.dpRing(ll, tol); if (s.length < 4) continue; out.push({level: g.value, ring: s}); } } return out; };
/* built-up area: draw streets (6 px wide at zoom 13) and residential/commercial land use, blur, keep the dense part */
AC.urbanMask = tiles => { const xs = tiles.map(t => t.x), ys = tiles.map(t => t.y), x0 = Math.min(...xs), y0 = Math.min(...ys), W = (Math.max(...xs) - x0 + 1) * 256, H = (Math.max(...ys) - y0 + 1) * 256;
  const cv = document.createElement('canvas'); cv.width = W; cv.height = H; const ctx = cv.getContext('2d', {willReadFrequently: true}); ctx.strokeStyle = '#000'; ctx.fillStyle = '#000'; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  const SC = new Set(['minor', 'tertiary', 'secondary', 'primary', 'trunk', 'motorway']), LC = new Set(['residential', 'commercial', 'industrial', 'retail', 'neighbourhood', 'suburb', 'quarter']);
  for (const t of tiles) { const vt = AC.vt(t), ox = (t.x - x0) * 256, oy = (t.y - y0) * 256; const T = vt.layers.transportation; if (T) { const s = 256 / T.extent; ctx.lineWidth = 6; ctx.beginPath(); for (let i = 0; i < T.length; i++) { const f = T.feature(i); if (f.type !== 2 || !SC.has(f.properties.class)) continue; for (const line of f.loadGeometry()) line.forEach((p, j) => { const X = ox + p.x * s, Y = oy + p.y * s; j ? ctx.lineTo(X, Y) : ctx.moveTo(X, Y); }); } ctx.stroke(); }
    const LU = vt.layers.landuse; if (LU) { const s = 256 / LU.extent; ctx.beginPath(); for (let i = 0; i < LU.length; i++) { const f = LU.feature(i); if (f.type !== 3 || !LC.has(f.properties.class)) continue; for (const r of f.loadGeometry()) { r.forEach((p, j) => { const X = ox + p.x * s, Y = oy + p.y * s; j ? ctx.lineTo(X, Y) : ctx.moveTo(X, Y); }); ctx.closePath(); } } ctx.fill('nonzero'); } }
  const cv2 = document.createElement('canvas'); cv2.width = W; cv2.height = H; const c2 = cv2.getContext('2d', {willReadFrequently: true}); c2.filter = 'blur(8px)'; c2.drawImage(cv, 0, 0); const d = c2.getImageData(0, 0, W, H).data;
  const W2 = W >> 1, H2 = H >> 1, v = new Float64Array(W2 * H2); for (let r = 0; r < H2; r++) for (let c = 0; c < W2; c++) v[r * W2 + c] = d[((r * 2) * W + c * 2) * 4 + 3];
  return {v, W: W2, H: H2, x0, y0, z: 13, scale: 128}; };

/* ---- build the records ---- */
const recs = []; const P = s => recs.push(s);
const RC = {motorway: 't', trunk: 't', primary: 'p', secondary: 's'};
for (const [c, ls] of Object.entries(AC.lines(AC.tiles.vtc, 'transportation', pr => RC[pr.class] || null))) for (const l of AC.merge(ls, 20)) { const s = AC.dp(l, c === 's' ? 18 : 14); if (s.length < 2 || AC.lenM(s) < (c === 's' ? 150 : 80)) continue; P('R|c' + c + '|' + AC.enc(s)); }
for (const [c, ls] of Object.entries(AC.lines(AC.tiles.vtp, 'transportation', pr => ({motorway: 't', trunk: 't'})[pr.class] || null))) for (const l of AC.merge(ls, 80)) { const s = AC.dp(l, 120); if (s.length < 2 || AC.lenM(s) < 1000) continue; P('R|p' + c + '|' + AC.enc(s)); }
for (const [scope, tiles, tol, mergeTol, minLen, named] of [['c', AC.tiles.vtc, 14, 20, 150, false], ['p', AC.tiles.vtp, 200, 80, 6000, true]]) {
  const byName = AC.lines(tiles, 'waterway', pr => pr.class === 'river' && (!named || pr.name) ? ('r:' + (pr.name || '')) : null);
  for (const [k, ls] of Object.entries(byName)) { const name = k.slice(2).replace(/\|/g, '/'); for (const l of AC.merge(ls, mergeTol)) { const s = AC.dp(l, tol); if (s.length < 2 || AC.lenM(s) < minLen) continue; P('V|' + scope + '|' + name + '|' + AC.enc(s)); } } }
for (const r of AC.polys(AC.tiles.vtp, 'water', pr => pr.class === 'lake' || pr.class === 'pond')) { if (AC.areaKm2(r) < 1.5) continue; const s = AC.dpRing(r, 120); if (s.length < 4) continue; P('W|p|' + AC.enc(s)); }
const want = /^(El Misti|Chachani volcano|Pichu Pichu)$/, seenK = new Set();
for (const o of AC.points(AC.tiles.vtp, 'mountain_peak', pr => want.test(pr.name || ''))) { if (seenK.has(o.pr.name)) continue; seenK.add(o.pr.name); P('K|' + (o.pr.class || '') + '|' + o.pr.name + '|' + (o.pr.ele || '') + '|' + AC.enc([o.ll])); }
for (const o of AC.points(AC.tiles.vtp, 'place', pr => pr.class === 'city' && pr.name === 'Arequipa')) P('T|city|Arequipa|' + AC.enc([o.ll]));
if (AC.plaza) P('T|plaza|Plaza de Armas|' + AC.enc([AC.plaza]));
for (const o of AC.rings(AC.mosaic(AC.tiles.tep), [2000, 3000, 4000, 5000], 400, 6)) P('C|p|' + o.level + '|' + AC.enc(o.ring));
for (const o of AC.rings(AC.mosaic(AC.tiles.tec), [2300, 2400, 2500, 2600, 2800, 3000, 3500, 4000, 4500, 5000], 55, 0.2)) P('C|c|' + o.level + '|' + AC.enc(o.ring));
for (const o of AC.rings(AC.urbanMask(AC.tiles.vtc), [128], 32, 0.25)) P('U|c|' + AC.enc(o.ring));
AC.text = recs.join('\n');

const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([AC.text], {type: 'text/plain'})); a.download = 'osm_layers.txt'; a.click();
console.log('osm_layers.txt:', AC.text.length, 'characters,', recs.length, 'records');
})();
