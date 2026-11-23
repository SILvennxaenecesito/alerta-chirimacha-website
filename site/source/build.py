"""Build the bilingual Alerta Chirimacha draft site.

Run from this folder:
    python3 build.py template.html ../data ../index.html

What it does
  1. Reads ../data/districts.csv (the 29 districts of Arequipa province and
     their place in the schematic hexagon map) and the report counts:
       ../data/reports-by-district.csv          real counts from the team, if present
       ../data/reports-by-district.sample.csv   otherwise: made-up counts for the design
     With the sample file the page shows "DATOS DE EJEMPLO / SAMPLE DATA"
     on the map, the panel and the table.
  2. Draws the district map and the table and puts them where the template says
     @@TILEMAP@@, @@TABLE_ROWS@@, @@DATA_JSON@@, @@SAMPLE_CLASS@@, @@TOTAL@@.
  3. Expands the language macros. Spanish comes first in this site:
       ⟦Español||English⟧   in HTML text   -> <span class="es">…</span><span class="en">…</span>
       ⟪Español||English⟫   in SVG <text>  -> <tspan class="es">…</tspan><tspan class="en">…</tspan>
       attr="⟦Español||English⟧"           -> attr="Español" data-en-attr="English"
       <title>⟦Español||English⟧</title>   -> <title data-en="English">Español</title>
                                              (same for <desc> and <option>)
     The page script swaps the data-en* values when the language changes; CSS
     hides whichever span/tspan is not active.

Privacy: the map only ever shows totals per district. Do not add coordinates,
addresses, names or photo metadata to the data files.
"""
import csv
import json
import math
import os
import re
import sys
from html import escape

BINS = [(0, 0), (1, 5), (6, 15), (16, 30), (31, 10**9)]


def read_csv(path):
    with open(path, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def bin_of(v):
    for i, (lo, hi) in enumerate(BINS):
        if lo <= v <= hi:
            return i
    return len(BINS) - 1


def load(data_dir):
    districts = read_csv(os.path.join(data_dir, 'districts.csv'))
    real = os.path.join(data_dir, 'reports-by-district.csv')
    sample = not os.path.exists(real)
    reports = read_csv(os.path.join(data_dir, 'reports-by-district.sample.csv') if sample else real)
    by_name = {r['district'].strip(): r for r in reports}
    names = [d['district'] for d in districts]
    assert len(names) == 29 and len(set(names)) == 29, 'expected the 29 districts of Arequipa province'
    missing = [n for n in names if n not in by_name]
    extra = [n for n in by_name if n not in names]
    assert not missing and not extra, f'district names do not match: missing {missing}, unknown {extra}'
    cells = set()
    out = []
    for d in districts:
        key = (int(d['col']), int(d['row']))
        assert key not in cells, f'two districts share map cell {key}'
        cells.add(key)
        r = by_name[d['district']]
        conf = r.get('confirmed', '').strip()
        out.append({
            'd': d['district'], 'label': d['label'], 'col': key[0], 'row': key[1], 'ubigeo': d['ubigeo'],
            'reports': int(r['reports']), 'confirmed': int(conf) if conf else None,
        })
    return out, sample


def hexagon(cx, cy, r):
    pts = []
    for k in range(6):
        a = math.radians(60 * k - 90)
        pts.append(f'{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}')
    return ' '.join(pts)


def tilemap(rows, sample):
    r = 38
    w = math.sqrt(3) * r
    m = 14
    cols = max(x['col'] for x in rows) + 1.5
    nrows = max(x['row'] for x in rows) + 1
    W = m * 2 + w * cols
    H = m * 2 + 2 * r + 1.5 * r * (nrows - 1)
    s = [f'<svg class="tm" viewBox="0 0 {W:.0f} {H:.0f}" role="group" aria-labelledby="tm-title">',
         '<title id="tm-title">⟦Mapa esquemático de los 29 distritos de la provincia de Arequipa||Schematic map of the 29 districts of Arequipa province⟧</title>']
    for x in rows:
        cx = m + w * (x['col'] + 0.5 * (x['row'] % 2)) + w / 2
        cy = m + r + 1.5 * r * x['row']
        b = bin_of(x['reports'])
        lines = x['label'].split('|')
        tag_es = ' (ejemplo)' if sample else ''
        tag_en = ' (sample)' if sample else ''
        rep_es = f"{x['reports']} reporte" + ('' if x['reports'] == 1 else 's')
        rep_en = f"{x['reports']} report" + ('' if x['reports'] == 1 else 's')
        s.append(f'<g class="tile b{b}" data-d="{escape(x["d"])}" tabindex="0" role="button" '
                 f'aria-label="⟦{escape(x["d"])}: {rep_es}{tag_es}||{escape(x["d"])}: {rep_en}{tag_en}⟧">')
        s.append(f'<polygon points="{hexagon(cx, cy, r - 1.5)}"/>')
        ny = cy - 6 - 6 * (len(lines) - 1)
        s.append('<text class="tname" text-anchor="middle">' + ''.join(
            f'<tspan x="{cx:.1f}" y="{ny + 11.5 * i:.1f}">{escape(t)}</tspan>' for i, t in enumerate(lines)) + '</text>')
        s.append(f'<text class="tval" x="{cx:.1f}" y="{cy + 21:.1f}" text-anchor="middle">{x["reports"]}</text>')
        s.append('</g>')
    if sample:
        s.append(f'<g class="ribbon" aria-hidden="true"><rect x="{W - 214:.0f}" y="6" width="206" height="24" rx="12"/>'
                 f'<text x="{W - 111:.0f}" y="22.5" text-anchor="middle">⟪DATOS DE EJEMPLO||SAMPLE DATA⟫</text></g>')
    s.append('</svg>')
    return ''.join(s)


def table_rows(rows, sample):
    out = []
    for x in sorted(rows, key=lambda x: (-x['reports'], x['d'])):
        conf = '—' if x['confirmed'] is None else str(x['confirmed'])
        out.append(f'<tr><th scope="row">{escape(x["d"])}</th><td class="num">{x["reports"]}</td><td class="num">{conf}</td></tr>')
    return ''.join(out)


def expand(s):
    def attr(m):
        es, en = m[3], m[4]
        assert '"' not in es and '"' not in en, m[0]
        return f'{m[1]}{m[2]}="{es}" data-en-{m[2]}="{en}"'
    s = re.sub(r'(\s)([a-zA-Z][\w:-]*)="⟦([^"⟧]*?)\|\|([^"⟧]*?)⟧"', attr, s)

    def elt(m):
        tag, rest, es, en = m[1], m[2], m[3], m[4]
        assert '"' not in en and '<' not in es + en, m[0]
        return f'<{tag}{rest} data-en="{en}">{es}</{tag}>'
    s = re.sub(r'<(title|desc|option)(\b[^>]*)>⟦(.*?)\|\|(.*?)⟧</\1>', elt, s, flags=re.S)
    s = re.sub(r'⟦(.*?)\|\|(.*?)⟧', r'<span class="es">\1</span><span class="en">\2</span>', s, flags=re.S)
    s = re.sub(r'⟪(.*?)\|\|(.*?)⟫', r'<tspan class="es">\1</tspan><tspan class="en">\2</tspan>', s, flags=re.S)
    assert not re.search('[⟦⟧⟪⟫]', s), 'unexpanded macro'
    return s


def main():
    src, data_dir, out = sys.argv[1], sys.argv[2], sys.argv[3]
    rows, sample = load(data_dir)
    s = open(src, encoding='utf-8').read()
    data = {'sample': sample, 'bins': BINS[:-1] + [(31, None)],
            'districts': [{k: x[k] for k in ('d', 'reports', 'confirmed', 'ubigeo')} for x in rows]}
    fills = {
        '@@TILEMAP@@': tilemap(rows, sample),
        '@@TABLE_ROWS@@': table_rows(rows, sample),
        '@@DATA_JSON@@': json.dumps(data, ensure_ascii=False),
        '@@SAMPLE_CLASS@@': 'is-sample' if sample else '',
        '@@TOTAL@@': str(sum(x['reports'] for x in rows)),
    }
    for k, v in fills.items():
        assert k in s, f'{k} missing from template'
        s = s.replace(k, v)
    s = expand(s)
    assert '@@' not in s, 'unfilled placeholder'
    open(out, 'w', encoding='utf-8').write(s)
    print(len(s) // 1024, 'KB', '(sample data)' if sample else '(real data)')


if __name__ == '__main__':
    main()
